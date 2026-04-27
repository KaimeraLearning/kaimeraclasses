"""
Iteration 35 — Proof workflow + Class actual-duration + Credit blocking
Tests:
1. Class lifecycle: start_class sets started_at_actual; end_class computes actual_duration_minutes = min(student_left, now) - start
2. /classes/student-left/{class_id}: only assigned student can call; idempotent
3. /teacher/submit-proof: computes screenshot_hash (sha256), uses backend actual_duration_minutes,
   supports resubmission after rejection, increments rejection_count, sets credit_blocked when >=2
4. /counsellor/verify-proof rejection increments rejection_count + sets credit_blocked on 2nd rejection
5. /counsellor/proof-history/{class_id}: returns {current, archived}
6. /admin/approve-proof: respects credit_blocked
7. /teacher/dashboard exposes latest_proof_status, latest_proof_admin_status,
   latest_proof_rejection_count, latest_proof_credit_blocked, latest_proof_rejection_reason
"""
import os
import uuid
import hashlib
import base64
import asyncio
from datetime import datetime, timezone, timedelta

import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://skill-exchange-149.preview.emergentagent.com").rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb+srv://info_db_user:3OLEYfaeF1vTJZ1F@cluster0.oxrrozs.mongodb.net/")
DB_NAME = os.environ.get("DB_NAME", "kaimeraclasses")

ADMIN_EMAIL = "info@kaimeralearning.com"
ADMIN_PASS = "solidarity&peace2023"

TEACHER_ID = f"user_TEST_t_{uuid.uuid4().hex[:8]}"
STUDENT_ID = f"user_TEST_s_{uuid.uuid4().hex[:8]}"
COUNS_ID = f"user_TEST_c_{uuid.uuid4().hex[:8]}"
OTHER_STUDENT_ID = f"user_TEST_x_{uuid.uuid4().hex[:8]}"
ASSIGN_ID = f"assign_TEST_{uuid.uuid4().hex[:8]}"
CLASS_ID = f"class_TEST_{uuid.uuid4().hex[:8]}"

