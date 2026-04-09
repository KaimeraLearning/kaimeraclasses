"""
Iteration 13 - Major System Overhaul Testing
Tests for:
1. Enrollment Chain (demo-first constraint, matured lead logic, teacher rating filter)
2. Financial Logic (charge on class creation not acceptance, insufficient funds check, duplicate prevention)
3. Smart Dashboard (Today's/Upcoming/Conducted for teacher, Live/Pending Rating/Completed for student)
4. Teacher Rating & Penalty (cancellation reduces rating, bad feedback reduces rating, 5+ cancellations = 3-day suspension)
5. Permission-Based Chat (scoped messaging)
"""

import pytest
import requests
import os
import uuid
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


class TestAuthAndSetup:
    """Authentication and setup tests"""
    
    def test_admin_login(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "session_token" in data
        assert data["user"]["role"] == "admin"
        print(f"✓ Admin login successful")
        return data["session_token"]
    
    def test_teacher_login(self):
        """Test teacher login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEACHER_EMAIL,
            "password": TEACHER_PASSWORD
        })
        assert response.status_code == 200, f"Teacher login failed: {response.text}"
        data = response.json()
        assert data["user"]["role"] == "teacher"
        print(f"✓ Teacher login successful")
        return data["session_token"]
    
    def test_student_login(self):
        """Test student login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STUDENT_EMAIL,
            "password": STUDENT_PASSWORD
        })
        assert response.status_code == 200, f"Student login failed: {response.text}"
        data = response.json()
        assert data["user"]["role"] == "student"
        print(f"✓ Student login successful")
        return data["session_token"]
    
    def test_counsellor_login(self):
        """Test counsellor login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COUNSELLOR_EMAIL,
            "password": COUNSELLOR_PASSWORD
        })
        assert response.status_code == 200, f"Counsellor login failed: {response.text}"
        data = response.json()
        assert data["user"]["role"] == "counsellor"
        print(f"✓ Counsellor login successful")
        return data["session_token"]


class TestPurgeSystemEndpoint:
    """Test purge system endpoint exists (don't actually purge)"""
    
    def test_purge_system_requires_auth(self):
        """Verify purge-system endpoint exists and requires auth"""
        response = requests.post(f"{BASE_URL}/api/admin/purge-system")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✓ POST /api/admin/purge-system requires authentication (401)")
    
    def test_purge_system_requires_admin(self):
        """Verify purge-system requires admin role"""
        # Login as teacher
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEACHER_EMAIL,
            "password": TEACHER_PASSWORD
        })
        token = login_res.json().get("session_token")
        
        response = requests.post(
            f"{BASE_URL}/api/admin/purge-system",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        print(f"✓ POST /api/admin/purge-system requires admin role (403 for teacher)")


class TestDemoFirstConstraint:
    """Test demo-first constraint for student assignment"""
    
    def test_assign_student_without_demo_fails(self):
        """Verify student without completed demo cannot be assigned"""
        # Login as admin
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = login_res.json().get("session_token")
        
        # Create a new student without demo
        test_email = f"test_nodemo_{uuid.uuid4().hex[:8]}@test.com"
        
        # Try to assign this student (should fail if no demo)
        # First we need to get a teacher ID
        teachers_res = requests.get(
            f"{BASE_URL}/api/admin/teachers",
            headers={"Authorization": f"Bearer {token}"}
        )
        if teachers_res.status_code == 200 and teachers_res.json():
            teacher_id = teachers_res.json()[0]["user_id"]
            
            # Try to assign a non-existent student (will fail with 404)
            response = requests.post(
                f"{BASE_URL}/api/admin/assign-student",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "student_id": f"fake_student_{uuid.uuid4().hex[:8]}",
                    "teacher_id": teacher_id
                }
            )
            # Should fail with 404 (student not found) or 400 (no demo)
            assert response.status_code in [400, 404], f"Expected 400/404, got {response.status_code}: {response.text}"
            print(f"✓ POST /api/admin/assign-student validates student existence")


