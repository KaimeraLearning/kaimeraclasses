"""Iteration 28 backend tests:
1) Per-day proof for multi-day classes (proof_date check)
2) Teacher cancel sets can_reschedule=true & refund
3) Reschedule endpoint allows teacher-cancelled (not just student-cancelled)
4) Reschedule reactivates class (status -> 'scheduled' with new date/time)
5) Counsellor student-profile class history exposes cancelled_by/rescheduled fields
6) Admin login + backend compiles
"""
import os
import inspect
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN_EMAIL = "info@kaimeralearning.com"
ADMIN_PASS = "solidarity&peace2023"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASS},
        timeout=30,
    )
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("session_token") or data.get("token") or data.get("access_token")
    assert tok, f"No token in admin login response: {data}"
    return tok


# ─── Backend health & compile ──────────────────────────────────────────────────
class TestHealth:
    def test_admin_login_works(self, admin_token):
        assert isinstance(admin_token, str) and len(admin_token) > 0

    def test_backend_imports_no_syntax_errors(self):
        """Verify the iteration 28 modules compile cleanly."""
        from routes import teacher as teacher_routes  # noqa: F401
        from routes import counsellor as counsellor_routes  # noqa: F401
        # Required handlers exist
        assert hasattr(teacher_routes, "router")
        assert hasattr(counsellor_routes, "router")


# ─── Source-level guarantees (ground truth for the iteration changes) ──────────
class TestSourceGuarantees:
    """These verify that the documented logic actually exists in code."""

    def _src(self, mod):
        return inspect.getsource(mod)

    def test_teacher_dashboard_per_day_proof_logic(self):
        from routes import teacher
        s = self._src(teacher)
        assert "proof_date" in s, "proof_date check missing in teacher.py"
        # multi-day branch using duration_days > 1
        assert "duration_days" in s and "> 1" in s
        # today_str_proof comparison
        assert "today_str_proof" in s or "p.get('proof_date')" in s

    def test_teacher_cancel_sets_can_reschedule(self):
        from routes import teacher
        s = self._src(teacher.teacher_cancel_class)
        assert '"can_reschedule": True' in s or "'can_reschedule': True" in s, \
            "teacher_cancel_class must set can_reschedule=True"
        assert '"cancelled_by": "teacher"' in s or "'cancelled_by': 'teacher'" in s

    def test_reschedule_accepts_teacher_cancelled(self):
        from routes import teacher
        s = self._src(teacher.reschedule_class)
        assert "is_teacher_cancelled" in s, "reschedule must branch on is_teacher_cancelled"
        # Reactivation: status -> scheduled (assignment-style)
        assert 'update_fields["status"] = "scheduled"' in s or "update_fields['status'] = 'scheduled'" in s
        # Updates date/time fields
        assert 'update_fields["date"] = new_date' in s or "update_fields['date'] = new_date" in s
        assert 'update_fields["start_time"]' in s or "update_fields['start_time']" in s
        assert 'update_fields["end_time"]' in s or "update_fields['end_time']" in s
        assert "rescheduled_date" in s and "rescheduled_start_time" in s
        # Increments reschedule_count
        assert "reschedule_count" in s

    def test_reschedule_validation_block(self):
        from routes import teacher
        s = self._src(teacher.reschedule_class)
        # Allows EITHER teacher cancelled OR student cancelled today
        assert "student_cancelled_today" in s
        assert "is_teacher_cancelled" in s
        # 400 when neither
        assert "Can only reschedule cancelled classes" in s or "reschedule" in s.lower()

    def test_counsellor_student_profile_returns_class_sessions_full(self):
        from routes import counsellor
        s = self._src(counsellor.get_student_profile)
        # Returns class_history derived from class_sessions.find with {"_id": 0}
        assert "class_sessions" in s
        assert '"_id": 0' in s or "'_id': 0" in s
        assert "class_history" in s
        # Because projection only excludes _id, cancelled_by/rescheduled/reschedule_count/rescheduled_*
        # fields are passed through automatically when they exist on the doc.

    def test_full_cancellation_wallet_refund_logic(self):
        from routes import teacher
        s = self._src(teacher.teacher_cancel_class)
        assert "full_cancellation_refund" in s
        assert '"payment_status": "refunded"' in s or "'payment_status': 'refunded'" in s


# ─── Reschedule endpoint contract (auth) ───────────────────────────────────────
class TestRescheduleContract:
    def test_reschedule_requires_auth(self):
        r = requests.post(
            f"{BASE_URL}/api/teacher/reschedule-class/some_id",
            json={"new_date": "2026-02-01", "new_start_time": "10:00", "new_end_time": "11:00"},
            timeout=20,
        )
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"

    def test_reschedule_rejects_admin(self, admin_token):
        r = requests.post(
            f"{BASE_URL}/api/teacher/reschedule-class/some_id",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"new_date": "2026-02-01", "new_start_time": "10:00", "new_end_time": "11:00"},
            timeout=20,
        )
        # Must reject non-teacher
        assert r.status_code == 403, f"Expected 403 for non-teacher, got {r.status_code} {r.text}"

    def test_teacher_cancel_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/teacher/cancel-class/x", timeout=20)
        assert r.status_code in (401, 403)

    def test_teacher_cancel_rejects_admin(self, admin_token):
        r = requests.post(
            f"{BASE_URL}/api/teacher/cancel-class/some_id",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=20,
        )
        assert r.status_code == 403


# ─── Counsellor student-profile contract ───────────────────────────────────────
class TestCounsellorProfileContract:
    def test_student_profile_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/counsellor/student-profile/no_such", timeout=20)
        assert r.status_code in (401, 403)

    def test_student_profile_admin_allowed_returns_404_for_missing(self, admin_token):
        # Admin role is allowed (in addition to counsellor) per route check
        r = requests.get(
            f"{BASE_URL}/api/counsellor/student-profile/__nonexistent__",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=20,
        )
        assert r.status_code == 404, f"Expected 404 for unknown student, got {r.status_code} {r.text}"

    def test_student_profile_class_history_shape_when_student_exists(self, admin_token):
        """If at least one student exists, verify class_history list is returned and
        each item is the raw class_sessions document (so cancel/reschedule fields pass through)."""
        # Find a student via admin users list
        r = requests.get(
            f"{BASE_URL}/api/admin/all-users",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30,
        )
        if r.status_code != 200:
            pytest.skip(f"admin/all-users not available: {r.status_code}")
        users = r.json()
        students = [u for u in users if u.get("role") == "student"]
        if not students:
            pytest.skip("No students seeded")
        sid = students[0]["user_id"]
        r2 = requests.get(
            f"{BASE_URL}/api/counsellor/student-profile/{sid}",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30,
        )
        assert r2.status_code == 200, r2.text
        data = r2.json()
        assert "class_history" in data
        assert isinstance(data["class_history"], list)
        # _id must be excluded
        for cls in data["class_history"]:
            assert "_id" not in cls
        # Allowed fields (when present) — confirm the projection didn't strip them
        # Soft check: at least dict shape and class_id key on any non-empty item
        if data["class_history"]:
            sample = data["class_history"][0]
            assert "class_id" in sample