TEACHER_TOKEN = f"session_TEST_t_{uuid.uuid4().hex}"
STUDENT_TOKEN = f"session_TEST_s_{uuid.uuid4().hex}"
COUNS_TOKEN = f"session_TEST_c_{uuid.uuid4().hex}"
OTHER_STUDENT_TOKEN = f"session_TEST_x_{uuid.uuid4().hex}"


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module", autouse=True)
def seed_and_cleanup(event_loop):
    """Seed TEST_ users, sessions, assignment, class. Cleanup at end."""
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")

    async def _seed():
        # Users
        common = {"created_at": now.isoformat(), "is_approved": True, "is_verified": True, "credits": 1000.0}
        await db.users.insert_many([
            {"user_id": TEACHER_ID, "email": f"TEST_t_{TEACHER_ID}@kaimera.test", "name": "TEST Teacher", "role": "teacher", **common},
            {"user_id": STUDENT_ID, "email": f"TEST_s_{STUDENT_ID}@kaimera.test", "name": "TEST Student", "role": "student", **common},
            {"user_id": COUNS_ID, "email": f"TEST_c_{COUNS_ID}@kaimera.test", "name": "TEST Counsellor", "role": "counsellor", **common},
            {"user_id": OTHER_STUDENT_ID, "email": f"TEST_x_{OTHER_STUDENT_ID}@kaimera.test", "name": "TEST Other Student", "role": "student", **common},
        ])
        exp = (now + timedelta(days=7)).isoformat()
        await db.user_sessions.insert_many([
            {"user_id": TEACHER_ID, "session_token": TEACHER_TOKEN, "expires_at": exp, "created_at": now.isoformat()},
            {"user_id": STUDENT_ID, "session_token": STUDENT_TOKEN, "expires_at": exp, "created_at": now.isoformat()},
            {"user_id": COUNS_ID, "session_token": COUNS_TOKEN, "expires_at": exp, "created_at": now.isoformat()},
            {"user_id": OTHER_STUDENT_ID, "session_token": OTHER_STUDENT_TOKEN, "expires_at": exp, "created_at": now.isoformat()},
        ])
        # Assignment
        await db.student_teacher_assignments.insert_one({
            "assignment_id": ASSIGN_ID, "student_id": STUDENT_ID, "teacher_id": TEACHER_ID,
            "status": "approved", "payment_status": "paid", "credit_price": 200.0,
            "assigned_days": 1, "assigned_by": COUNS_ID,
            "expires_at": (now + timedelta(days=30)).isoformat(),
            "created_at": now.isoformat()
        })
        # Class scheduled today, time window includes "now" so start works
        ist = now + timedelta(hours=5, minutes=30)
        start_min = max(0, ist.hour*60 + ist.minute - 1)  # 1 min ago in IST
        end_min = min(24*60-1, start_min + 120)
        s_h, s_m = divmod(start_min, 60)
        e_h, e_m = divmod(end_min, 60)
        await db.class_sessions.insert_one({
            "class_id": CLASS_ID, "teacher_id": TEACHER_ID, "teacher_name": "TEST Teacher",
            "title": "TEST Class", "subject": "Math", "class_type": "regular", "is_demo": False,
            "date": today, "end_date": today, "duration_days": 1, "current_day": 1,
            "start_time": f"{s_h:02d}:{s_m:02d}", "end_time": f"{e_h:02d}:{e_m:02d}",
            "credits_required": 200.0, "price_per_day": 200.0,
            "max_students": 1, "assigned_student_id": STUDENT_ID,
            "enrolled_students": [{"user_id": STUDENT_ID, "name": "TEST Student"}],
            "status": "scheduled", "verification_status": "pending",
            "cancellations": [], "cancellation_count": 0, "max_cancellations": 3,
            "created_at": now.isoformat()
        })

    async def _cleanup():
        await db.users.delete_many({"user_id": {"$in": [TEACHER_ID, STUDENT_ID, COUNS_ID, OTHER_STUDENT_ID]}})
        await db.user_sessions.delete_many({"user_id": {"$in": [TEACHER_ID, STUDENT_ID, COUNS_ID, OTHER_STUDENT_ID]}})
        await db.student_teacher_assignments.delete_many({"assignment_id": ASSIGN_ID})
        await db.class_sessions.delete_many({"class_id": CLASS_ID})
        await db.class_proofs.delete_many({"class_id": CLASS_ID})
        await db.class_proof_history.delete_many({"class_id": CLASS_ID})
        await db.notifications.delete_many({"user_id": {"$in": [TEACHER_ID, STUDENT_ID, COUNS_ID, OTHER_STUDENT_ID]}})
        await db.transactions.delete_many({"user_id": {"$in": [TEACHER_ID, STUDENT_ID]}})
        client.close()

    event_loop.run_until_complete(_seed())
    yield db
    event_loop.run_until_complete(_cleanup())


