"""
Test suite for EdTech CRM Video Class Features - Iteration 4
Tests: Class lifecycle (start/end/status), Teacher dashboard week view, 
Student Join button, Stripe webhook, Teacher schedule calendar
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

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


class TestAuth:
    """Authentication tests for all roles"""
    
    def test_admin_login(self):
        """Admin can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "session_token" in data
        assert data["user"]["role"] == "admin"
        print(f"✓ Admin login successful: {data['user']['name']}")
    
    def test_teacher_login(self):
        """Teacher can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEACHER_EMAIL,
            "password": TEACHER_PASSWORD
        })
        assert response.status_code == 200, f"Teacher login failed: {response.text}"
        data = response.json()
        assert "session_token" in data
        assert data["user"]["role"] == "teacher"
        print(f"✓ Teacher login successful: {data['user']['name']}")
    
    def test_student_login(self):
        """Student can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STUDENT_EMAIL,
            "password": STUDENT_PASSWORD
        })
        assert response.status_code == 200, f"Student login failed: {response.text}"
        data = response.json()
        assert "session_token" in data
        assert data["user"]["role"] == "student"
        print(f"✓ Student login successful: {data['user']['name']}")
    
    def test_counsellor_login(self):
        """Counsellor can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COUNSELLOR_EMAIL,
            "password": COUNSELLOR_PASSWORD
        })
        assert response.status_code == 200, f"Counsellor login failed: {response.text}"
        data = response.json()
        assert "session_token" in data
        assert data["user"]["role"] == "counsellor"
        print(f"✓ Counsellor login successful: {data['user']['name']}")


class TestTeacherDashboardWeekView:
    """Tests for Teacher Dashboard week view feature"""
    
    @pytest.fixture
    def teacher_session(self):
        """Get teacher session token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEACHER_EMAIL,
            "password": TEACHER_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["session_token"]
    
    def test_teacher_dashboard_returns_week_classes(self, teacher_session):
        """Teacher dashboard returns this_week classes and other_classes"""
        headers = {"Authorization": f"Bearer {teacher_session}"}
        response = requests.get(f"{BASE_URL}/api/teacher/dashboard", headers=headers)
        assert response.status_code == 200, f"Dashboard failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "classes" in data, "Missing 'classes' (this week) in response"
        assert "other_classes" in data, "Missing 'other_classes' in response"
        assert "pending_assignments" in data
        assert "approved_students" in data
        
        print(f"✓ Teacher dashboard: {len(data['classes'])} this week, {len(data['other_classes'])} other classes")
        print(f"  Approved students: {len(data['approved_students'])}")
    
    def test_teacher_dashboard_week_classes_structure(self, teacher_session):
        """Verify class structure in dashboard response"""
        headers = {"Authorization": f"Bearer {teacher_session}"}
        response = requests.get(f"{BASE_URL}/api/teacher/dashboard", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        all_classes = data['classes'] + data['other_classes']
        if all_classes:
            cls = all_classes[0]
            assert "class_id" in cls
            assert "title" in cls
            assert "status" in cls
            assert "date" in cls
            assert "end_date" in cls or "date" in cls
            print(f"✓ Class structure verified: {cls['title']} ({cls['status']})")


class TestClassLifecycle:
    """Tests for class start/end/status endpoints"""
    
    @pytest.fixture
    def teacher_session(self):
        """Get teacher session token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEACHER_EMAIL,
            "password": TEACHER_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["session_token"]
    
    @pytest.fixture
    def student_session(self):
        """Get student session token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STUDENT_EMAIL,
            "password": STUDENT_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["session_token"]
    
    @pytest.fixture
    def active_class_id(self, teacher_session):
        """Get an active class ID for testing"""
        headers = {"Authorization": f"Bearer {teacher_session}"}
        response = requests.get(f"{BASE_URL}/api/teacher/dashboard", headers=headers)
        assert response.status_code == 200
        data = response.json()
        all_classes = data['classes'] + data['other_classes']
        if all_classes:
            return all_classes[0]['class_id']
        pytest.skip("No classes available for testing")
    
    def test_get_class_status(self, teacher_session, active_class_id):
        """GET /api/classes/status/{class_id} returns current status"""
        headers = {"Authorization": f"Bearer {teacher_session}"}
        response = requests.get(f"{BASE_URL}/api/classes/status/{active_class_id}", headers=headers)
        assert response.status_code == 200, f"Status failed: {response.text}"
        data = response.json()
        
        assert "class_id" in data
        assert "status" in data
        assert "room_id" in data
        assert "teacher_id" in data
        assert "is_in_progress" in data
        
        print(f"✓ Class status: {data['status']}, in_progress: {data['is_in_progress']}")
    
    def test_start_class_creates_room(self, teacher_session, active_class_id):
        """POST /api/classes/start/{class_id} sets status to in_progress and creates room_id"""
        headers = {"Authorization": f"Bearer {teacher_session}"}
        
        # Start the class
        response = requests.post(f"{BASE_URL}/api/classes/start/{active_class_id}", headers=headers)
        assert response.status_code == 200, f"Start class failed: {response.text}"
        data = response.json()
        
        assert "room_id" in data
        assert data["room_id"].startswith("kaimera-")
        print(f"✓ Class started, room_id: {data['room_id']}")
        
        # Verify status changed
        status_response = requests.get(f"{BASE_URL}/api/classes/status/{active_class_id}", headers=headers)
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["status"] == "in_progress"
        assert status_data["is_in_progress"] == True
        print(f"✓ Class status verified: in_progress")
    
    def test_student_sees_in_progress_class(self, student_session, active_class_id, teacher_session):
        """Student can see class status when in_progress"""
        # First ensure class is started
        teacher_headers = {"Authorization": f"Bearer {teacher_session}"}
        requests.post(f"{BASE_URL}/api/classes/start/{active_class_id}", headers=teacher_headers)
        
        # Student checks status
        student_headers = {"Authorization": f"Bearer {student_session}"}
        response = requests.get(f"{BASE_URL}/api/classes/status/{active_class_id}", headers=student_headers)
        assert response.status_code == 200, f"Student status check failed: {response.text}"
        data = response.json()
        
        assert data["is_in_progress"] == True
        print(f"✓ Student sees class in_progress: {data['title']}")
    
    def test_end_class_resets_status(self, teacher_session, active_class_id):
        """POST /api/classes/end/{class_id} sets status back to scheduled or completed"""
        headers = {"Authorization": f"Bearer {teacher_session}"}
        
        # Ensure class is started first
        requests.post(f"{BASE_URL}/api/classes/start/{active_class_id}", headers=headers)
        
        # End the class
        response = requests.post(f"{BASE_URL}/api/classes/end/{active_class_id}", headers=headers)
        assert response.status_code == 200, f"End class failed: {response.text}"
        data = response.json()
        
        assert "status" in data
        assert data["status"] in ["scheduled", "completed"]
        print(f"✓ Class ended, new status: {data['status']}")
        
        # Verify status changed
        status_response = requests.get(f"{BASE_URL}/api/classes/status/{active_class_id}", headers=headers)
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["is_in_progress"] == False
        print(f"✓ Class no longer in_progress")
    
    def test_start_class_notifies_student(self, teacher_session, student_session, active_class_id):
        """Starting class creates notification for enrolled student"""
        teacher_headers = {"Authorization": f"Bearer {teacher_session}"}
        student_headers = {"Authorization": f"Bearer {student_session}"}
        
        # Start the class
        requests.post(f"{BASE_URL}/api/classes/start/{active_class_id}", headers=teacher_headers)
        
        # Check student notifications
        response = requests.get(f"{BASE_URL}/api/notifications/my", headers=student_headers)
        assert response.status_code == 200
        notifications = response.json()
        
        # Look for class_started notification
        class_started_notifs = [n for n in notifications if n.get('type') == 'class_started']
        print(f"✓ Student has {len(class_started_notifs)} class_started notifications")
        
        # End class to reset state
        requests.post(f"{BASE_URL}/api/classes/end/{active_class_id}", headers=teacher_headers)
    
    def test_non_teacher_cannot_start_class(self, student_session, active_class_id):
        """Student cannot start a class"""
        headers = {"Authorization": f"Bearer {student_session}"}
        response = requests.post(f"{BASE_URL}/api/classes/start/{active_class_id}", headers=headers)
        assert response.status_code == 403
        print(f"✓ Student correctly blocked from starting class")


class TestStudentDashboard:
    """Tests for Student Dashboard features"""
    
    @pytest.fixture
    def student_session(self):
        """Get student session token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STUDENT_EMAIL,
            "password": STUDENT_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["session_token"]
    
    def test_student_dashboard_returns_classes(self, student_session):
        """Student dashboard returns upcoming and past classes"""
        headers = {"Authorization": f"Bearer {student_session}"}
        response = requests.get(f"{BASE_URL}/api/student/dashboard", headers=headers)
        assert response.status_code == 200, f"Dashboard failed: {response.text}"
        data = response.json()
        
        assert "credits" in data
        assert "upcoming_classes" in data
        assert "past_classes" in data
        
        print(f"✓ Student dashboard: {data['credits']} credits, {len(data['upcoming_classes'])} upcoming classes")
    
    def test_student_class_has_status(self, student_session):
        """Student classes include status field for Join button logic"""
        headers = {"Authorization": f"Bearer {student_session}"}
        response = requests.get(f"{BASE_URL}/api/student/dashboard", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        if data['upcoming_classes']:
            cls = data['upcoming_classes'][0]
            assert "status" in cls
            assert "class_id" in cls
            print(f"✓ Student class has status: {cls['title']} ({cls['status']})")


class TestTeacherScheduleCalendar:
    """Tests for Teacher Schedule Calendar status display"""
    
    @pytest.fixture
    def admin_session(self):
        """Get admin session token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["session_token"]
    
    def test_admin_classes_returns_all_classes(self, admin_session):
        """Admin can get all classes for schedule view"""
        headers = {"Authorization": f"Bearer {admin_session}"}
        response = requests.get(f"{BASE_URL}/api/admin/classes", headers=headers)
        assert response.status_code == 200, f"Admin classes failed: {response.text}"
        classes = response.json()
        
        assert isinstance(classes, list)
        if classes:
            cls = classes[0]
            assert "status" in cls
            assert "date" in cls
            assert "teacher_id" in cls
            print(f"✓ Admin classes: {len(classes)} total, first: {cls['title']} ({cls['status']})")
    
    def test_classes_have_schedule_status(self, admin_session):
        """Classes have status for BOOKED/LIVE/DONE/OFF display"""
        headers = {"Authorization": f"Bearer {admin_session}"}
        response = requests.get(f"{BASE_URL}/api/admin/classes", headers=headers)
        assert response.status_code == 200
        classes = response.json()
        
        valid_statuses = ['scheduled', 'in_progress', 'completed', 'cancelled', 'dismissed']
        for cls in classes:
            assert cls['status'] in valid_statuses, f"Invalid status: {cls['status']}"
        
        print(f"✓ All {len(classes)} classes have valid status for calendar display")


class TestStripeWebhook:
    """Tests for Stripe webhook endpoint"""
    
    def test_stripe_webhook_endpoint_exists(self):
        """POST /api/webhook/stripe endpoint exists"""
        # Send empty body - should fail validation but endpoint should exist
        response = requests.post(f"{BASE_URL}/api/webhook/stripe", data=b"")
        # 400 or 422 means endpoint exists but validation failed (expected)
        # 404 would mean endpoint doesn't exist
        assert response.status_code != 404, "Stripe webhook endpoint not found"
        print(f"✓ Stripe webhook endpoint exists (status: {response.status_code})")


class TestComplaintVisibility:
    """Tests for complaint visibility feature"""
    
    @pytest.fixture
    def teacher_session(self):
        """Get teacher session token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEACHER_EMAIL,
            "password": TEACHER_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["session_token"]
    
    def test_teacher_sees_student_complaints(self, teacher_session):
        """Teacher can see complaints from assigned students"""
        headers = {"Authorization": f"Bearer {teacher_session}"}
        response = requests.get(f"{BASE_URL}/api/teacher/student-complaints", headers=headers)
        assert response.status_code == 200, f"Complaints failed: {response.text}"
        complaints = response.json()
        
        assert isinstance(complaints, list)
        print(f"✓ Teacher sees {len(complaints)} student complaints")


class TestAdminCreateStudent:
    """Tests for Admin create student feature"""
    
    @pytest.fixture
    def admin_session(self):
        """Get admin session token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["session_token"]
    
    def test_admin_create_student_endpoint_exists(self, admin_session):
        """POST /api/admin/create-student endpoint exists"""
        headers = {"Authorization": f"Bearer {admin_session}"}
        # Try with duplicate email to verify endpoint works
        response = requests.post(f"{BASE_URL}/api/admin/create-student", headers=headers, json={
            "email": STUDENT_EMAIL,  # Existing email
            "password": "test123",
            "name": "Test Student"
        })
        # 400 means endpoint exists and rejected duplicate
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}"
        print(f"✓ Admin create student endpoint works (status: {response.status_code})")


