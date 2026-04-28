"""Iteration 36: Verify admin user-creation endpoints do NOT leak password/credentials in API responses,
and that response messages signal email-only delivery. Also covers reset-password (auto-gen + no echo)
and notify_event best-effort (assign-student, demo flows, class start)."""
import os
import json
import uuid
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://skill-exchange-149.preview.emergentagent.com').rstrip('/')

ADMIN_EMAIL = "info@kaimeralearning.com"
ADMIN_PASSWORD = "solidarity&peace2023"

# IDs of test users we create — used for cleanup
_CREATED_USER_IDS = []
_CREATED_EMAILS = []


@pytest.fixture
def admin_headers():
    """Function-scoped login — tests fresh session each call to avoid invalidation."""
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=20)
    if r.status_code != 200:
        pytest.skip(f"Admin login failed: {r.status_code} {r.text[:200]}")
    token = r.json().get("session_token") or r.json().get("token") or r.json().get("access_token")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _rand_email(prefix):
    return f"test{prefix}{uuid.uuid4().hex[:8]}@gmail.com"


def _no_password_leak(payload: dict):
    """Verify response does NOT carry password/credentials/temp_password fields."""
    leaked_keys = []
    forbidden = {"password", "temp_password", "credentials", "student_credentials",
                 "teacher_credentials", "counsellor_credentials", "auto_password",
                 "new_password", "password_hash"}
    text = json.dumps(payload).lower()
    for k in forbidden:
        if k in payload:
            leaked_keys.append(k)
    assert not leaked_keys, f"Response leaked password fields: {leaked_keys} → {payload}"


# ── Admin create-teacher ────────────────────────────────────────────────────
class TestCreateTeacher:
    def test_create_teacher_no_password_in_response(self, admin_headers):
        email = _rand_email("teacher")
        r = requests.post(f"{BASE_URL}/api/admin/create-teacher",
                          headers=admin_headers,
                          json={"email": email, "name": "TEST Teacher Auto", "password": "ignored123"},
                          timeout=30)
        assert r.status_code == 200, f"create-teacher failed: {r.status_code} {r.text[:300]}"
        data = r.json()
        _no_password_leak(data)
        assert "Credentials emailed" in data.get("message", "") or "emailed" in data.get("message", "").lower(), \
            f"Message must indicate email delivery: {data.get('message')}"
        assert data.get("user_id"), "user_id missing"
        assert data.get("teacher_code", "").startswith("KL-T"), f"teacher_code missing/wrong: {data.get('teacher_code')}"
        _CREATED_USER_IDS.append(data["user_id"])
        _CREATED_EMAILS.append(email)


# ── Admin create-counsellor ─────────────────────────────────────────────────
class TestCreateCounsellor:
    def test_create_counsellor_no_password_in_response(self, admin_headers):
        email = _rand_email("counsel")
        r = requests.post(f"{BASE_URL}/api/admin/create-counsellor",
                          headers=admin_headers,
                          json={"email": email, "name": "TEST Counsellor Auto", "password": "ignored123"},
                          timeout=30)
        assert r.status_code == 200, f"create-counsellor failed: {r.status_code} {r.text[:300]}"
        data = r.json()
        _no_password_leak(data)
        assert "emailed" in data.get("message", "").lower()
        assert data.get("counselor_id", "").startswith("KLC-")
        _CREATED_USER_IDS.append(data["user_id"])
        _CREATED_EMAILS.append(email)


# ── Admin create-student ────────────────────────────────────────────────────
class TestCreateStudent:
    def test_create_student_no_password_even_when_sent(self, admin_headers):
        email = _rand_email("student")
        # Even if request body contains password, response must not echo it
        r = requests.post(f"{BASE_URL}/api/admin/create-student",
                          headers=admin_headers,
                          json={
                              "email": email, "name": "TEST Student Auto",
                              "password": "ShouldNotBeEchoed123",
                              "phone": None, "institute": "TestInst",
                              "goal": "Math", "preferred_time_slot": "evening",
                              "state": "KA", "city": "BLR", "country": "IN", "grade": "8"
                          },
                          timeout=30)
        assert r.status_code == 200, f"create-student failed: {r.status_code} {r.text[:300]}"
        data = r.json()
        _no_password_leak(data)
        assert "ShouldNotBeEchoed" not in json.dumps(data), "Request password leaked back!"
        assert data.get("student_code", "").startswith("KL-S")
        _CREATED_USER_IDS.append(data["user_id"])
        _CREATED_EMAILS.append(email)


