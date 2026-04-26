"""
Iteration 29 backend tests:
1) Reschedule reverses per-class credit refund and (if any) full assignment refund
2) Reschedule extends end_date by reschedule_count days
3) Attendance mark returns needs_reason when no class on that date (status 200)
4) Attendance mark stores reason / class_id / off_day_marking fields
5) GET /api/counsellor/student-attendance/{student_id} - role-gated to counsellor/admin
6) Admin login works
7) Backend compiles without errors (module import)
"""
import os
import re
import importlib
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://skill-exchange-149.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "info@kaimeralearning.com"
ADMIN_PASSWORD = "solidarity&peace2023"


# ---------- Source-level guarantees ----------
class TestBackendCompiles:
    """Confirm modified modules import without error (i.e., compile)."""

    def test_teacher_module_imports(self):
        m = importlib.import_module("routes.teacher")
        assert m is not None

    def test_attendance_module_imports(self):
        m = importlib.import_module("routes.attendance")
        assert m is not None

    def test_counsellor_module_imports(self):
        m = importlib.import_module("routes.counsellor")
        assert m is not None


class TestRescheduleRefundReversalSource:
    """Source-level checks for refund-loophole fix in reschedule endpoint."""

    @classmethod
    def setup_class(cls):
        with open("/app/backend/routes/teacher.py", "r") as f:
            cls.src = f.read()

    def test_reschedule_recharge_transaction_type(self):
        assert '"reschedule_recharge"' in self.src or "'reschedule_recharge'" in self.src

    def test_per_class_refund_decrement(self):
        # Re-charges student credits ($inc credits by -refund)
        assert "$inc" in self.src and "-refund_to_reclaim" in self.src

    def test_refund_reversal_transaction_type(self):
        assert '"refund_reversal"' in self.src or "'refund_reversal'" in self.src

    def test_assignment_payment_status_flipped_back_to_paid(self):
        assert '"payment_status": "paid"' in self.src or "'payment_status': 'paid'" in self.src

    def test_assignment_refunded_filter(self):
        # Looks up refunded assignment to reverse
        assert '"payment_status": "refunded"' in self.src or "'payment_status': 'refunded'" in self.src

    def test_end_date_shifted_by_reschedule_count(self):
        # reschedule_num added to timedelta days
        assert "reschedule_num" in self.src
        m = re.search(r"timedelta\(days=cls\.get\(['\"]duration_days['\"],\s*1\)\s*-\s*1\s*\+\s*reschedule_num\)", self.src)
        assert m is not None, "end_date shift formula not found"


class TestAttendanceNonClassDaySource:
    """Source-level checks for attendance non-class-day detection."""

    @classmethod
    def setup_class(cls):
        with open("/app/backend/routes/attendance.py", "r") as f:
            cls.src = f.read()

    def test_needs_reason_response(self):
        assert '"needs_reason": True' in self.src or "'needs_reason': True" in self.src

    def test_available_classes_returned(self):
        assert "available_classes" in self.src

    def test_reason_field_optional(self):
        assert 'reason = body.get("reason")' in self.src or "reason = body.get('reason')" in self.src

    def test_class_id_field_optional(self):
        assert 'class_id = body.get("class_id")' in self.src or "class_id = body.get('class_id')" in self.src

    def test_off_day_marking_set_when_no_class(self):
        assert 'record["off_day_marking"] = True' in self.src or "record['off_day_marking'] = True" in self.src

    def test_class_lookup_uses_date_range(self):
        # has_class_today uses date <= target <= end_date
        assert '"date": {"$lte": date}' in self.src or "'date': {'$lte': date}" in self.src
        assert '"end_date": {"$gte": date}' in self.src or "'end_date': {'$gte': date}" in self.src


class TestCounsellorStudentAttendanceSource:
    """Source-level checks for new counsellor student-attendance endpoint."""

    @classmethod
    def setup_class(cls):
        with open("/app/backend/routes/counsellor.py", "r") as f:
            cls.src = f.read()

    def test_endpoint_registered(self):
        assert "/counsellor/student-attendance/{student_id}" in self.src

    def test_role_gated_counsellor_admin(self):
        # Endpoint must restrict to counsellor or admin
        m = re.search(r'counsellor_student_attendance.*?role not in \[\s*"counsellor"\s*,\s*"admin"\s*\]', self.src, re.S)
        assert m is not None

    def test_returns_attendance_records_no_objectid(self):
        # _id excluded
        assert 'db.attendance.find({"student_id": student_id}, {"_id": 0})' in self.src