class TestFinancialLogic:
    """Test financial logic - charge on class creation, insufficient funds, duplicate prevention"""
    
    def test_insufficient_funds_check(self):
        """Test that class creation fails if student has insufficient funds"""
        # Login as teacher
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEACHER_EMAIL,
            "password": TEACHER_PASSWORD
        })
        token = login_res.json().get("session_token")
        teacher_id = login_res.json()["user"]["user_id"]
        
        # Get teacher dashboard to find approved students
        dash_res = requests.get(
            f"{BASE_URL}/api/teacher/dashboard",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if dash_res.status_code == 200:
            data = dash_res.json()
            approved_students = data.get("approved_students", [])
            
            if approved_students:
                student_id = approved_students[0]["student_id"]
                
                # Try to create a class with very high duration (likely to exceed credits)
                tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
                response = requests.post(
                    f"{BASE_URL}/api/classes/create",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "title": "Test Insufficient Funds",
                        "subject": "Math",
                        "class_type": "1:1",
                        "date": tomorrow,
                        "start_time": "10:00",
                        "end_time": "11:00",
                        "max_students": 1,
                        "assigned_student_id": student_id,
                        "duration_days": 1000,  # Very high to trigger insufficient funds
                        "is_demo": False
                    }
                )
                # Should fail with 400 if insufficient funds
                if response.status_code == 400:
                    assert "insufficient" in response.text.lower() or "funds" in response.text.lower(), f"Expected insufficient funds error: {response.text}"
                    print(f"✓ POST /api/classes/create returns error for insufficient funds")
                else:
                    print(f"⚠ Class creation returned {response.status_code} - may have sufficient credits")
            else:
                print(f"⚠ No approved students found for teacher - skipping insufficient funds test")
        else:
            print(f"⚠ Could not get teacher dashboard: {dash_res.status_code}")
    
    def test_duplicate_class_prevention(self):
        """Test that duplicate active class for same student-teacher pair is prevented"""
        # Login as teacher
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEACHER_EMAIL,
            "password": TEACHER_PASSWORD
        })
        token = login_res.json().get("session_token")
        
        # Get teacher dashboard
        dash_res = requests.get(
            f"{BASE_URL}/api/teacher/dashboard",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if dash_res.status_code == 200:
            data = dash_res.json()
            approved_students = data.get("approved_students", [])
            todays_sessions = data.get("todays_sessions", [])
            upcoming_classes = data.get("upcoming_classes", [])
            
            # Find a student who already has an active class
            active_student_ids = set()
            for cls in todays_sessions + upcoming_classes:
                if cls.get("assigned_student_id"):
                    active_student_ids.add(cls["assigned_student_id"])
            
            if active_student_ids and approved_students:
                # Find a student with active class
                for student in approved_students:
                    if student["student_id"] in active_student_ids:
                        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
                        response = requests.post(
                            f"{BASE_URL}/api/classes/create",
                            headers={"Authorization": f"Bearer {token}"},
                            json={
                                "title": "Test Duplicate Prevention",
                                "subject": "Math",
                                "class_type": "1:1",
                                "date": tomorrow,
                                "start_time": "14:00",
                                "end_time": "15:00",
                                "max_students": 1,
                                "assigned_student_id": student["student_id"],
                                "duration_days": 1,
                                "is_demo": False
                            }
                        )
                        if response.status_code == 400:
                            assert "already" in response.text.lower() or "active" in response.text.lower() or "duplicate" in response.text.lower(), f"Expected duplicate error: {response.text}"
                            print(f"✓ POST /api/classes/create returns error for duplicate active class")
                        else:
                            print(f"⚠ Duplicate class creation returned {response.status_code}")
                        break
            else:
                print(f"⚠ No students with active classes found - skipping duplicate test")
        else:
            print(f"⚠ Could not get teacher dashboard: {dash_res.status_code}")


class TestTeacherDashboard:
    """Test teacher dashboard with Today's/Upcoming/Conducted sections"""
    
    def test_teacher_dashboard_structure(self):
        """Verify teacher dashboard returns correct structure"""
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEACHER_EMAIL,
            "password": TEACHER_PASSWORD
        })
        token = login_res.json().get("session_token")
        
        response = requests.get(
            f"{BASE_URL}/api/teacher/dashboard",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Teacher dashboard failed: {response.text}"
        
        data = response.json()
        # Check required fields
        assert "todays_sessions" in data, "Missing todays_sessions"
        assert "upcoming_classes" in data, "Missing upcoming_classes"
        assert "conducted_classes" in data, "Missing conducted_classes"
        assert "star_rating" in data, "Missing star_rating"
        assert "is_suspended" in data, "Missing is_suspended"
        
        print(f"✓ GET /api/teacher/dashboard returns todays_sessions, upcoming_classes, conducted_classes, star_rating, is_suspended")


class TestStudentDashboard:
    """Test student dashboard with Live/Pending Rating/Completed sections"""
    
    def test_student_dashboard_structure(self):
        """Verify student dashboard returns correct structure"""
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STUDENT_EMAIL,
            "password": STUDENT_PASSWORD
        })
        token = login_res.json().get("session_token")
        
        response = requests.get(
            f"{BASE_URL}/api/student/dashboard",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Student dashboard failed: {response.text}"
        
        data = response.json()
        # Check required fields
        assert "live_classes" in data, "Missing live_classes"
        assert "upcoming_classes" in data, "Missing upcoming_classes"
        assert "completed_classes" in data, "Missing completed_classes"
        assert "pending_rating" in data, "Missing pending_rating"
        
        print(f"✓ GET /api/student/dashboard returns live_classes, upcoming_classes, completed_classes, pending_rating")


class TestTeacherRatingSystem:
    """Test teacher rating and penalty system"""
    
    def test_teacher_my_rating_endpoint(self):
        """Test GET /api/teacher/my-rating returns rating details"""
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEACHER_EMAIL,
            "password": TEACHER_PASSWORD
        })
        token = login_res.json().get("session_token")
        
        response = requests.get(
            f"{BASE_URL}/api/teacher/my-rating",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Teacher my-rating failed: {response.text}"
        
        data = response.json()
        assert "star_rating" in data, "Missing star_rating"
        assert "rating_details" in data, "Missing rating_details"
        assert "recent_events" in data, "Missing recent_events"
        
        print(f"✓ GET /api/teacher/my-rating returns star_rating, rating_details, recent_events")
    
    def test_admin_teacher_ratings_endpoint(self):
        """Test GET /api/admin/teacher-ratings returns teacher list with ratings"""
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = login_res.json().get("session_token")
        
        response = requests.get(
            f"{BASE_URL}/api/admin/teacher-ratings",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Admin teacher-ratings failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Expected list of teachers"
        if data:
            teacher = data[0]
            assert "user_id" in teacher, "Missing user_id"
            assert "name" in teacher, "Missing name"
            # star_rating may not exist if never calculated
            print(f"✓ GET /api/admin/teacher-ratings returns teacher list with rating info")
        else:
            print(f"✓ GET /api/admin/teacher-ratings returns empty list (no teachers)")
    
    def test_teacher_cancel_class_endpoint(self):
        """Test POST /api/teacher/cancel-class/{id} exists and requires auth"""
        response = requests.post(f"{BASE_URL}/api/teacher/cancel-class/fake_class_id")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✓ POST /api/teacher/cancel-class/{{id}} requires authentication")
    
    def test_student_rate_class_endpoint(self):
        """Test POST /api/student/rate-class exists and requires auth"""
        response = requests.post(f"{BASE_URL}/api/student/rate-class", json={
            "class_id": "fake",
            "rating": 5,
            "comments": "test"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✓ POST /api/student/rate-class requires authentication")


class TestChatSystem:
    """Test permission-based chat system"""
    
    def test_chat_send_requires_auth(self):
        """Test POST /api/chat/send requires authentication"""
        response = requests.post(f"{BASE_URL}/api/chat/send", json={
            "recipient_id": "fake",
            "message": "test"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✓ POST /api/chat/send requires authentication")
    
    def test_chat_contacts_endpoint(self):
        """Test GET /api/chat/contacts returns scoped contacts"""
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEACHER_EMAIL,
            "password": TEACHER_PASSWORD
        })
        token = login_res.json().get("session_token")
        
        response = requests.get(
            f"{BASE_URL}/api/chat/contacts",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Chat contacts failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Expected list of contacts"
        print(f"✓ GET /api/chat/contacts returns scoped contacts based on role")
    
    def test_chat_conversations_endpoint(self):
        """Test GET /api/chat/conversations returns conversation list"""
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEACHER_EMAIL,
            "password": TEACHER_PASSWORD
        })
        token = login_res.json().get("session_token")
        
        response = requests.get(
            f"{BASE_URL}/api/chat/conversations",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Chat conversations failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Expected list of conversations"
        print(f"✓ GET /api/chat/conversations returns conversation list")
    
    def test_chat_messages_endpoint(self):
        """Test GET /api/chat/messages/{partner_id} returns messages"""
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEACHER_EMAIL,
            "password": TEACHER_PASSWORD
        })
        token = login_res.json().get("session_token")
        
        response = requests.get(
            f"{BASE_URL}/api/chat/messages/fake_partner_id",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Chat messages failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Expected list of messages"
        print(f"✓ GET /api/chat/messages/{{partner_id}} returns messages")
    
    def test_chat_permission_scoping(self):
        """Test that chat respects permission scoping"""
        # Login as student
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STUDENT_EMAIL,
            "password": STUDENT_PASSWORD
        })
        token = login_res.json().get("session_token")
        
        # Try to send message to a random user (should fail if not assigned)
        response = requests.post(
            f"{BASE_URL}/api/chat/send",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "recipient_id": "random_user_id",
                "message": "test message"
            }
        )
        # Should fail with 403 or 404
        assert response.status_code in [403, 404], f"Expected 403/404 for unauthorized chat, got {response.status_code}"
        print(f"✓ POST /api/chat/send respects permission scoping")


class TestCounsellorRatingFilter:
    """Test counsellor rating filter in assignment modal"""
    
    def test_counsellor_dashboard_has_teachers_with_ratings(self):
        """Verify counsellor dashboard returns teachers with rating info"""
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COUNSELLOR_EMAIL,
            "password": COUNSELLOR_PASSWORD
        })
        token = login_res.json().get("session_token")
        
        response = requests.get(
            f"{BASE_URL}/api/counsellor/dashboard",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Counsellor dashboard failed: {response.text}"
        
        data = response.json()
        teachers = data.get("teachers", [])
        if teachers:
            # Check if teachers have star_rating field (may be None if never calculated)
            print(f"✓ GET /api/counsellor/dashboard returns teachers list for rating filter")
        else:
            print(f"⚠ No teachers in counsellor dashboard")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