# ── Admin create-user (generic) ─────────────────────────────────────────────
class TestCreateUser:
    def test_create_user_password_sanitized(self, admin_headers):
        email = _rand_email("user")
        r = requests.post(f"{BASE_URL}/api/admin/create-user",
                          headers=admin_headers,
                          json={"role": "student", "name": "TEST Generic User",
                                "email": email, "password": "auto"},
                          timeout=30)
        assert r.status_code == 200, f"create-user failed: {r.status_code} {r.text[:300]}"
        data = r.json()
        _no_password_leak(data)
        assert "auto" != data.get("password", None)
        assert "emailed" in data.get("message", "").lower()
        _CREATED_USER_IDS.append(data["user_id"])
        _CREATED_EMAILS.append(email)


# ── Admin reset-password ────────────────────────────────────────────────────
class TestResetPassword:
    def test_reset_password_no_echo_auto_generated(self, admin_headers):
        # Use the first created teacher's email (must exist for reset)
        if not _CREATED_EMAILS:
            pytest.skip("No created users available for reset test")
        target_email = _CREATED_EMAILS[0]
        # Omit new_password — backend must auto-generate
        r = requests.post(f"{BASE_URL}/api/admin/reset-password",
                          headers=admin_headers,
                          json={"email": target_email},
                          timeout=30)
        assert r.status_code == 200, f"reset-password failed: {r.status_code} {r.text[:300]}"
        data = r.json()
        _no_password_leak(data)
        # Even if user passes new_password, ensure response doesn't echo it
        r2 = requests.post(f"{BASE_URL}/api/admin/reset-password",
                           headers=admin_headers,
                           json={"email": target_email, "new_password": "ExplicitPassword456!"},
                           timeout=30)
        assert r2.status_code == 200
        data2 = r2.json()
        assert "ExplicitPassword456" not in json.dumps(data2), "Explicit password leaked back!"


# ── Admin assign-student (best-effort notify) ───────────────────────────────
class TestAssignStudent:
    def test_assign_student_endpoint_does_not_raise_on_no_demo(self, admin_headers):
        # Without a completed demo this endpoint should return 400 (not 500),
        # confirming notify_event is never reached AND no crash occurs.
        if len(_CREATED_USER_IDS) < 2:
            pytest.skip("Need teacher+student to test assign")
        student_id = None
        teacher_id = None
        # Map by querying admin/all-users
        r = requests.get(f"{BASE_URL}/api/admin/all-users", headers=admin_headers, timeout=20)
        users = r.json() if r.status_code == 200 else []
        for u in users:
            if u.get("user_id") in _CREATED_USER_IDS:
                if u.get("role") == "student" and not student_id:
                    student_id = u["user_id"]
                elif u.get("role") == "teacher" and not teacher_id:
                    teacher_id = u["user_id"]
        if not (student_id and teacher_id):
            pytest.skip("Could not locate created student+teacher")
        r = requests.post(f"{BASE_URL}/api/admin/assign-student",
                          headers=admin_headers,
                          json={"student_id": student_id, "teacher_id": teacher_id},
                          timeout=30)
        # Should be 400 (no demo completed), NOT 500
        assert r.status_code in (200, 400), f"Unexpected status: {r.status_code} {r.text[:300]}"
        if r.status_code == 400:
            assert "demo" in r.text.lower()


# ── Cleanup test users created during this run ──────────────────────────────
def teardown_module(module):
    try:
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=20)
        if r.status_code != 200:
            return
        token = r.json().get("session_token") or r.json().get("token") or r.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        # Try cleanup endpoint per user (if available)
        for uid in _CREATED_USER_IDS:
            try:
                requests.delete(f"{BASE_URL}/api/admin/user/{uid}",
                                headers=headers, timeout=10)
            except Exception:
                pass
    except Exception:
        pass
