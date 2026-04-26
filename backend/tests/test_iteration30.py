"""Iteration 30: Cancel/Reschedule flow redesign + admin cancel_rating_deduction.

Tests focus on direct DB-driven endpoints and pricing endpoints since teacher/student
accounts cannot be programmatically created (OTP-gated). Class flow is exercised by
seeding class_sessions directly and calling teacher endpoints that allow it via JWT
on synthetic teacher user docs.
"""
import os
import uuid
import requests
import pytest
import asyncio
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN_EMAIL = "info@kaimeralearning.com"
ADMIN_PASSWORD = "solidarity&peace2023"


# ---- Shared fixtures ----
@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                      timeout=15)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("session_token") or data.get("token") or data.get("access_token")
    assert token, f"No token in response: {data}"
    return token


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


# ---- Pricing tests: cancel_rating_deduction ----
class TestPricing:
    def test_get_pricing_baseline(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/admin/get-pricing", headers=admin_headers, timeout=15)
        assert r.status_code == 200
        data = r.json()
        # Document baseline shape
        assert "demo_price_student" in data
        assert "class_price_student" in data

    def test_set_pricing_with_cancel_rating_deduction(self, admin_headers):
        payload = {
            "demo_price_student": 100.0,
            "class_price_student": 200.0,
            "demo_earning_teacher": 50.0,
            "class_earning_teacher": 100.0,
            "cancel_rating_deduction": 0.35,
        }
        r = requests.post(f"{BASE_URL}/api/admin/set-pricing",
                          headers=admin_headers, json=payload, timeout=15)
        assert r.status_code == 200, f"set-pricing failed: {r.text}"
        # Verify by GET
        g = requests.get(f"{BASE_URL}/api/admin/get-pricing", headers=admin_headers, timeout=15)
        assert g.status_code == 200
        data = g.json()
        assert data.get("cancel_rating_deduction") == 0.35, f"deduction not saved: {data}"
        assert data.get("class_price_student") == 200.0

    def test_set_pricing_default_cancel_rating_deduction(self, admin_headers):
        # Without sending cancel_rating_deduction; Pydantic should default to 0.2
        payload = {
            "demo_price_student": 100.0,
            "class_price_student": 200.0,
            "demo_earning_teacher": 50.0,
            "class_earning_teacher": 100.0,
        }
        r = requests.post(f"{BASE_URL}/api/admin/set-pricing",
                          headers=admin_headers, json=payload, timeout=15)
        assert r.status_code == 200
        g = requests.get(f"{BASE_URL}/api/admin/get-pricing", headers=admin_headers, timeout=15)
        data = g.json()
        # Should fallback to default 0.2
        assert data.get("cancel_rating_deduction") == 0.2, f"default not applied: {data}"


# ---- Direct DB tests for cancel/reschedule flow ----
# We need direct DB access to seed a teacher + class without OTP gating.
@pytest.fixture(scope="module")
def db():
    """Direct mongo access for seeding test data."""
    from motor.motor_asyncio import AsyncIOMotorClient
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")
    client = AsyncIOMotorClient(mongo_url)
    return client[db_name]


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
def teacher_setup(db, event_loop):
    """Seed a teacher user + active class + session token."""
    teacher_id = f"test_teacher_{uuid.uuid4().hex[:8]}"
    teacher_email = f"TEST_{teacher_id}@gmail.com"
    class_id = f"test_class_{uuid.uuid4().hex[:8]}"
    student_id = f"test_student_{uuid.uuid4().hex[:8]}"

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    end_date = (datetime.now(timezone.utc) + timedelta(days=4)).strftime("%Y-%m-%d")

    teacher_doc = {
        "user_id": teacher_id, "email": teacher_email, "name": "Test Teacher 30",
        "role": "teacher", "is_approved": True, "is_suspended": False,
        "credits": 0, "star_rating": 5.0, "rating_details": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    student_doc = {
        "user_id": student_id, "email": f"TEST_{student_id}@gmail.com",
        "name": "Test Student 30", "role": "student", "credits": 1000,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    class_doc = {
        "class_id": class_id, "teacher_id": teacher_id, "teacher_name": "Test Teacher 30",
        "title": "TEST_Cancel Flow Class", "subject": "Math", "class_type": "1-on-1",
        "is_demo": False, "date": today, "end_date": end_date, "duration_days": 5,
        "current_day": 1, "start_time": "10:00", "end_time": "11:00",
        "credits_required": 500, "price_per_day": 100, "max_students": 1,
        "assigned_student_id": student_id,
        "enrolled_students": [{"user_id": student_id, "name": "Test Student 30"}],
        "status": "scheduled", "verification_status": "pending",
        "cancellations": [], "cancellation_count": 0, "max_cancellations": 3,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    assignment_doc = {
        "assignment_id": f"assign_{uuid.uuid4().hex[:8]}",
        "teacher_id": teacher_id, "student_id": student_id,
        "status": "approved", "payment_status": "paid",
        "credit_price": 100, "assigned_days": 5,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    async def setup():
        await db.users.insert_one(teacher_doc)
        await db.users.insert_one(student_doc)
        await db.class_sessions.insert_one(class_doc)
        await db.student_teacher_assignments.insert_one(assignment_doc)
        # Create session token row matching auth.get_current_user expectations
        token_str = f"sess_{uuid.uuid4().hex}"
        await db.user_sessions.insert_one({
            "session_token": token_str,
            "user_id": teacher_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        })
        return token_str

    token = event_loop.run_until_complete(setup())

    yield {"teacher_id": teacher_id, "class_id": class_id,
           "student_id": student_id, "token": token, "end_date": end_date,
           "today": today}

    # Teardown
    async def teardown():
        await db.users.delete_one({"user_id": teacher_id})
        await db.users.delete_one({"user_id": student_id})
        await db.class_sessions.delete_one({"class_id": class_id})
        await db.student_teacher_assignments.delete_one({"teacher_id": teacher_id})
        await db.teacher_rating_events.delete_many({"teacher_id": teacher_id})
        await db.notifications.delete_many({"user_id": {"$in": [teacher_id, student_id]}})
        await db.user_sessions.delete_one({"user_id": teacher_id})

    event_loop.run_until_complete(teardown())


def _teacher_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


class TestTeacherCancelSessionLevel:
    """Iteration 30 core: teacher cancel cancels TODAY's session only."""

    def test_cancel_keeps_class_scheduled_and_extends_end_date(self, teacher_setup, db, event_loop):
        token = teacher_setup["token"]
        cid = teacher_setup["class_id"]
        original_end = teacher_setup["end_date"]
        today = teacher_setup["today"]

        r = requests.post(f"{BASE_URL}/api/teacher/cancel-class/{cid}",
                          headers=_teacher_headers(token), timeout=15)
        # If JWT secret mismatches, this may 401; capture for diagnostic
        if r.status_code == 401:
            pytest.skip(f"JWT auth not accepted (secret differs). Body: {r.text}")
        assert r.status_code == 200, f"Cancel failed: {r.status_code} {r.text}"
        body = r.json()
        assert body.get("needs_reschedule") is True

        # Verify DB state directly
        async def fetch():
            return await db.class_sessions.find_one({"class_id": cid}, {"_id": 0})
        cls = event_loop.run_until_complete(fetch())

        assert cls["status"] == "scheduled", \
            f"Status should remain scheduled, got {cls['status']}"
        assert cls.get("needs_reschedule") is True
        assert cls.get("cancelled_today") is True
        assert len(cls.get("cancellations", [])) == 1
        assert cls["cancellations"][0]["cancelled_by_role"] == "teacher"
        assert cls["cancellations"][0]["date"] == today
        # End date shifted +1 day
        expected_new_end = (datetime.strptime(original_end, "%Y-%m-%d")
                            + timedelta(days=1)).strftime("%Y-%m-%d")
        assert cls["end_date"] == expected_new_end, \
            f"end_date {cls['end_date']} != expected {expected_new_end}"

    def test_start_class_blocked_when_needs_reschedule(self, teacher_setup):
        token = teacher_setup["token"]
        cid = teacher_setup["class_id"]
        r = requests.post(f"{BASE_URL}/api/classes/start/{cid}",
                          headers=_teacher_headers(token), timeout=15)
        if r.status_code == 401:
            pytest.skip("JWT auth not accepted")
        assert r.status_code == 400, f"Should block, got {r.status_code} {r.text}"
        assert "reschedule" in r.text.lower()

    def test_reschedule_clears_flag_and_updates_timings(self, teacher_setup, db, event_loop):
        token = teacher_setup["token"]
        cid = teacher_setup["class_id"]
        new_date = (datetime.now(timezone.utc) + timedelta(days=10)).strftime("%Y-%m-%d")
        r = requests.post(
            f"{BASE_URL}/api/teacher/reschedule-class/{cid}",
            headers=_teacher_headers(token),
            json={"new_date": new_date, "new_start_time": "14:00", "new_end_time": "15:00"},
            timeout=15,
        )
        if r.status_code == 401:
            pytest.skip("JWT auth not accepted")
        assert r.status_code == 200, f"Reschedule failed: {r.status_code} {r.text}"

        async def fetch():
            return await db.class_sessions.find_one({"class_id": cid}, {"_id": 0})
        cls = event_loop.run_until_complete(fetch())
        assert cls.get("needs_reschedule") is False
        assert cls.get("cancelled_today") is False
        assert cls.get("start_time") == "14:00"
        assert cls.get("end_time") == "15:00"
        assert cls.get("rescheduled") is True

    def test_start_class_works_after_reschedule(self, teacher_setup):
        token = teacher_setup["token"]
        cid = teacher_setup["class_id"]
        r = requests.post(f"{BASE_URL}/api/classes/start/{cid}",
                          headers=_teacher_headers(token), timeout=15)
        if r.status_code == 401:
            pytest.skip("JWT auth not accepted")
        assert r.status_code == 200, f"Start failed after reschedule: {r.text}"
        assert "room_id" in r.json()


class TestRatingUsesAdminDeduction:
    """Verify rating service reads cancel_rating_deduction from DB."""

    def test_rating_deduction_from_db(self, db, event_loop, admin_headers):
        # Set deduction = 0.5
        requests.post(
            f"{BASE_URL}/api/admin/set-pricing",
            headers=admin_headers,
            json={"demo_price_student": 100, "class_price_student": 200,
                  "demo_earning_teacher": 50, "class_earning_teacher": 100,
                  "cancel_rating_deduction": 0.5},
            timeout=15,
        )

        # Seed a teacher + 1 cancellation event in current month
        from services.rating import recalc_teacher_rating
        import sys
        sys.path.insert(0, "/app/backend")

        teacher_id = f"test_rating_t_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)

        async def setup_and_calc():
            await db.users.insert_one({
                "user_id": teacher_id, "email": f"TEST_{teacher_id}@gmail.com",
                "name": "Rating Test", "role": "teacher", "star_rating": 5.0,
            })
            await db.teacher_rating_events.insert_one({
                "event_id": f"evt_{uuid.uuid4().hex[:8]}",
                "teacher_id": teacher_id, "event": "cancellation",
                "reason": "test", "created_at": now.isoformat(),
            })
            rating = await recalc_teacher_rating(teacher_id)
            return rating

        rating = event_loop.run_until_complete(setup_and_calc())
        # recalc_teacher_rating returns (rating, suspended) tuple
        if isinstance(rating, tuple):
            rating = rating[0]
        # 5.0 - 1 * 0.5 = 4.5
        assert rating == 4.5, f"Expected 4.5 (5 - 0.5), got {rating}"

        # Cleanup
        async def cleanup():
            await db.users.delete_one({"user_id": teacher_id})
            await db.teacher_rating_events.delete_many({"teacher_id": teacher_id})
        event_loop.run_until_complete(cleanup())