def H(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
    assert r.status_code == 200, f"admin login failed {r.status_code} {r.text[:200]}"
    j = r.json()
    return j.get("token") or j.get("session_token") or j.get("access_token")


# -------------------- TESTS --------------------

class TestClassLifecycle:
    """start_class -> student-left -> end_class — actual_duration tracking"""

    def test_01_start_class_sets_started_at_actual(self, seed_and_cleanup, event_loop):
        r = requests.post(f"{BASE_URL}/api/classes/start/{CLASS_ID}", headers=H(TEACHER_TOKEN))
        assert r.status_code == 200, r.text
        data = r.json()
        assert "jitsi_room" in data
        # Verify in DB
        cls = event_loop.run_until_complete(seed_and_cleanup.class_sessions.find_one({"class_id": CLASS_ID}, {"_id": 0}))
        assert cls.get("started_at_actual"), "started_at_actual not set"
        assert cls.get("status") == "in_progress"
        assert cls.get("ended_at_actual") is None
        assert cls.get("student_left_at") is None

    def test_02_student_left_forbidden_for_teacher(self):
        r = requests.post(f"{BASE_URL}/api/classes/student-left/{CLASS_ID}", headers=H(TEACHER_TOKEN))
        assert r.status_code == 403, f"teacher should not be able to call student-left, got {r.status_code} {r.text[:200]}"

    def test_03_student_left_forbidden_for_other_student(self):
        r = requests.post(f"{BASE_URL}/api/classes/student-left/{CLASS_ID}", headers=H(OTHER_STUDENT_TOKEN))
        assert r.status_code == 403

    def test_04_student_left_records_timestamp(self, seed_and_cleanup, event_loop):
        r = requests.post(f"{BASE_URL}/api/classes/student-left/{CLASS_ID}", headers=H(STUDENT_TOKEN))
        assert r.status_code == 200, r.text
        cls = event_loop.run_until_complete(seed_and_cleanup.class_sessions.find_one({"class_id": CLASS_ID}, {"_id": 0}))
        assert cls.get("student_left_at"), "student_left_at not stored"
        first_ts = cls["student_left_at"]
        # Idempotent — second call should not overwrite
        import time as _t
        _t.sleep(1.2)
        r2 = requests.post(f"{BASE_URL}/api/classes/student-left/{CLASS_ID}", headers=H(STUDENT_TOKEN))
        assert r2.status_code == 200
        cls2 = event_loop.run_until_complete(seed_and_cleanup.class_sessions.find_one({"class_id": CLASS_ID}, {"_id": 0}))
        assert cls2["student_left_at"] == first_ts, "student-left should be idempotent"

    def test_05_end_class_computes_actual_duration(self, seed_and_cleanup, event_loop):
        r = requests.post(f"{BASE_URL}/api/classes/end/{CLASS_ID}", headers=H(TEACHER_TOKEN))
        assert r.status_code == 200, r.text
        cls = event_loop.run_until_complete(seed_and_cleanup.class_sessions.find_one({"class_id": CLASS_ID}, {"_id": 0}))
        assert cls.get("ended_at_actual"), "ended_at_actual missing"
        assert "actual_duration_minutes" in cls
        assert isinstance(cls["actual_duration_minutes"], (int, float))
        assert cls["actual_duration_minutes"] >= 0
        # min(student_left, now) - start should be very small (a few seconds), so < 1 min
        # (started_at and student_left both within seconds of each other)
        assert cls["actual_duration_minutes"] < 5, f"expected small duration, got {cls['actual_duration_minutes']}"


class TestProofSubmissionAndCreditBlocking:
    """Proof submit → reject → resubmit → reject again → approve → no credit because credit_blocked"""

    SCREENSHOT = "data:image/png;base64," + base64.b64encode(b"first-screenshot-bytes").decode()
    EXPECTED_HASH = hashlib.sha256(b"first-screenshot-bytes").hexdigest()

    def test_06_submit_proof_stores_hash_and_actual_duration(self, seed_and_cleanup, event_loop):
        body = {
            "class_id": CLASS_ID,
            "feedback_text": "First submission feedback",
            "student_performance": "good",
            "topics_covered": "Algebra",
            "screenshot_base64": self.SCREENSHOT,
            "meeting_duration_minutes": 999  # client-supplied bogus value, server should override
        }
        r = requests.post(f"{BASE_URL}/api/teacher/submit-proof", headers=H(TEACHER_TOKEN), json=body)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "proof_id" in data
        assert data.get("submission_count") == 1
        assert data.get("credit_blocked") in (False, None)

        proof = event_loop.run_until_complete(
            seed_and_cleanup.class_proofs.find_one({"class_id": CLASS_ID}, {"_id": 0})
        )
        assert proof["screenshot_hash"] == self.EXPECTED_HASH, "sha256 hash mismatch"
        assert proof["meeting_duration_minutes"] != 999, "server should override client duration with backend actual"
        assert proof["rejection_count"] == 0
        assert proof["credit_blocked"] is False
        assert proof["status"] == "pending"

    def test_07_counsellor_rejects_first_proof(self, seed_and_cleanup, event_loop):
        proof = event_loop.run_until_complete(
            seed_and_cleanup.class_proofs.find_one({"class_id": CLASS_ID}, {"_id": 0})
        )
        body = {"proof_id": proof["proof_id"], "approved": False, "reviewer_notes": "Screenshot unclear"}
        r = requests.post(f"{BASE_URL}/api/counsellor/verify-proof", headers=H(COUNS_TOKEN), json=body)
        assert r.status_code == 200, r.text
        updated = event_loop.run_until_complete(
            seed_and_cleanup.class_proofs.find_one({"proof_id": proof["proof_id"]}, {"_id": 0})
        )
        assert updated["status"] == "rejected"
        assert (updated.get("rejection_count") or 0) >= 1, f"rejection_count should be incremented, got {updated.get('rejection_count')}"
        assert updated.get("reviewer_notes") == "Screenshot unclear"

    def test_08_teacher_dashboard_exposes_rejection_fields(self):
        r = requests.get(f"{BASE_URL}/api/teacher/dashboard", headers=H(TEACHER_TOKEN))
        assert r.status_code == 200, r.text
        data = r.json()
        all_classes = (data.get("conducted_classes") or []) + (data.get("todays_sessions") or []) + (data.get("classes") or [])
        target = next((c for c in all_classes if c.get("class_id") == CLASS_ID), None)
        assert target, f"class {CLASS_ID} not found in teacher dashboard"
        assert "latest_proof_status" in target, f"missing latest_proof_status in dashboard class: keys={list(target.keys())}"
        assert target["latest_proof_status"] == "rejected"
        assert "latest_proof_rejection_count" in target
        assert "latest_proof_credit_blocked" in target
        assert "latest_proof_rejection_reason" in target
        assert target["latest_proof_rejection_reason"] != ""

    def test_09_resubmit_proof_after_rejection(self, seed_and_cleanup, event_loop):
        new_screenshot = "data:image/png;base64," + base64.b64encode(b"second-screenshot-bytes").decode()
        body = {
            "class_id": CLASS_ID, "feedback_text": "Resubmitted with clearer screenshot",
            "student_performance": "good", "topics_covered": "Algebra",
            "screenshot_base64": new_screenshot, "meeting_duration_minutes": 0
        }
        r = requests.post(f"{BASE_URL}/api/teacher/submit-proof", headers=H(TEACHER_TOKEN), json=body)
        assert r.status_code == 200, f"resubmission should succeed, got {r.status_code} {r.text[:200]}"
        data = r.json()
        assert data.get("submission_count") == 2, f"expected submission_count=2, got {data.get('submission_count')}"
        assert "resubmission" in data.get("message", "").lower()

        # Old proof archived
        archived = event_loop.run_until_complete(
            seed_and_cleanup.class_proof_history.find_one({"class_id": CLASS_ID}, {"_id": 0})
        )
        assert archived is not None, "old rejected proof should be archived"
        assert archived["status"] == "rejected"

        # New current proof exists, hash differs, rejection_count carried forward
        current = event_loop.run_until_complete(
            seed_and_cleanup.class_proofs.find_one({"class_id": CLASS_ID}, {"_id": 0})
        )
        assert current["screenshot_hash"] == hashlib.sha256(b"second-screenshot-bytes").hexdigest()
        assert (current.get("rejection_count") or 0) == 1, "rejection_count should carry forward to resubmission"

    def test_10_proof_history_endpoint_returns_current_and_archived(self):
        r = requests.get(f"{BASE_URL}/api/counsellor/proof-history/{CLASS_ID}", headers=H(COUNS_TOKEN))
        assert r.status_code == 200, r.text
        data = r.json()
        assert "current" in data and "archived" in data
        assert data["current"] is not None
        assert isinstance(data["archived"], list)
        assert len(data["archived"]) >= 1

    def test_11_second_rejection_sets_credit_blocked(self, seed_and_cleanup, event_loop):
        proof = event_loop.run_until_complete(
            seed_and_cleanup.class_proofs.find_one({"class_id": CLASS_ID}, {"_id": 0})
        )
        body = {"proof_id": proof["proof_id"], "approved": False, "reviewer_notes": "Still not acceptable"}
        r = requests.post(f"{BASE_URL}/api/counsellor/verify-proof", headers=H(COUNS_TOKEN), json=body)
        assert r.status_code == 200, r.text
        updated = event_loop.run_until_complete(
            seed_and_cleanup.class_proofs.find_one({"proof_id": proof["proof_id"]}, {"_id": 0})
        )
        assert updated["status"] == "rejected"
        assert (updated.get("rejection_count") or 0) >= 2
        assert updated.get("credit_blocked") is True, f"credit_blocked should be True after 2nd rejection, got {updated.get('credit_blocked')}"

    def test_12_third_resubmit_carries_credit_blocked_flag(self, seed_and_cleanup, event_loop):
        new_screenshot = "data:image/png;base64," + base64.b64encode(b"third-screenshot-bytes").decode()
        body = {
            "class_id": CLASS_ID, "feedback_text": "Third try",
            "student_performance": "good", "topics_covered": "Algebra",
            "screenshot_base64": new_screenshot, "meeting_duration_minutes": 0
        }
        r = requests.post(f"{BASE_URL}/api/teacher/submit-proof", headers=H(TEACHER_TOKEN), json=body)
        assert r.status_code == 200
        data = r.json()
        assert data.get("credit_blocked") is True, f"3rd submission after 2 rejections should be credit_blocked, got {data.get('credit_blocked')}"
        current = event_loop.run_until_complete(
            seed_and_cleanup.class_proofs.find_one({"class_id": CLASS_ID}, {"_id": 0})
        )
        assert current.get("credit_blocked") is True

    def test_13_admin_approve_respects_credit_blocked(self, seed_and_cleanup, event_loop, admin_token):
        if not admin_token:
            pytest.skip("admin login token not retrieved")
        # 3rd proof currently pending; counsellor must approve to forward to admin
        proof = event_loop.run_until_complete(
            seed_and_cleanup.class_proofs.find_one({"class_id": CLASS_ID}, {"_id": 0})
        )
        # capture teacher earnings before
        teacher_before = event_loop.run_until_complete(
            seed_and_cleanup.users.find_one({"user_id": TEACHER_ID}, {"_id": 0})
        )
        earnings_before = float(teacher_before.get("earnings", 0) or 0)
        credits_before = float(teacher_before.get("credits", 0) or 0)

        # Counsellor approves -> sets admin_status="pending"
        c_body = {"proof_id": proof["proof_id"], "approved": True, "reviewer_notes": "OK from counsellor"}
        rc = requests.post(f"{BASE_URL}/api/counsellor/verify-proof", headers=H(COUNS_TOKEN), json=c_body)
        assert rc.status_code == 200, rc.text

        body = {"proof_id": proof["proof_id"], "approved": True, "admin_notes": "Admin override approval"}
        r = requests.post(f"{BASE_URL}/api/admin/approve-proof", headers=H(admin_token), json=body)
        assert r.status_code == 200, r.text
        updated = event_loop.run_until_complete(
            seed_and_cleanup.class_proofs.find_one({"proof_id": proof["proof_id"]}, {"_id": 0})
        )
        assert updated.get("admin_status") == "approved" or updated.get("status") == "approved"
        # credit_blocked must persist; teacher earnings/credits should NOT change
        teacher_after = event_loop.run_until_complete(
            seed_and_cleanup.users.find_one({"user_id": TEACHER_ID}, {"_id": 0})
        )
        earnings_after = float(teacher_after.get("earnings", 0) or 0)
        credits_after = float(teacher_after.get("credits", 0) or 0)
        assert updated.get("credit_blocked") is True, "credit_blocked flag should still be set"
        assert earnings_after == earnings_before, f"credit-blocked teacher earnings changed: {earnings_before} -> {earnings_after}"
        assert credits_after == credits_before, f"credit-blocked teacher credits changed: {credits_before} -> {credits_after}"