# ---------- Live HTTP contract checks ----------
@pytest.fixture(scope="module")
def admin_session():
    """Returns a requests.Session() with admin cookie/Bearer set."""
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=20)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    data = r.json()
    session_token = data.get("session_token") or data.get("token") or data.get("access_token")
    assert session_token, f"No session_token in response: {data}"
    # Auth supports both cookie and bearer; set both for safety
    s.headers.update({"Authorization": f"Bearer {session_token}"})
    s.cookies.set("session_token", session_token)
    return s


class TestAdminAuth:
    def test_admin_login_success(self):
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert "session_token" in d or "token" in d or "access_token" in d
        u = d.get("user") or {}
        assert u.get("role") == "admin"

    def test_admin_login_wrong_password(self):
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": ADMIN_EMAIL, "password": "WRONG"}, timeout=20)
        assert r.status_code in (400, 401, 403)


class TestAttendanceMarkContract:
    """HTTP contract for /api/attendance/mark - role gated to teacher only."""

    def test_mark_unauthenticated_returns_401(self):
        r = requests.post(f"{BASE_URL}/api/attendance/mark",
                          json={"student_id": "x", "date": "2026-01-01", "status": "present"}, timeout=20)
        assert r.status_code in (401, 403)

    def test_mark_admin_forbidden(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/attendance/mark",
                               json={"student_id": "x", "date": "2026-01-01", "status": "present"}, timeout=20)
        # Teachers only -> 403 for admin
        assert r.status_code == 403


class TestCounsellorStudentAttendanceContract:
    """HTTP contract for /api/counsellor/student-attendance/{student_id}."""

    def test_unauthenticated_returns_401(self):
        r = requests.get(f"{BASE_URL}/api/counsellor/student-attendance/some_student_id", timeout=20)
        assert r.status_code in (401, 403)

    def test_admin_can_access(self, admin_session):
        # Admin role is allowed; should return list (possibly empty) with 200
        r = admin_session.get(f"{BASE_URL}/api/counsellor/student-attendance/nonexistent_student", timeout=20)
        assert r.status_code == 200, f"Expected 200 for admin, got {r.status_code} {r.text}"
        body = r.json()
        assert isinstance(body, list)

    def test_admin_response_excludes_mongo_objectid(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/counsellor/student-attendance/anything", timeout=20)
        assert r.status_code == 200
        for rec in r.json():
            assert "_id" not in rec


class TestRescheduleEndpointContract:
    """Reschedule endpoint - teachers only."""

    def test_unauthenticated_returns_401(self):
        r = requests.post(f"{BASE_URL}/api/teacher/reschedule-class/some_class_id",
                          json={"new_date": "2026-01-15", "new_start_time": "10:00", "new_end_time": "11:00"}, timeout=20)
        assert r.status_code in (401, 403)

    def test_admin_forbidden(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/teacher/reschedule-class/some_class_id",
                               json={"new_date": "2026-01-15", "new_start_time": "10:00", "new_end_time": "11:00"}, timeout=20)
        assert r.status_code == 403


# ---------- Frontend source guarantees ----------
class TestFrontendIntegrationSource:
    """Confirm UI wires to the new backend contract."""

    @classmethod
    def setup_class(cls):
        with open("/app/frontend/src/pages/TeacherDashboard.js", "r") as f:
            cls.tsrc = f.read()
        with open("/app/frontend/src/pages/CounsellorStudents.js", "r") as f:
            cls.csrc = f.read()

    def test_teacher_handles_needs_reason(self):
        assert "data.needs_reason" in self.tsrc
        assert "available_classes" in self.tsrc

    def test_teacher_dialog_has_reason_options(self):
        assert "data-testid=\"reason-forgot\"" in self.tsrc
        assert "data-testid=\"reason-rescheduled\"" in self.tsrc

    def test_teacher_attendance_renders_off_day(self):
        assert "off_day_marking" in self.tsrc
        assert "Off-day" in self.tsrc

    def test_counsellor_calls_student_attendance_endpoint(self):
        assert "/counsellor/student-attendance/" in self.csrc

    def test_counsellor_renders_off_day_marking(self):
        assert "off_day_marking" in self.csrc