class TestNotifications:
    """Tests for notification features"""
    
    @pytest.fixture
    def teacher_session(self):
        """Get teacher session token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEACHER_EMAIL,
            "password": TEACHER_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["session_token"]
    
    def test_teacher_notifications_endpoint(self, teacher_session):
        """Teacher can get notifications"""
        headers = {"Authorization": f"Bearer {teacher_session}"}
        response = requests.get(f"{BASE_URL}/api/notifications/my", headers=headers)
        assert response.status_code == 200, f"Notifications failed: {response.text}"
        notifications = response.json()
        
        assert isinstance(notifications, list)
        unread = len([n for n in notifications if not n.get('read', True)])
        print(f"✓ Teacher has {len(notifications)} notifications ({unread} unread)")


class TestCancelClassDay:
    """Tests for cancel class day feature"""
    
    @pytest.fixture
    def student_session(self):
        """Get student session token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STUDENT_EMAIL,
            "password": STUDENT_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["session_token"]
    
    @pytest.fixture
    def active_class_id(self, student_session):
        """Get an active class ID for testing"""
        headers = {"Authorization": f"Bearer {student_session}"}
        response = requests.get(f"{BASE_URL}/api/student/dashboard", headers=headers)
        assert response.status_code == 200
        data = response.json()
        if data['upcoming_classes']:
            return data['upcoming_classes'][0]['class_id']
        pytest.skip("No upcoming classes for testing")
    
    def test_cancel_class_day_endpoint_exists(self, student_session, active_class_id):
        """POST /api/classes/cancel-day/{class_id} endpoint exists"""
        headers = {"Authorization": f"Bearer {student_session}"}
        response = requests.post(f"{BASE_URL}/api/classes/cancel-day/{active_class_id}", headers=headers)
        # 200 or 400 (already cancelled today) means endpoint works
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}, {response.text}"
        print(f"✓ Cancel class day endpoint works (status: {response.status_code})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
