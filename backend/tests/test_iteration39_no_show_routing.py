"""Iteration 39: Teacher dashboard must NOT route teacher-no-show classes to
'conducted' (where the Submit Proof button lives). They go to 'cancelled' with
the teacher_no_show flag set so the UI shows a MISSED badge instead.

Also verifies that the student dashboard, when it detects an on-the-fly
no-show, persists the status and routes the class to cancelled (NOT live).
"""
import os
import asyncio
import uuid
import sys
from datetime import datetime, timezone, timedelta

import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")
load_dotenv("/app/backend/.env")
from services.time_utils import now_local  # noqa: E402

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://skill-exchange-149.preview.emergentagent.com").rstrip("/")
API_KEY = os.environ.get("API_KEY")
MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME")

HEADERS = {"Content-Type": "application/json"}
if API_KEY:
    HEADERS["x-api-key"] = API_KEY


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
def db(event_loop):
    client = AsyncIOMotorClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


def _make_user(role: str, email: str, password: str = "Test@1234"):
    """Helper to create + login a user, return (user_id, auth_headers)."""
    import bcrypt
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    return user_id, pw_hash


def test_teacher_dashboard_routes_no_show_to_cancelled_not_conducted(event_loop, db):
    """Class scheduled for today, end_time has passed in IST, teacher never
    started. The teacher dashboard must route it to `cancelled_classes` with
    teacher_no_show=True — NOT to `conducted_classes` (Submit Proof should be hidden)."""
    teacher_email = f"tch_ns_{uuid.uuid4().hex[:8]}@gmail.com"
    teacher_pwd = "Test@1234"
    teacher_id, pw_hash = _make_user("teacher", teacher_email, teacher_pwd)
    class_id = f"class_{uuid.uuid4().hex[:12]}"

    async def setup():
        await db.users.insert_one({
            "user_id": teacher_id, "name": "Teach NS", "email": teacher_email,
            "role": "teacher", "is_approved": True, "is_verified": True,
            "password_hash": pw_hash, "star_rating": 5.0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        ist_now = now_local()
        today_ist = ist_now.strftime("%Y-%m-%d")
        end_time = (ist_now - timedelta(hours=2)).strftime("%H:%M")
        start_time = (ist_now - timedelta(hours=3)).strftime("%H:%M")
        await db.class_sessions.insert_one({
            "class_id": class_id, "teacher_id": teacher_id, "teacher_name": "Teach NS",
            "title": "No-Show Test Class", "subject": "Math", "is_demo": False,
            "date": today_ist, "end_date": today_ist,
            "start_time": start_time, "end_time": end_time,
            "status": "scheduled", "started_at_actual": None,
            "duration_days": 1, "max_students": 1,
            "enrolled_students": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    event_loop.run_until_complete(setup())

    try:
        # Login as teacher
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": teacher_email, "password": teacher_pwd},
                          headers=HEADERS, timeout=20)
        assert r.status_code == 200, f"Login failed: {r.text}"
        token = r.json().get("session_token") or r.json().get("token")
        auth = {**HEADERS, "Authorization": f"Bearer {token}"}

        r = requests.get(f"{BASE_URL}/api/teacher/dashboard", headers=auth, timeout=20)
        assert r.status_code == 200, f"Dashboard failed: {r.text}"
        data = r.json()

        conducted_ids = [c["class_id"] for c in data.get("conducted_classes", [])]
        cancelled_ids = [c["class_id"] for c in data.get("cancelled_classes", [])]

        assert class_id not in conducted_ids, (
            f"BUG: no-show class {class_id} ended up in conducted_classes — "
            f"Submit Proof would show. ConductedIDs={conducted_ids}"
        )
        assert class_id in cancelled_ids, (
            f"No-show class should be in cancelled_classes. "
            f"CancelledIDs={cancelled_ids} ConductedIDs={conducted_ids}"
        )

        # And the teacher_no_show flag is set
        target = next((c for c in data["cancelled_classes"] if c["class_id"] == class_id), None)
        assert target and target.get("teacher_no_show") is True, (
            f"teacher_no_show flag not set on cancelled class: {target}"
        )

        # Verify DB persistence: status should now be teacher_no_show
        async def check_db():
            cls = await db.class_sessions.find_one({"class_id": class_id}, {"_id": 0})
            return cls.get("status"), cls.get("teacher_no_show")
        status_db, flag_db = event_loop.run_until_complete(check_db())
        assert status_db == "teacher_no_show", f"DB status not persisted: {status_db}"
        assert flag_db is True, f"DB teacher_no_show flag not set: {flag_db}"

    finally:
        async def cleanup():
            await db.users.delete_one({"user_id": teacher_id})
            await db.class_sessions.delete_one({"class_id": class_id})
            await db.sessions.delete_many({"user_id": teacher_id})
        event_loop.run_until_complete(cleanup())


def test_student_dashboard_routes_no_show_to_cancelled_not_live(event_loop, db):
    """Same scenario, student-side: when end_time has passed in IST and teacher
    never started, the class must NOT be in `live_classes` (no Join Live button)."""
    student_email = f"stu_ns_{uuid.uuid4().hex[:8]}@gmail.com"
    student_pwd = "Test@1234"
    student_id, pw_hash = _make_user("student", student_email, student_pwd)
    class_id = f"class_{uuid.uuid4().hex[:12]}"

    async def setup():
        await db.users.insert_one({
            "user_id": student_id, "name": "Stu NS", "email": student_email,
            "role": "student", "credits": 100.0, "is_verified": True, "is_approved": True,
            "password_hash": pw_hash,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        ist_now = now_local()
        today_ist = ist_now.strftime("%Y-%m-%d")
        end_time = (ist_now - timedelta(hours=2)).strftime("%H:%M")
        start_time = (ist_now - timedelta(hours=3)).strftime("%H:%M")
        await db.class_sessions.insert_one({
            "class_id": class_id, "is_demo": True, "title": "Demo No-Show Stu",
            "date": today_ist, "end_date": today_ist,
            "start_time": start_time, "end_time": end_time,
            "status": "scheduled", "started_at_actual": None,
            "teacher_id": "tch_ist", "teacher_name": "T",
            "assigned_student_id": student_id,
            "enrolled_students": [{"user_id": student_id, "name": "Stu NS"}],
            "subject": "Demo",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    event_loop.run_until_complete(setup())

    try:
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": student_email, "password": student_pwd},
                          headers=HEADERS, timeout=20)
        assert r.status_code == 200
        token = r.json().get("session_token") or r.json().get("token")
        auth = {**HEADERS, "Authorization": f"Bearer {token}"}

        r = requests.get(f"{BASE_URL}/api/student/dashboard", headers=auth, timeout=20)
        assert r.status_code == 200
        data = r.json()

        live_ids = [c["class_id"] for c in data.get("live_classes", [])]
        cancelled_ids = [c["class_id"] for c in data.get("cancelled_classes", [])]

        assert class_id not in live_ids, (
            f"BUG: no-show class shown in live_classes (Join Live would render). "
            f"LiveIDs={live_ids}"
        )
        assert class_id in cancelled_ids, (
            f"No-show class should be in cancelled_classes. "
            f"CancelledIDs={cancelled_ids} LiveIDs={live_ids}"
        )
        target = next((c for c in data["cancelled_classes"] if c["class_id"] == class_id), None)
        assert target and target.get("teacher_no_show") is True

    finally:
        async def cleanup():
            await db.users.delete_one({"user_id": student_id})
            await db.class_sessions.delete_one({"class_id": class_id})
            await db.sessions.delete_many({"user_id": student_id})
        event_loop.run_until_complete(cleanup())
