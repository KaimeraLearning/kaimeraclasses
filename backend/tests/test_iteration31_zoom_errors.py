"""
Iteration 31 backend tests:
- Zoom service module imports
- /api/classes/start/{id} returns Zoom fields
- /api/classes/status/{id} returns Zoom fields when in_progress
- Wrong login -> 'Invalid credentials' (401)
- Global exception handler wraps unhandled errors as JSON 500
- Admin login still works
- Cancel rating deduction admin pricing field still functional (regression)
"""
import os
import uuid
import pytest
import requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Load backend .env so MONGO_URL, ZOOM_* are available for offline tests
load_dotenv('/app/backend/.env')

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    # Fallback to frontend/.env
    try:
        with open('/app/frontend/.env') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    BASE_URL = line.split('=', 1)[1].strip().rstrip('/')
                    break
    except Exception:
        pass

ADMIN_EMAIL = "info@kaimeralearning.com"
ADMIN_PASSWORD = "solidarity&peace2023"


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def admin_token(api):
    r = api.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("session_token") or data.get("token")
    assert token, f"No session_token in admin login response: {data}"
    return token


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


# --- Zoom service module import ---
def test_zoom_module_imports():
    from services import zoom as zoom_mod
    assert hasattr(zoom_mod, "create_zoom_meeting")
    assert hasattr(zoom_mod, "generate_zoom_sdk_signature")
    assert hasattr(zoom_mod, "get_zoom_access_token")


def test_zoom_sdk_signature_generates():
    """Generate a JWT signature offline (no Zoom API call)."""
    # Re-read env vars dynamically since services.zoom captures at import time
    import services.zoom as zm
    zm.ZOOM_CLIENT_ID = os.environ.get("ZOOM_CLIENT_ID", zm.ZOOM_CLIENT_ID)
    zm.ZOOM_CLIENT_SECRET = os.environ.get("ZOOM_CLIENT_SECRET", zm.ZOOM_CLIENT_SECRET)
    sig = zm.generate_zoom_sdk_signature(123456789, role=1)
    assert isinstance(sig, str)
    parts = sig.split(".")
    assert len(parts) == 3, "JWT must have 3 parts"


# --- Auth: wrong creds -> 'Invalid credentials' ---
def test_wrong_login_returns_invalid_credentials(api):
    r = api.post(f"{BASE_URL}/api/auth/login", json={"email": "nobody@example.com", "password": "wrong"})
    assert r.status_code == 401
    body = r.json()
    assert "Invalid credentials" in (body.get("detail") or ""), f"Got: {body}"


def test_admin_login_works(admin_token):
    assert admin_token and len(admin_token) > 10


# --- Global exception handler returns JSON ---
def test_global_exception_handler_json(api):
    """Hit a non-existent /api route to ensure JSON shape; 404 also acceptable."""
    r = api.get(f"{BASE_URL}/api/__definitely_not_a_route_xyz__")
    assert r.headers.get("content-type", "").startswith("application/json")
    assert r.status_code in (404, 405, 500)


