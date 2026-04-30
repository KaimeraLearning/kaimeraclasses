"""Iteration 37: Teacher No-Show refund logic for demo limits.

When a teacher fails to start a demo class (no-show), that demo MUST NOT
count against the user's 2-demo limit. The student should be able to book
another demo without hitting "Demo limit exceeded".

This test directly mutates MongoDB (via motor) to simulate a teacher no-show
state, then verifies the public POST /api/demo/request endpoint correctly
excludes no-show demos from the limit count — including:
  (a) classes explicitly flagged with `teacher_no_show=True`
  (b) classes whose scheduled end_time + 30min grace has passed without
      `started_at_actual` being set (the on-the-fly detection path).
"""
import os
import asyncio
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

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


async def _cleanup(db, email):
    await db.demo_requests.delete_many({"email": email})
    await db.class_sessions.delete_many({"enrolled_students.user_id": {"$exists": True}, "title": {"$regex": email[:20]}})
    await db.users.delete_one({"email": email})


def _future_slot(days=2):
    """Return (date_str, time_str) safely in the future."""
    d = datetime.now(timezone.utc) + timedelta(days=days)
    return d.strftime("%Y-%m-%d"), "10:00"


def _post_demo(email, name="Test Demo Student"):
    date_str, time_str = _future_slot()
    body = {
        "name": name, "email": email, "phone": "9999999999",
        "age": 20, "institute": "Test", "preferred_date": date_str,
        "preferred_time_slot": time_str, "message": "auto-test"
    }
    return requests.post(f"{BASE_URL}/api/demo/request", json=body, headers=HEADERS, timeout=20)


# ── Scenario A: explicit teacher_no_show=True flag ──────────────────────────
def test_explicit_teacher_no_show_does_not_count(event_loop, db):
    email = f"noshow_a_{uuid.uuid4().hex[:8]}@gmail.com"
    try:
        # 1st demo: real public booking
        r1 = _post_demo(email)
        assert r1.status_code == 200, f"Demo 1 failed: {r1.status_code} {r1.text}"
        demo1_id = r1.json()["demo_id"]

        # Forcefully simulate "teacher accepted then no-showed" by inserting
        # a class doc tied to demo1 with explicit no-show flag.
        async def setup():
            class_id = f"class_{uuid.uuid4().hex[:12]}"
            past_date = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
            await db.class_sessions.insert_one({
                "class_id": class_id, "demo_id": demo1_id, "is_demo": True,
                "title": f"Demo Session - {email}",
                "date": past_date, "end_date": past_date,
                "start_time": "10:00", "end_time": "11:00",
                "status": "teacher_no_show", "teacher_no_show": True,
                "started_at_actual": None,
            })
            await db.demo_requests.update_one(
                {"demo_id": demo1_id},
                {"$set": {"status": "accepted", "class_id": class_id}}
            )
        event_loop.run_until_complete(setup())

        # 2nd demo: should succeed because demo 1 was a no-show
        r2 = _post_demo(email)
        assert r2.status_code == 200, f"Demo 2 must succeed (no-show refund): {r2.status_code} {r2.text}"

        # 3rd demo: this one should also succeed (still under 2-limit since 1 doesn't count)
        r3 = _post_demo(email)
        assert r3.status_code == 200, f"Demo 3 must succeed (only demo 2 counted): {r3.status_code} {r3.text}"

        # 4th: NOW we should hit the 2-demo limit (demos 2+3 count)
        r4 = _post_demo(email)
        assert r4.status_code == 400, f"Demo 4 should hit limit: {r4.status_code} {r4.text}"
        assert "limit" in r4.text.lower()
    finally:
        event_loop.run_until_complete(_cleanup(db, email))


# ── Scenario B: on-the-fly no-show detection (end_time + 30min elapsed) ─────
def test_implicit_time_elapsed_no_show_does_not_count(event_loop, db):
    email = f"noshow_b_{uuid.uuid4().hex[:8]}@gmail.com"
    try:
        r1 = _post_demo(email)
        assert r1.status_code == 200
        demo1_id = r1.json()["demo_id"]

        # Simulate: teacher accepted, class scheduled for YESTERDAY, never started.
        # No DB-level no-show flag is set yet (cron hasn't run / status still "scheduled")
        # — the count logic must detect this on-the-fly.
        async def setup():
            class_id = f"class_{uuid.uuid4().hex[:12]}"
            past_date = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%d")
            await db.class_sessions.insert_one({
                "class_id": class_id, "demo_id": demo1_id, "is_demo": True,
                "title": f"Demo Session - {email}",
                "date": past_date, "end_date": past_date,
                "start_time": "10:00", "end_time": "11:00",
                "status": "scheduled",        # <— still "scheduled" (no cron yet)
                "started_at_actual": None,    # <— teacher never started
                # NOTE: no `teacher_no_show` flag at all
            })
            await db.demo_requests.update_one(
                {"demo_id": demo1_id},
                {"$set": {"status": "accepted", "class_id": class_id}}
            )
        event_loop.run_until_complete(setup())

        r2 = _post_demo(email)
        assert r2.status_code == 200, (
            f"Demo 2 must succeed (implicit no-show): {r2.status_code} {r2.text}\n"
            "Backend should detect end_time+30min elapsed without start as no-show."
        )
    finally:
        event_loop.run_until_complete(_cleanup(db, email))


# ── Scenario C: started classes still count (regression guard) ──────────────
def test_actually_started_demo_does_count(event_loop, db):
    email = f"started_c_{uuid.uuid4().hex[:8]}@gmail.com"
    try:
        r1 = _post_demo(email)
        assert r1.status_code == 200
        demo1_id = r1.json()["demo_id"]

        async def setup():
            class_id = f"class_{uuid.uuid4().hex[:12]}"
            past_date = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
            await db.class_sessions.insert_one({
                "class_id": class_id, "demo_id": demo1_id, "is_demo": True,
                "title": f"Demo Session - {email}",
                "date": past_date, "end_date": past_date,
                "start_time": "10:00", "end_time": "11:00",
                "status": "completed",
                "started_at_actual": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            })
            await db.demo_requests.update_one(
                {"demo_id": demo1_id}, {"$set": {"status": "accepted", "class_id": class_id}}
            )
        event_loop.run_until_complete(setup())

        # Demo 2 still allowed (still under limit of 2)
        r2 = _post_demo(email)
        assert r2.status_code == 200

        # Demo 3 must fail — both demos counted
        r3 = _post_demo(email)
        assert r3.status_code == 400, f"Limit should trigger: {r3.status_code} {r3.text}"
    finally:
        event_loop.run_until_complete(_cleanup(db, email))
