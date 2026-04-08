"""
Test suite for Demo Booking & Tracking workflow
Tests: Demo request, Live Sheet, Accept/Assign, Feedback, History, Admin grant extra
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "info@kaimeralearning.com"
ADMIN_PASSWORD = "solidarity&peace2023"
TEACHER_EMAIL = "teacher1@kaimera.com"
TEACHER_PASSWORD = "password123"
STUDENT_EMAIL = "student1@kaimera.com"
STUDENT_PASSWORD = "password123"
COUNSELLOR_EMAIL = "counsellor1@kaimera.com"
COUNSELLOR_PASSWORD = "password123"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def admin_session(api_client):
    """Get admin session"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    session = requests.Session()
    session.cookies.update(response.cookies)
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def teacher_session(api_client):
    """Get teacher session"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEACHER_EMAIL,
        "password": TEACHER_PASSWORD
    })
    assert response.status_code == 200, f"Teacher login failed: {response.text}"
    session = requests.Session()
    session.cookies.update(response.cookies)
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def student_session(api_client):
    """Get student session"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": STUDENT_EMAIL,
        "password": STUDENT_PASSWORD
    })
    assert response.status_code == 200, f"Student login failed: {response.text}"
    session = requests.Session()
    session.cookies.update(response.cookies)
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def counsellor_session(api_client):
    """Get counsellor session"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": COUNSELLOR_EMAIL,
        "password": COUNSELLOR_PASSWORD
    })
    assert response.status_code == 200, f"Counsellor login failed: {response.text}"
    session = requests.Session()
    session.cookies.update(response.cookies)
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestDemoRequestPublicEndpoint:
    """Test POST /api/demo/request - Public endpoint (no auth required)"""
    
    def test_demo_request_success(self, api_client):
        """Submit a demo request with all required fields"""
        unique_email = f"test_demo_{uuid.uuid4().hex[:8]}@example.com"
        payload = {
            "name": "Test Demo User",
            "email": unique_email,
            "phone": "+91 9876543210",
            "age": 16,
            "institute": "Test School",
            "preferred_date": "2026-02-15",
            "preferred_time_slot": "10:00",
            "message": "I want to learn math"
        }
        response = api_client.post(f"{BASE_URL}/api/demo/request", json=payload)
        assert response.status_code == 200, f"Demo request failed: {response.text}"
        data = response.json()
        assert "demo_id" in data
        assert data["message"] == "Demo request submitted successfully!"
        print(f"✓ Demo request created: {data['demo_id']}")
    
    def test_demo_request_missing_phone(self, api_client):
        """Demo request should fail without phone"""
        payload = {
            "name": "Test User",
            "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
            "preferred_date": "2026-02-15",
            "preferred_time_slot": "10:00"
        }
        response = api_client.post(f"{BASE_URL}/api/demo/request", json=payload)
        assert response.status_code == 422, "Should fail without phone"
        print("✓ Demo request correctly rejects missing phone")
    
    def test_demo_request_invalid_email(self, api_client):
        """Demo request should fail with invalid email"""
        payload = {
            "name": "Test User",
            "email": "invalid-email",
            "phone": "+91 9876543210",
            "preferred_date": "2026-02-15",
            "preferred_time_slot": "10:00"
        }
        response = api_client.post(f"{BASE_URL}/api/demo/request", json=payload)
        assert response.status_code == 422, "Should fail with invalid email"
        print("✓ Demo request correctly rejects invalid email")


class TestDemoLiveSheet:
    """Test GET /api/demo/live-sheet - Teacher/Counsellor/Admin access"""
    
    def test_live_sheet_teacher_access(self, teacher_session):
        """Teacher can access live sheet"""
        response = teacher_session.get(f"{BASE_URL}/api/demo/live-sheet")
        assert response.status_code == 200, f"Teacher live sheet failed: {response.text}"
        data = response.json()
        assert "demos" in data
        assert isinstance(data["demos"], list)
        # Teachers don't get teacher list
        print(f"✓ Teacher can access live sheet, {len(data['demos'])} pending demos")
    
    def test_live_sheet_counsellor_access(self, counsellor_session):
        """Counsellor can access live sheet with teacher list"""
        response = counsellor_session.get(f"{BASE_URL}/api/demo/live-sheet")
        assert response.status_code == 200, f"Counsellor live sheet failed: {response.text}"
        data = response.json()
        assert "demos" in data
        assert "teachers" in data
        assert isinstance(data["teachers"], list)
        print(f"✓ Counsellor can access live sheet with {len(data['teachers'])} teachers")
    
    def test_live_sheet_admin_access(self, admin_session):
        """Admin can access live sheet with teacher list"""
        response = admin_session.get(f"{BASE_URL}/api/demo/live-sheet")
        assert response.status_code == 200, f"Admin live sheet failed: {response.text}"
        data = response.json()
        assert "demos" in data
        assert "teachers" in data
        print(f"✓ Admin can access live sheet")
    
    def test_live_sheet_student_denied(self, student_session):
        """Student cannot access live sheet"""
        response = student_session.get(f"{BASE_URL}/api/demo/live-sheet")
        assert response.status_code == 403, "Student should be denied"
        print("✓ Student correctly denied access to live sheet")


class TestDemoAcceptByTeacher:
    """Test POST /api/demo/accept/{demo_id} - Teacher accepts demo"""
    
    @pytest.fixture
    def new_demo_for_accept(self, api_client):
        """Create a fresh demo request for accept test"""
        unique_email = f"accept_test_{uuid.uuid4().hex[:8]}@example.com"
        payload = {
            "name": "Accept Test Student",
            "email": unique_email,
            "phone": "+91 1234567890",
            "preferred_date": "2026-02-20",
            "preferred_time_slot": "14:00"
        }
        response = api_client.post(f"{BASE_URL}/api/demo/request", json=payload)
        assert response.status_code == 200
        return response.json()["demo_id"], unique_email
    
    def test_teacher_accept_demo(self, teacher_session, new_demo_for_accept):
        """Teacher accepts a demo - should create class and student"""
        demo_id, student_email = new_demo_for_accept
        response = teacher_session.post(f"{BASE_URL}/api/demo/accept/{demo_id}")
        assert response.status_code == 200, f"Accept failed: {response.text}"
        data = response.json()
        assert "class_id" in data
        assert "student_id" in data
        assert "message" in data
        # New student should have credentials
        if "student_credentials" in data:
            assert data["student_credentials"]["email"] == student_email
            print(f"✓ New student created: {data['student_credentials']}")
        print(f"✓ Teacher accepted demo, class created: {data['class_id']}")
    
    def test_accept_nonexistent_demo(self, teacher_session):
        """Accept non-existent demo should fail"""
        response = teacher_session.post(f"{BASE_URL}/api/demo/accept/nonexistent_demo_id")
        assert response.status_code == 404
        print("✓ Accept non-existent demo correctly returns 404")
    
    def test_student_cannot_accept(self, student_session, api_client):
        """Student cannot accept demos"""
        # Create a demo first
        unique_email = f"student_accept_test_{uuid.uuid4().hex[:8]}@example.com"
        payload = {
            "name": "Test",
            "email": unique_email,
            "phone": "+91 1111111111",
            "preferred_date": "2026-02-25",
            "preferred_time_slot": "11:00"
        }
        create_resp = api_client.post(f"{BASE_URL}/api/demo/request", json=payload)
        demo_id = create_resp.json()["demo_id"]
        
        response = student_session.post(f"{BASE_URL}/api/demo/accept/{demo_id}")
        assert response.status_code == 403, "Student should be denied"
        print("✓ Student correctly denied from accepting demos")


class TestDemoAssignByCounsellor:
    """Test POST /api/demo/assign - Counsellor assigns demo to teacher"""
    
    @pytest.fixture
    def new_demo_for_assign(self, api_client):
        """Create a fresh demo request for assign test"""
        unique_email = f"assign_test_{uuid.uuid4().hex[:8]}@example.com"
        payload = {
            "name": "Assign Test Student",
            "email": unique_email,
            "phone": "+91 2222222222",
            "preferred_date": "2026-02-22",
            "preferred_time_slot": "15:00"
        }
        response = api_client.post(f"{BASE_URL}/api/demo/request", json=payload)
        assert response.status_code == 200
        return response.json()["demo_id"]
    
    @pytest.fixture
    def teacher_id(self, counsellor_session):
        """Get a teacher ID from live sheet"""
        response = counsellor_session.get(f"{BASE_URL}/api/demo/live-sheet")
        data = response.json()
        if data["teachers"]:
            return data["teachers"][0]["user_id"]
        pytest.skip("No teachers available for assignment")
    
    def test_counsellor_assign_demo(self, counsellor_session, new_demo_for_assign, teacher_id):
        """Counsellor assigns demo to teacher"""
        payload = {
            "demo_id": new_demo_for_assign,
            "teacher_id": teacher_id
        }
        response = counsellor_session.post(f"{BASE_URL}/api/demo/assign", json=payload)
        assert response.status_code == 200, f"Assign failed: {response.text}"
        data = response.json()
        assert "message" in data
        print(f"✓ Counsellor assigned demo: {data['message']}")
    
    def test_admin_can_assign_demo(self, admin_session, api_client):
        """Admin can also assign demos"""
        # Create demo
        unique_email = f"admin_assign_{uuid.uuid4().hex[:8]}@example.com"
        payload = {
            "name": "Admin Assign Test",
            "email": unique_email,
            "phone": "+91 3333333333",
            "preferred_date": "2026-02-23",
            "preferred_time_slot": "16:00"
        }
        create_resp = api_client.post(f"{BASE_URL}/api/demo/request", json=payload)
        demo_id = create_resp.json()["demo_id"]
        
        # Get teacher
        sheet_resp = admin_session.get(f"{BASE_URL}/api/demo/live-sheet")
        teachers = sheet_resp.json()["teachers"]
        if not teachers:
            pytest.skip("No teachers available")
        
        assign_payload = {
            "demo_id": demo_id,
            "teacher_id": teachers[0]["user_id"]
        }
        response = admin_session.post(f"{BASE_URL}/api/demo/assign", json=assign_payload)
        assert response.status_code == 200, f"Admin assign failed: {response.text}"
        print("✓ Admin can assign demos")
    
    def test_teacher_cannot_assign(self, teacher_session, api_client):
        """Teacher cannot assign demos"""
        unique_email = f"teacher_assign_{uuid.uuid4().hex[:8]}@example.com"
        payload = {
            "name": "Teacher Assign Test",
            "email": unique_email,
            "phone": "+91 4444444444",
            "preferred_date": "2026-02-24",
            "preferred_time_slot": "17:00"
        }
        create_resp = api_client.post(f"{BASE_URL}/api/demo/request", json=payload)
        demo_id = create_resp.json()["demo_id"]
        
        assign_payload = {
            "demo_id": demo_id,
            "teacher_id": "some_teacher_id"
        }
        response = teacher_session.post(f"{BASE_URL}/api/demo/assign", json=assign_payload)
        assert response.status_code == 403, "Teacher should be denied"
        print("✓ Teacher correctly denied from assigning demos")


class TestDemoFeedback:
    """Test POST /api/demo/feedback - Student submits feedback"""
    
    def test_student_my_demos(self, student_session):
        """Student can get their demos"""
        response = student_session.get(f"{BASE_URL}/api/demo/my-demos")
        assert response.status_code == 200, f"My demos failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Student can view their demos: {len(data)} demos")
    
    def test_feedback_requires_student_role(self, teacher_session):
        """Only students can submit feedback"""
        payload = {
            "demo_id": "some_demo_id",
            "rating": 5,
            "feedback_text": "Great session!"
        }
        response = teacher_session.post(f"{BASE_URL}/api/demo/feedback", json=payload)
        assert response.status_code == 403, "Teacher should be denied"
        print("✓ Non-students correctly denied from submitting feedback")


class TestDemoLimits:
    """Test demo limits (max 3 per email) and admin grant extra"""
    
    def test_demo_limit_enforcement(self, api_client):
        """Test that demo limit is enforced"""
        unique_email = f"limit_test_{uuid.uuid4().hex[:8]}@example.com"
        
        # Create 3 demos
        for i in range(3):
            payload = {
                "name": f"Limit Test {i+1}",
                "email": unique_email,
                "phone": "+91 5555555555",
                "preferred_date": f"2026-03-0{i+1}",
                "preferred_time_slot": "10:00"
            }
            response = api_client.post(f"{BASE_URL}/api/demo/request", json=payload)
            assert response.status_code == 200, f"Demo {i+1} should succeed"
        
        # 4th demo should fail
        payload = {
            "name": "Limit Test 4",
            "email": unique_email,
            "phone": "+91 5555555555",
            "preferred_date": "2026-03-04",
            "preferred_time_slot": "10:00"
        }
        response = api_client.post(f"{BASE_URL}/api/demo/request", json=payload)
        assert response.status_code == 400, "4th demo should be rejected"
        assert "Maximum" in response.json()["detail"]
        print("✓ Demo limit (max 3) correctly enforced")
    
    def test_admin_grant_extra_demo(self, admin_session, api_client):
        """Admin can grant extra demo"""
        unique_email = f"extra_test_{uuid.uuid4().hex[:8]}@example.com"
        
        # Create 3 demos first
        for i in range(3):
            payload = {
                "name": f"Extra Test {i+1}",
                "email": unique_email,
                "phone": "+91 6666666666",
                "preferred_date": f"2026-04-0{i+1}",
                "preferred_time_slot": "11:00"
            }
            api_client.post(f"{BASE_URL}/api/demo/request", json=payload)
        
        # Grant extra
        grant_payload = {"email": unique_email}
        response = admin_session.post(f"{BASE_URL}/api/admin/grant-demo-extra", json=grant_payload)
        assert response.status_code == 200, f"Grant extra failed: {response.text}"
        print(f"✓ Admin granted extra demo: {response.json()['message']}")
        
        # Now 4th demo should succeed
        payload = {
            "name": "Extra Test 4",
            "email": unique_email,
            "phone": "+91 6666666666",
            "preferred_date": "2026-04-04",
            "preferred_time_slot": "11:00"
        }
        response = api_client.post(f"{BASE_URL}/api/demo/request", json=payload)
        assert response.status_code == 200, "4th demo should succeed after extra grant"
        print("✓ Extra demo grant allows 4th demo")
    
    def test_non_admin_cannot_grant_extra(self, counsellor_session):
        """Non-admin cannot grant extra demo"""
        payload = {"email": "test@example.com"}
        response = counsellor_session.post(f"{BASE_URL}/api/admin/grant-demo-extra", json=payload)
        assert response.status_code == 403, "Counsellor should be denied"
        print("✓ Non-admin correctly denied from granting extra demos")


class TestHistoryEndpoints:
    """Test history search and profile endpoints"""
    
    def test_history_search(self, admin_session):
        """Admin can search history"""
        response = admin_session.get(f"{BASE_URL}/api/history/search?q=demo")
        assert response.status_code == 200, f"History search failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ History search returned {len(data)} logs")
    
    def test_history_search_empty_query(self, counsellor_session):
        """Counsellor can search with empty query (returns all)"""
        response = counsellor_session.get(f"{BASE_URL}/api/history/search?q=")
        assert response.status_code == 200
        print("✓ History search with empty query works")
    
    def test_history_users_list(self, admin_session):
        """Admin can get users list for history"""
        response = admin_session.get(f"{BASE_URL}/api/history/users")
        assert response.status_code == 200, f"History users failed: {response.text}"
        data = response.json()
        assert "students" in data
        assert "teachers" in data
        print(f"✓ History users: {len(data['students'])} students, {len(data['teachers'])} teachers")
    
    def test_student_history_profile(self, admin_session):
        """Admin can view student history profile"""
        # Get a student ID first
        users_resp = admin_session.get(f"{BASE_URL}/api/history/users")
        students = users_resp.json()["students"]
        if not students:
            pytest.skip("No students available")
        
        student_id = students[0]["user_id"]
        response = admin_session.get(f"{BASE_URL}/api/history/student/{student_id}")
        assert response.status_code == 200, f"Student history failed: {response.text}"
        data = response.json()
        assert "student" in data
        assert "demos" in data
        assert "classes" in data
        assert "logs" in data
        print(f"✓ Student history profile loaded: {data['student']['name']}")
    
    def test_teacher_history_profile(self, counsellor_session):
        """Counsellor can view teacher history profile"""
        users_resp = counsellor_session.get(f"{BASE_URL}/api/history/users")
        teachers = users_resp.json()["teachers"]
        if not teachers:
            pytest.skip("No teachers available")
        
        teacher_id = teachers[0]["user_id"]
        response = counsellor_session.get(f"{BASE_URL}/api/history/teacher/{teacher_id}")
        assert response.status_code == 200, f"Teacher history failed: {response.text}"
        data = response.json()
        assert "teacher" in data
        assert "demos" in data
        assert "classes" in data
        assert "logs" in data
        print(f"✓ Teacher history profile loaded: {data['teacher']['name']}")
    
    def test_student_cannot_access_history(self, student_session):
        """Student cannot access history endpoints"""
        response = student_session.get(f"{BASE_URL}/api/history/search?q=test")
        assert response.status_code == 403, "Student should be denied"
        print("✓ Student correctly denied from history endpoints")


class TestDemoAllEndpoint:
    """Test GET /api/demo/all - Admin/Counsellor only"""
    
    def test_admin_get_all_demos(self, admin_session):
        """Admin can get all demos"""
        response = admin_session.get(f"{BASE_URL}/api/demo/all")
        assert response.status_code == 200, f"Get all demos failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Admin can view all {len(data)} demos")
    
    def test_counsellor_get_all_demos(self, counsellor_session):
        """Counsellor can get all demos"""
        response = counsellor_session.get(f"{BASE_URL}/api/demo/all")
        assert response.status_code == 200
        print("✓ Counsellor can view all demos")
    
    def test_teacher_cannot_get_all_demos(self, teacher_session):
        """Teacher cannot get all demos"""
        response = teacher_session.get(f"{BASE_URL}/api/demo/all")
        assert response.status_code == 403, "Teacher should be denied"
        print("✓ Teacher correctly denied from viewing all demos")


class TestFeedbackPendingEndpoint:
    """Test GET /api/demo/feedback-pending - Counsellor/Admin only"""
    
    def test_counsellor_get_pending_feedback(self, counsellor_session):
        """Counsellor can get pending feedback"""
        response = counsellor_session.get(f"{BASE_URL}/api/demo/feedback-pending")
        assert response.status_code == 200, f"Pending feedback failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Counsellor can view {len(data)} pending feedbacks")
    
    def test_student_cannot_get_pending_feedback(self, student_session):
        """Student cannot get pending feedback"""
        response = student_session.get(f"{BASE_URL}/api/demo/feedback-pending")
        assert response.status_code == 403, "Student should be denied"
        print("✓ Student correctly denied from pending feedback")