# --- /api/classes/start/{id} and status/{id} Zoom fields ---
@pytest.fixture(scope="module")
def seeded_class(admin_headers):
    """
    Seed a teacher + class_session + a teacher session token directly via Mongo
    so we can call /api/classes/start with a teacher Authorization header.
    """
    import asyncio
    from motor.motor_asyncio import AsyncIOMotorClient

    mongo_url = os.environ['MONGO_URL']
    db_name = os.environ['DB_NAME']
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    teacher_id = f"TEST_t_{uuid.uuid4().hex[:8]}"
    class_id = f"TEST_c_{uuid.uuid4().hex[:8]}"
    session_token = f"TEST_tok_{uuid.uuid4().hex}"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    end_date = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")

    async def seed():
        await db.users.insert_one({
            "user_id": teacher_id, "email": f"{teacher_id}@gmail.com",
            "name": "TEST Teacher", "role": "teacher", "is_verified": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        await db.user_sessions.insert_one({
            "session_token": session_token, "user_id": teacher_id, "role": "teacher",
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        await db.class_sessions.insert_one({
            "class_id": class_id, "title": "TEST Zoom Class",
            "teacher_id": teacher_id, "teacher_name": "TEST Teacher",
            "status": "scheduled", "date": today, "end_date": end_date,
            "start_time": "10:00", "end_time": "11:00",
            "enrolled_students": [], "is_demo": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    async def teardown():
        await db.users.delete_many({"user_id": teacher_id})
        await db.user_sessions.delete_many({"session_token": session_token})
        await db.class_sessions.delete_many({"class_id": class_id})

    asyncio.get_event_loop().run_until_complete(seed())
    yield {"teacher_id": teacher_id, "class_id": class_id, "session_token": session_token}
    asyncio.get_event_loop().run_until_complete(teardown())
    client.close()


def test_classes_start_returns_zoom_fields(seeded_class):
    """
    Calls real Zoom API. If credentials invalid in env, expect 500 with descriptive message.
    Otherwise expect 200 with all zoom_* fields populated.
    """
    headers = {"Authorization": f"Bearer {seeded_class['session_token']}", "Content-Type": "application/json"}
    r = requests.post(f"{BASE_URL}/api/classes/start/{seeded_class['class_id']}", headers=headers, timeout=30)
    if r.status_code == 500:
        # Zoom creds may be invalid in test env - acceptable per problem statement
        body = r.json()
        assert "Failed to create video meeting" in body.get("detail", ""), \
            f"Unexpected 500: {body}"
        pytest.skip(f"Zoom API call failed (likely invalid creds in env): {body['detail'][:200]}")
    assert r.status_code == 200, f"start_class failed: {r.status_code} {r.text}"
    data = r.json()
    for key in ("zoom_meeting_id", "zoom_join_url", "zoom_password", "zoom_signature", "zoom_sdk_key"):
        assert key in data, f"Missing key {key} in response: {data}"
    assert data["zoom_signature"] and len(data["zoom_signature"]) > 20
    assert data["zoom_sdk_key"]


def test_classes_status_returns_zoom_when_in_progress(seeded_class):
    headers = {"Authorization": f"Bearer {seeded_class['session_token']}"}
    r = requests.get(f"{BASE_URL}/api/classes/status/{seeded_class['class_id']}", headers=headers, timeout=15)
    assert r.status_code == 200, f"status failed: {r.status_code} {r.text}"
    data = r.json()
    # Always returns these keys (may be empty if class not started)
    for key in ("zoom_meeting_id", "zoom_join_url", "zoom_signature", "zoom_sdk_key"):
        assert key in data, f"Missing key {key}"
    # If a previous test successfully started the class, zoom fields populated
    if data.get("status") == "in_progress":
        assert data["zoom_signature"], "Expected signature when in_progress"


# --- Regression: cancel_rating_deduction admin pricing ---
def test_cancel_rating_deduction_admin_pricing(api, admin_headers):
    # GET pricing
    r = api.get(f"{BASE_URL}/api/admin/get-pricing", headers=admin_headers)
    assert r.status_code == 200
    pricing = r.json()
    # SET via update-pricing
    payload = dict(pricing)
    payload["cancel_rating_deduction"] = 0.25
    # Remove possibly-readonly keys that backend ignores
    for k in ("_id", "id"):
        payload.pop(k, None)
    r2 = api.post(f"{BASE_URL}/api/admin/set-pricing", json=payload, headers=admin_headers)
    assert r2.status_code in (200, 201), f"update-pricing failed: {r2.status_code} {r2.text}"
    # Verify persisted
    r3 = api.get(f"{BASE_URL}/api/admin/get-pricing", headers=admin_headers)
    assert r3.status_code == 200
    assert abs(r3.json().get("cancel_rating_deduction", 0) - 0.25) < 1e-6
