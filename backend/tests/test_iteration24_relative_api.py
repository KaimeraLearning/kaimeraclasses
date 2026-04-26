"""Iteration 24 - Verify backend auth endpoints still work (frontend now uses relative /api paths)."""
import os
import requests
import pytest

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://skill-exchange-149.preview.emergentagent.com').rstrip('/')
ADMIN_EMAIL = "info@kaimeralearning.com"
ADMIN_PASS = "solidarity&peace2023"


@pytest.fixture(scope="module")
def session():
    return requests.Session()


@pytest.fixture(scope="module")
def admin_token():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    data = r.json()
    assert data["user"]["role"] == "admin"
    assert "session_token" in data
    return data["session_token"]


@pytest.fixture
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# Auth endpoints
def test_login_admin_success(session):
    r = session.post(f"{BASE_URL}/api/auth/login",
                     json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
    assert r.status_code == 200
    data = r.json()
    assert data["user"]["email"] == ADMIN_EMAIL
    assert data["user"]["role"] == "admin"
    assert isinstance(data.get("session_token"), str) and len(data["session_token"]) > 10


def test_login_invalid_credentials(session):
    r = session.post(f"{BASE_URL}/api/auth/login",
                     json={"email": ADMIN_EMAIL, "password": "wrong-pass"})
    assert r.status_code in (400, 401, 403)


def test_auth_me_with_token(session, admin_token):
    r = requests.get(f"{BASE_URL}/api/auth/me",
                    headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == ADMIN_EMAIL
    assert data["role"] == "admin"


def test_auth_me_without_token(session):
    s = requests.Session()  # fresh session, no cookies
    r = s.get(f"{BASE_URL}/api/auth/me")
    assert r.status_code in (401, 403)


def test_zz_logout_endpoint(session, admin_token):
    r = requests.post(f"{BASE_URL}/api/auth/logout",
                     headers={"Authorization": f"Bearer {admin_token}"})
    # Logout may return 200 or 204
    assert r.status_code in (200, 204)


# Admin dashboard data endpoints (used by AdminDashboard tabs)
def test_admin_all_users_list(session, admin_token):
    r = requests.get(f"{BASE_URL}/api/admin/all-users",
                    headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


def test_admin_classes_list(session, admin_token):
    r = requests.get(f"{BASE_URL}/api/admin/classes",
                    headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200


def test_admin_learning_plans_list(session, admin_token):
    r = requests.get(f"{BASE_URL}/api/admin/learning-plans",
                    headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200


def test_admin_unauthorized_without_token(session):
    s = requests.Session()
    r = s.get(f"{BASE_URL}/api/admin/all-users")
    assert r.status_code in (401, 403)
