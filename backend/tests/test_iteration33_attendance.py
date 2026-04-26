"""Iteration 33: Per-class per-day attendance overhaul tests.

Tests:
- Admin login works
- POST /api/attendance/mark requires class_id (auto-detect or specified)
- POST /api/attendance/mark returns 409 if already marked for same class+date
- POST /api/attendance/mark returns needs_class_selection when no class on that date
- GET /api/attendance/unmarked returns array (teacher only)
- GET /api/attendance/class-today/{student_id} returns today's classes with already_marked flag
- GET /api/attendance/teacher returns records with class_title field
"""
import os
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/backend/.env")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://skill-exchange-149.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = "info@kaimeralearning.com"
ADMIN_PASSWORD = "solidarity&peace2023"

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME")


@pytest.fixture(scope="module")
def mongo():
    client = MongoClient(MONGO_URL)
    return client[DB_NAME]


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    body = r.json()
    token = body.get("token") or body.get("access_token") or body.get("session_token")
    if token:
        s.headers.update({"Authorization": f"Bearer {token}"})
    return s


# ---- Admin login ----

class TestAdminAuth:
    def test_admin_login(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("user", {}).get("role") == "admin" or body.get("role") == "admin"


# ---- Teacher seed + attendance flows (direct DB seeding to enable testing) ----

@pytest.fixture(scope="module")
def teacher_seed(mongo):
    """Create a TEST_ teacher, student, paid assignment, and one class covering today.
    Returns dict with ids and teacher session token."""
    suffix = uuid.uuid4().hex[:8]
    teacher_id = f"TEST_teacher_{suffix}"
    student_id = f"TEST_student_{suffix}"
    class_id = f"TEST_class_{suffix}"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    next_week = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")
    long_past = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%d")

    # Insert teacher
    mongo.users.insert_one({
        "user_id": teacher_id,
        "email": f"TEST_teacher_{suffix}@test.com",
        "name": "TEST Teacher",
        "role": "teacher",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    mongo.users.insert_one({
        "user_id": student_id,
        "email": f"TEST_student_{suffix}@test.com",
        "name": "TEST Student",
        "role": "student",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    # Assignment paid+approved
    mongo.student_teacher_assignments.insert_one({
        "assignment_id": f"TEST_assn_{suffix}",
        "teacher_id": teacher_id,
        "student_id": student_id,
        "student_name": "TEST Student",
        "status": "approved",
        "payment_status": "paid",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    # A class that covers today (for auto-detect)
    mongo.class_sessions.insert_one({
        "class_id": class_id,
        "teacher_id": teacher_id,
        "assigned_student_id": student_id,
        "student_name": "TEST Student",
        "title": "TEST Math 101",
        "status": "scheduled",
        "date": yesterday,
        "end_date": next_week,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    # An old class that ended before yesterday (for unmarked-history tests)
    old_class_id = f"TEST_oldclass_{suffix}"
    mongo.class_sessions.insert_one({
        "class_id": old_class_id,
        "teacher_id": teacher_id,
        "assigned_student_id": student_id,
        "student_name": "TEST Student",
        "title": "TEST Old Class",
        "status": "completed",
        "date": long_past,
        "end_date": long_past,  # single-day class, should appear unmarked
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    # Create a session token for teacher (matches services/auth pattern in this app)
    token = uuid.uuid4().hex
    mongo.user_sessions.insert_one({
        "session_token": token,
        "user_id": teacher_id,
        "email": f"TEST_teacher_{suffix}@test.com",
        "name": "TEST Teacher",
        "role": "teacher",
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
    })

    yield {
        "teacher_id": teacher_id,
        "student_id": student_id,
        "class_id": class_id,
        "old_class_id": old_class_id,
        "today": today,
        "yesterday": yesterday,
        "long_past": long_past,
        "token": token,
        "suffix": suffix,
    }

    # Teardown
    mongo.users.delete_many({"user_id": {"$in": [teacher_id, student_id]}})
    mongo.student_teacher_assignments.delete_many({"teacher_id": teacher_id})
    mongo.class_sessions.delete_many({"teacher_id": teacher_id})
    mongo.attendance.delete_many({"teacher_id": teacher_id})
    mongo.user_sessions.delete_many({"user_id": teacher_id})


def teacher_headers(seed):
    return {"Authorization": f"Bearer {seed['token']}", "Content-Type": "application/json"}


class TestAttendanceMark:
    def test_mark_requires_student_and_date(self, teacher_seed):
        r = requests.post(f"{API}/attendance/mark", json={}, headers=teacher_headers(teacher_seed))
        assert r.status_code == 400

    def test_mark_auto_detects_class_for_today(self, teacher_seed):
        payload = {"student_id": teacher_seed["student_id"], "date": teacher_seed["today"], "status": "present"}
        r = requests.post(f"{API}/attendance/mark", json=payload, headers=teacher_headers(teacher_seed))
        assert r.status_code == 200, r.text
        body = r.json()
        assert "TEST Math 101" in body.get("message", "")

    def test_mark_409_when_already_marked(self, teacher_seed):
        payload = {"student_id": teacher_seed["student_id"], "date": teacher_seed["today"], "status": "absent"}
        r = requests.post(f"{API}/attendance/mark", json=payload, headers=teacher_headers(teacher_seed))
        assert r.status_code == 409, r.text
        body = r.json()
        # FastAPI returns detail in body
        assert "already marked" in (body.get("detail") or "").lower()

    def test_mark_returns_needs_class_selection_for_off_date(self, teacher_seed, mongo):
        # Pick a date 30 days in the future where no class is scheduled
        off_date = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")
        payload = {"student_id": teacher_seed["student_id"], "date": off_date, "status": "present"}
        r = requests.post(f"{API}/attendance/mark", json=payload, headers=teacher_headers(teacher_seed))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("needs_class_selection") is True
        assert isinstance(body.get("available_classes"), list)
        assert len(body["available_classes"]) >= 1

    def test_mark_with_explicit_class_and_reason(self, teacher_seed):
        # Mark for a different date using explicit class_id (rescheduled)
        target_date = (datetime.now(timezone.utc) + timedelta(days=31)).strftime("%Y-%m-%d")
        payload = {
            "student_id": teacher_seed["student_id"],
            "date": target_date,
            "status": "present",
            "class_id": teacher_seed["class_id"],
            "reason": "rescheduled_class",
        }
        r = requests.post(f"{API}/attendance/mark", json=payload, headers=teacher_headers(teacher_seed))
        assert r.status_code == 200, r.text


class TestAttendanceQueries:
    def test_unmarked_endpoint_returns_array(self, teacher_seed):
        r = requests.get(f"{API}/attendance/unmarked", headers=teacher_headers(teacher_seed))
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list)
        # The TEST_oldclass on long_past should appear (no attendance was marked for it)
        old_match = [u for u in data if u.get("class_id") == teacher_seed["old_class_id"]]
        assert len(old_match) >= 1, f"expected unmarked record for old class, got {data}"
        first = old_match[0]
        assert first["date"] == teacher_seed["long_past"]
        assert first["class_title"] == "TEST Old Class"
        assert first["student_id"] == teacher_seed["student_id"]

    def test_class_today_returns_already_marked(self, teacher_seed):
        r = requests.get(
            f"{API}/attendance/class-today/{teacher_seed['student_id']}",
            headers=teacher_headers(teacher_seed),
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        match = [c for c in data if c["class_id"] == teacher_seed["class_id"]]
        assert len(match) == 1
        cls = match[0]
        # earlier test marked today as present
        assert cls["already_marked"] is True
        assert cls["marked_status"] == "present"
        assert "title" in cls

    def test_teacher_history_includes_class_title(self, teacher_seed):
        r = requests.get(f"{API}/attendance/teacher", headers=teacher_headers(teacher_seed))
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list)
        ours = [d for d in data if d.get("student_id") == teacher_seed["student_id"]]
        assert len(ours) >= 1
        sample = ours[0]
        assert "class_title" in sample
        assert "class_id" in sample
        assert sample["class_title"] in ["TEST Math 101"]


class TestNonTeacherAccess:
    def test_unmarked_requires_teacher_role(self, admin_session):
        r = admin_session.get(f"{API}/attendance/unmarked")
        assert r.status_code == 403

    def test_class_today_requires_teacher_role(self, admin_session):
        r = admin_session.get(f"{API}/attendance/class-today/anything")
        assert r.status_code == 403
