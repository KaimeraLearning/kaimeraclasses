"""Iteration 38: Verify teacher no-show detection works in IST timezone.

Bug: User reports student sees "Join Live" hours after teacher skipped a class
because the backend was comparing UTC `now` against class end_times that were
entered by users as IST wall-clock — a 5h30m skew that pushed the no-show
detection 5.5 hours into the future.

Fix verified: helper `services/time_utils.is_past_grace` uses IST throughout.
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
ADMIN_EMAIL = "info@kaimeralearning.com"
ADMIN_PASSWORD = "solidarity&peace2023"

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


def test_student_dashboard_marks_today_no_show_after_grace_in_ist(event_loop, db):
    """
    Class scheduled for today 09:00–10:00 IST. It's now 14:00 IST. Teacher
    never started. The student dashboard's `live_classes` entry must come back
    with `teacher_no_show=True`. Before the fix, this was False (UTC compared).
    """
    student_email = f"ist_test_{uuid.uuid4().hex[:8]}@gmail.com"
    student_id = f"user_{uuid.uuid4().hex[:12]}"
    class_id = f"class_{uuid.uuid4().hex[:12]}"
    student_pwd = "Test@1234"

    async def setup():
        # Hash password
        import bcrypt
        pw_hash = bcrypt.hashpw(student_pwd.encode(), bcrypt.gensalt()).decode()
        # Create the student
        await db.users.insert_one({
            "user_id": student_id, "name": "IST Test Stu", "email": student_email,
            "role": "student", "credits": 100.0, "is_verified": True, "is_approved": True,
            "password_hash": pw_hash,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        ist_now = now_local()
        today_ist = ist_now.strftime("%Y-%m-%d")
        # End time = 4 hours ago in IST (well past grace)
        end_time = (ist_now - timedelta(hours=4)).strftime("%H:%M")
        start_time = (ist_now - timedelta(hours=5)).strftime("%H:%M")
        await db.class_sessions.insert_one({
            "class_id": class_id, "is_demo": True, "title": "Demo Session - IST Test",
            "date": today_ist, "end_date": today_ist,
            "start_time": start_time, "end_time": end_time,
            "status": "scheduled",
            "started_at_actual": None,
            "teacher_id": "tch_ist", "teacher_name": "IST Teacher",
            "assigned_student_id": student_id,
            "enrolled_students": [{"user_id": student_id, "name": "IST Test Stu"}],
            "subject": "Demo",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        return today_ist, start_time, end_time

    today_ist, start_time, end_time = event_loop.run_until_complete(setup())
    print(f"\nSeeded class for {today_ist} {start_time}-{end_time} IST (now {now_local().strftime('%H:%M IST')})")

    try:
        # Student logs in
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": student_email, "password": student_pwd},
                          headers=HEADERS, timeout=20)
        assert r.status_code == 200, f"Student login failed: {r.text}"
        token = r.json().get("session_token") or r.json().get("token")
        auth_headers = {**HEADERS, "Authorization": f"Bearer {token}"}

        # Hit /api/student/dashboard
        r = requests.get(f"{BASE_URL}/api/student/dashboard", headers=auth_headers, timeout=20)
        assert r.status_code == 200, f"Dashboard fetch failed: {r.text}"
        data = r.json()

        # Class should be in either live_classes (with teacher_no_show=True)
        # OR in cancelled_classes (auto-progressed by end-of-day logic).
        live_classes = data.get("live_classes", [])
        cancelled = data.get("cancelled_classes", [])

        target = next((c for c in live_classes if c["class_id"] == class_id), None)
        cancelled_target = next((c for c in cancelled if c["class_id"] == class_id), None)

        if target:
            assert target.get("teacher_no_show") is True, (
                f"Class on dashboard should have teacher_no_show=True. Got: {target.get('teacher_no_show')}\n"
                f"start={start_time} end={end_time} now_ist={now_local().strftime('%H:%M')}"
            )
            print("PASS — class shown in live_classes with teacher_no_show=True")
        elif cancelled_target:
            assert cancelled_target.get("teacher_no_show") is True or cancelled_target.get("status") == "teacher_no_show", (
                f"Class auto-cancelled but no_show flag not set: {cancelled_target}"
            )
            print("PASS — class auto-progressed to cancelled with teacher_no_show=True")
        else:
            pytest.fail(
                f"Class {class_id} not found in dashboard. live_classes={[c['class_id'] for c in live_classes]}, "
                f"cancelled={[c['class_id'] for c in cancelled]}"
            )
    finally:
        async def cleanup():
            await db.users.delete_one({"user_id": student_id})
            await db.class_sessions.delete_one({"class_id": class_id})
            await db.sessions.delete_many({"user_id": student_id})
        event_loop.run_until_complete(cleanup())


def test_demo_request_rejects_past_ist_slot(event_loop, db):
    """User can't book a demo for a slot that's already past in IST.

    Before the fix: a slot of 'today 10:00' would be accepted at 11am IST
    because UTC comparison saw it as future (10:00 UTC > 05:30 UTC).
    """
    email = f"past_slot_{uuid.uuid4().hex[:8]}@gmail.com"
    ist_now = now_local()
    # Pick a time 1 hour ago in IST today
    past_time = (ist_now - timedelta(hours=1)).strftime("%H:%M")
    today_ist = ist_now.strftime("%Y-%m-%d")
    body = {
        "name": "Past Slot Test", "email": email, "phone": "9999999999",
        "age": 20, "institute": "Test", "preferred_date": today_ist,
        "preferred_time_slot": past_time, "message": "should fail"
    }
    r = requests.post(f"{BASE_URL}/api/demo/request", json=body, headers=HEADERS, timeout=20)
    assert r.status_code == 400, f"Past IST slot should be rejected, got {r.status_code}: {r.text}"
    assert "future" in r.text.lower() or "past" in r.text.lower()


def test_demo_request_accepts_future_ist_slot(event_loop, db):
    """A slot 1 hour in the future IST today should be accepted."""
    email = f"future_slot_{uuid.uuid4().hex[:8]}@gmail.com"
    ist_now = now_local()
    future_time = (ist_now + timedelta(hours=2)).strftime("%H:%M")
    today_ist = ist_now.strftime("%Y-%m-%d")
    # If +2h crosses midnight, push to tomorrow
    if (ist_now + timedelta(hours=2)).date() != ist_now.date():
        today_ist = (ist_now + timedelta(days=1)).strftime("%Y-%m-%d")
    body = {
        "name": "Future Slot", "email": email, "phone": "9999999999",
        "age": 20, "institute": "Test", "preferred_date": today_ist,
        "preferred_time_slot": future_time, "message": "should succeed"
    }
    try:
        r = requests.post(f"{BASE_URL}/api/demo/request", json=body, headers=HEADERS, timeout=20)
        assert r.status_code == 200, f"Future IST slot should be accepted: {r.status_code} {r.text}"
    finally:
        async def cleanup():
            await db.demo_requests.delete_many({"email": email})
        event_loop.run_until_complete(cleanup())
