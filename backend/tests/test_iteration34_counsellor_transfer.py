"""Iteration 34: Counsellor transfer-student + student-attendance dropdown tests.

Tests:
- Admin login works
- GET /api/counsellor/student-attendance/{id} returns {records, classes} format
- GET /api/counsellor/student-attendance/{id}?class_id=X filters records by class
- POST /api/counsellor/transfer-student creates new assignment for new teacher
- POST /api/counsellor/transfer-student marks old classes as 'transferred'
- POST /api/counsellor/transfer-student deducts old teacher rating via 'transfer_penalty' event
- POST /api/counsellor/transfer-student notifies old teacher, new teacher, and student
- POST /api/counsellor/transfer-student rejects same-teacher transfer (400)
- POST /api/counsellor/transfer-student rejects when no active assignment (404)
- Rating service includes transfer_penalty events in monthly penalty calculation
"""
import os
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://skill-exchange-149.preview.emergentagent.com").rstrip("/")
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


# ---- Admin login sanity ----

class TestAdminAuth:
    def test_admin_login(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert r.status_code == 200, r.text
        body = r.json()
        role = body.get("user", {}).get("role") or body.get("role")
        assert role == "admin"


# ---- Seed: student with two classes, two attendance records, two teachers ----

@pytest.fixture(scope="module")
def transfer_seed(mongo):
    suffix = uuid.uuid4().hex[:8]
    old_teacher_id = f"TEST_oldteacher_{suffix}"
    new_teacher_id = f"TEST_newteacher_{suffix}"
    student_id = f"TEST_student_{suffix}"
    class1_id = f"TEST_class1_{suffix}"
    class2_id = f"TEST_class2_{suffix}"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    next_week = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")
    far_future = (datetime.now(timezone.utc) + timedelta(days=14)).strftime("%Y-%m-%d")

    # Two teachers
    mongo.users.insert_one({
        "user_id": old_teacher_id, "email": f"TEST_oldt_{suffix}@test.com",
        "name": "TEST OldTeacher", "role": "teacher", "is_approved": True,
        "star_rating": 5.0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    mongo.users.insert_one({
        "user_id": new_teacher_id, "email": f"TEST_newt_{suffix}@test.com",
        "name": "TEST NewTeacher", "role": "teacher", "is_approved": True,
        "star_rating": 5.0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    mongo.users.insert_one({
        "user_id": student_id, "email": f"TEST_stu_{suffix}@test.com",
        "name": "TEST Student", "role": "student",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    # Active assignment to old teacher
    assignment_id = f"TEST_assn_{suffix}"
    mongo.student_teacher_assignments.insert_one({
        "assignment_id": assignment_id,
        "teacher_id": old_teacher_id, "teacher_name": "TEST OldTeacher",
        "teacher_email": f"TEST_oldt_{suffix}@test.com",
        "student_id": student_id, "student_name": "TEST Student",
        "student_email": f"TEST_stu_{suffix}@test.com",
        "status": "approved", "payment_status": "paid",
        "credit_price": 1000, "learning_plan_id": "lp1",
        "learning_plan_name": "Math Basics", "learning_plan_price": 1000,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    # Class1: scheduled, ends in 7 days (8 remaining including today)
    mongo.class_sessions.insert_one({
        "class_id": class1_id, "teacher_id": old_teacher_id,
        "assigned_student_id": student_id, "student_name": "TEST Student",
        "title": "TEST Math 101", "status": "scheduled",
        "date": yesterday, "end_date": next_week,
        "enrolled_students": [{"user_id": student_id}],
    })
    # Class2: scheduled, ends in 14 days (15 remaining)
    mongo.class_sessions.insert_one({
        "class_id": class2_id, "teacher_id": old_teacher_id,
        "assigned_student_id": student_id, "student_name": "TEST Student",
        "title": "TEST Science 101", "status": "scheduled",
        "date": yesterday, "end_date": far_future,
        "enrolled_students": [{"user_id": student_id}],
    })

    # Two attendance records (one per class)
    mongo.attendance.insert_one({
        "attendance_id": f"TEST_att1_{suffix}", "student_id": student_id,
        "teacher_id": old_teacher_id, "class_id": class1_id, "class_title": "TEST Math 101",
        "date": yesterday, "status": "present",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    mongo.attendance.insert_one({
        "attendance_id": f"TEST_att2_{suffix}", "student_id": student_id,
        "teacher_id": old_teacher_id, "class_id": class2_id, "class_title": "TEST Science 101",
        "date": yesterday, "status": "absent",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    yield {
        "old_teacher_id": old_teacher_id, "new_teacher_id": new_teacher_id,
        "student_id": student_id, "class1_id": class1_id, "class2_id": class2_id,
        "assignment_id": assignment_id, "today": today, "suffix": suffix,
    }

    # Teardown
    mongo.users.delete_many({"user_id": {"$in": [old_teacher_id, new_teacher_id, student_id]}})
    mongo.student_teacher_assignments.delete_many({"$or": [
        {"teacher_id": old_teacher_id}, {"teacher_id": new_teacher_id},
        {"student_id": student_id},
    ]})
    mongo.class_sessions.delete_many({"$or": [
        {"teacher_id": old_teacher_id}, {"teacher_id": new_teacher_id},
    ]})
    mongo.attendance.delete_many({"student_id": student_id})
    mongo.notifications.delete_many({"user_id": {"$in": [old_teacher_id, new_teacher_id, student_id]}})
    mongo.teacher_rating_events.delete_many({"teacher_id": {"$in": [old_teacher_id, new_teacher_id]}})


# ---- Counsellor student-attendance: returns {records, classes} ----

class TestStudentAttendance:
    def test_returns_records_and_classes_format(self, admin_session, transfer_seed):
        sid = transfer_seed["student_id"]
        r = admin_session.get(f"{API}/counsellor/student-attendance/{sid}")
        assert r.status_code == 200, r.text
        body = r.json()
        assert isinstance(body, dict), f"expected dict, got {type(body)}: {body}"
        assert "records" in body
        assert "classes" in body
        assert isinstance(body["records"], list)
        assert isinstance(body["classes"], list)
        # Should contain both attendance records seeded
        assert len(body["records"]) >= 2
        # Should contain both classes for dropdown
        class_ids = {c["class_id"] for c in body["classes"]}
        assert transfer_seed["class1_id"] in class_ids
        assert transfer_seed["class2_id"] in class_ids
        # Each dropdown entry has class_id + class_title
        for c in body["classes"]:
            assert "class_id" in c and "class_title" in c

    def test_filter_by_class_id(self, admin_session, transfer_seed):
        sid = transfer_seed["student_id"]
        c1 = transfer_seed["class1_id"]
        r = admin_session.get(f"{API}/counsellor/student-attendance/{sid}?class_id={c1}")
        assert r.status_code == 200, r.text
        body = r.json()
        assert "records" in body
        # All records should belong to class1 only
        for rec in body["records"]:
            assert rec.get("class_id") == c1
        # classes dropdown should still show both classes (not filtered)
        assert len(body["classes"]) >= 2


# ---- Transfer student endpoint ----

class TestTransferStudent:
    def test_same_teacher_rejected(self, admin_session, transfer_seed):
        r = admin_session.post(f"{API}/counsellor/transfer-student", json={
            "student_id": transfer_seed["student_id"],
            "old_teacher_id": transfer_seed["old_teacher_id"],
            "new_teacher_id": transfer_seed["old_teacher_id"],
        })
        assert r.status_code == 400, r.text
        assert "different" in r.text.lower() or "same" in r.text.lower()

    def test_missing_fields_rejected(self, admin_session, transfer_seed):
        r = admin_session.post(f"{API}/counsellor/transfer-student", json={
            "student_id": transfer_seed["student_id"],
        })
        assert r.status_code == 400

    def test_unknown_teacher_rejected(self, admin_session, transfer_seed):
        r = admin_session.post(f"{API}/counsellor/transfer-student", json={
            "student_id": transfer_seed["student_id"],
            "old_teacher_id": transfer_seed["old_teacher_id"],
            "new_teacher_id": "TEST_does_not_exist_xyz",
        })
        assert r.status_code == 404

    def test_transfer_success_full_flow(self, admin_session, transfer_seed, mongo):
        """End-to-end: new assignment created, old classes -> transferred,
        rating event recorded, notifications sent to all 3 parties."""
        r = admin_session.post(f"{API}/counsellor/transfer-student", json={
            "student_id": transfer_seed["student_id"],
            "old_teacher_id": transfer_seed["old_teacher_id"],
            "new_teacher_id": transfer_seed["new_teacher_id"],
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert "new_assignment_id" in body
        assert "old_teacher_rating" in body
        assert isinstance(body["old_teacher_rating"], (int, float))
        new_assn_id = body["new_assignment_id"]

        # 1. New assignment exists for new teacher
        new_assn = mongo.student_teacher_assignments.find_one({"assignment_id": new_assn_id})
        assert new_assn is not None
        assert new_assn["teacher_id"] == transfer_seed["new_teacher_id"]
        assert new_assn["student_id"] == transfer_seed["student_id"]
        assert new_assn["status"] == "approved"
        assert new_assn["payment_method"] == "transferred"
        # Remaining days: class1 (~8) + class2 (~15) = 23ish; allow flexible range
        assert new_assn["assigned_days"] >= 15, f"expected >=15 days, got {new_assn['assigned_days']}"
        assert new_assn.get("transferred_from_teacher_id") == transfer_seed["old_teacher_id"]

        # 2. Old assignment marked transferred
        old_assn = mongo.student_teacher_assignments.find_one(
            {"assignment_id": transfer_seed["assignment_id"]}
        )
        assert old_assn["status"] == "transferred"
        assert old_assn.get("transferred_to_teacher_id") == transfer_seed["new_teacher_id"]

        # 3. Old classes marked transferred
        c1 = mongo.class_sessions.find_one({"class_id": transfer_seed["class1_id"]})
        c2 = mongo.class_sessions.find_one({"class_id": transfer_seed["class2_id"]})
        assert c1["status"] == "transferred"
        assert c2["status"] == "transferred"
        assert c1.get("transferred_to") == transfer_seed["new_teacher_id"]

        # 4. Rating event recorded as 'transfer_penalty'
        ev = mongo.teacher_rating_events.find_one({
            "teacher_id": transfer_seed["old_teacher_id"], "event": "transfer_penalty"
        })
        assert ev is not None, "transfer_penalty event was not recorded"

        # 5. Notifications sent to all three parties
        old_t_notif = mongo.notifications.find_one({
            "user_id": transfer_seed["old_teacher_id"], "type": "student_transferred_out"
        })
        new_t_notif = mongo.notifications.find_one({
            "user_id": transfer_seed["new_teacher_id"], "type": "student_transferred_in"
        })
        stu_notif = mongo.notifications.find_one({
            "user_id": transfer_seed["student_id"], "type": "teacher_changed"
        })
        assert old_t_notif is not None
        assert new_t_notif is not None
        assert stu_notif is not None

    def test_transfer_no_active_assignment(self, admin_session, transfer_seed):
        """After previous transfer, the old assignment is no longer 'approved' so
        retrying with same old teacher should yield 404."""
        r = admin_session.post(f"{API}/counsellor/transfer-student", json={
            "student_id": transfer_seed["student_id"],
            "old_teacher_id": transfer_seed["old_teacher_id"],
            "new_teacher_id": transfer_seed["new_teacher_id"],
        })
        assert r.status_code == 404


# ---- Rating service includes transfer_penalty in monthly penalty ----

class TestRatingTransferPenalty:
    def test_transfer_penalty_reduces_rating(self, mongo, transfer_seed):
        """After the successful transfer, the old teacher's rating should reflect
        a transfer_penalty deduction (admin pricing default 0.2)."""
        old_t = mongo.users.find_one({"user_id": transfer_seed["old_teacher_id"]})
        assert old_t is not None
        # If rating was recalculated, monthly_cancellations field should exist
        details = old_t.get("rating_details", {})
        # Penalty should be > 0 since transfer_penalty event was recorded
        assert details.get("penalty", 0) > 0 or old_t.get("star_rating", 5.0) < 5.0, \
            f"Expected rating penalty >0 or star_rating <5.0, got details={details}, star={old_t.get('star_rating')}"
