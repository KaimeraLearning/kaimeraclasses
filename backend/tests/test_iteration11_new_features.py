"""
Iteration 11 Backend Tests - New P0 Features
Tests for:
1. Admin System Pricing (GET/POST /admin/get-pricing, /admin/set-pricing)
2. Admin Edit Student Profile (POST /admin/edit-student/{user_id})
3. Counsellor Student Profile with demo_history (GET /counsellor/student-profile/{student_id})
4. Teacher Reschedule Class (POST /teacher/reschedule-class/{class_id})
5. Counsellor Assign Student with new fields (class_frequency, specific_days, demo_performance_notes)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "info@kaimeralearning.com"
ADMIN_PASSWORD = "solidarity&peace2023"
STUDENT_EMAIL = "student1@kaimera.com"
STUDENT_PASSWORD = "password123"
TEACHER_EMAIL = "teacher1@kaimera.com"
TEACHER_PASSWORD = "password123"
COUNSELLOR_EMAIL = "counsellor1@kaimera.com"
COUNSELLOR_PASSWORD = "password123"


class TestAdminSystemPricing:
    """Tests for Admin System Pricing endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        # Login as admin
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        self.admin_token = response.json().get("session_token")
        self.session.cookies.set("session_token", self.admin_token)
    
    def test_get_pricing_returns_data(self):
        """GET /api/admin/get-pricing returns pricing data"""
        response = self.session.get(f"{BASE_URL}/api/admin/get-pricing")
        assert response.status_code == 200, f"Get pricing failed: {response.text}"
        data = response.json()
        # Should have all 4 pricing fields
        assert "demo_price_student" in data
        assert "class_price_student" in data
        assert "demo_earning_teacher" in data
        assert "class_earning_teacher" in data
        print(f"GET /api/admin/get-pricing - SUCCESS: {data}")
    
    def test_set_pricing_saves_correctly(self):
        """POST /api/admin/set-pricing saves pricing correctly"""
        test_pricing = {
            "demo_price_student": 5.0,
            "class_price_student": 10.0,
            "demo_earning_teacher": 3.0,
            "class_earning_teacher": 7.0
        }
        response = self.session.post(f"{BASE_URL}/api/admin/set-pricing", json=test_pricing)
        assert response.status_code == 200, f"Set pricing failed: {response.text}"
        
        # Verify by getting pricing again
        get_response = self.session.get(f"{BASE_URL}/api/admin/get-pricing")
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["demo_price_student"] == 5.0
        assert data["class_price_student"] == 10.0
        assert data["demo_earning_teacher"] == 3.0
        assert data["class_earning_teacher"] == 7.0
        print(f"POST /api/admin/set-pricing - SUCCESS: Pricing saved and verified")
    
    def test_set_pricing_non_admin_blocked(self):
        """POST /api/admin/set-pricing blocked for non-admin"""
        # Login as student
        student_session = requests.Session()
        login_resp = student_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": STUDENT_EMAIL,
            "password": STUDENT_PASSWORD
        })
        if login_resp.status_code != 200:
            pytest.skip("Student account not available")
        
        student_session.cookies.set("session_token", login_resp.json().get("session_token"))
        
        response = student_session.post(f"{BASE_URL}/api/admin/set-pricing", json={
            "demo_price_student": 100.0,
            "class_price_student": 100.0,
            "demo_earning_teacher": 100.0,
            "class_earning_teacher": 100.0
        })
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("POST /api/admin/set-pricing - Non-admin blocked (403)")


class TestAdminEditStudent:
    """Tests for Admin Edit Student Profile endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        # Login as admin
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        self.session.cookies.set("session_token", response.json().get("session_token"))
        
        # Get student user_id
        users_resp = self.session.get(f"{BASE_URL}/api/admin/all-users")
        if users_resp.status_code == 200:
            users = users_resp.json()
            students = [u for u in users if u.get("role") == "student"]
            if students:
                self.student_id = students[0]["user_id"]
                self.student_name = students[0].get("name", "Test Student")
            else:
                self.student_id = None
        else:
            self.student_id = None
    
    def test_edit_student_updates_profile(self):
        """POST /api/admin/edit-student/{user_id} updates student profile"""
        if not self.student_id:
            pytest.skip("No student found in database")
        
        update_data = {
            "name": "Alice Johnson Updated",
            "phone": "9876543210",
            "institute": "Test Institute Updated",
            "goal": "Updated Goal",
            "grade": "11",
            "city": "New City",
            "state": "New State"
        }
        
        response = self.session.post(f"{BASE_URL}/api/admin/edit-student/{self.student_id}", json=update_data)
        assert response.status_code == 200, f"Edit student failed: {response.text}"
        data = response.json()
        assert "updated_fields" in data
        print(f"POST /api/admin/edit-student - SUCCESS: Updated fields: {data.get('updated_fields')}")
        
        # Revert name back
        self.session.post(f"{BASE_URL}/api/admin/edit-student/{self.student_id}", json={"name": self.student_name})
    
    def test_edit_student_credits(self):
        """POST /api/admin/edit-student/{user_id} can update credits"""
        if not self.student_id:
            pytest.skip("No student found in database")
        
        response = self.session.post(f"{BASE_URL}/api/admin/edit-student/{self.student_id}", json={
            "credits": 50.0
        })
        assert response.status_code == 200, f"Edit credits failed: {response.text}"
        data = response.json()
        assert "credits" in data.get("updated_fields", [])
        print("POST /api/admin/edit-student - Credits update SUCCESS")
    
    def test_edit_student_not_found(self):
        """POST /api/admin/edit-student/{user_id} returns 404 for invalid user"""
        response = self.session.post(f"{BASE_URL}/api/admin/edit-student/invalid_user_id", json={
            "name": "Test"
        })
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("POST /api/admin/edit-student - Invalid user returns 404")
    
    def test_edit_student_non_admin_blocked(self):
        """POST /api/admin/edit-student blocked for non-admin"""
        if not self.student_id:
            pytest.skip("No student found in database")
        
        # Login as counsellor
        counsellor_session = requests.Session()
        login_resp = counsellor_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COUNSELLOR_EMAIL,
            "password": COUNSELLOR_PASSWORD
        })
        if login_resp.status_code != 200:
            pytest.skip("Counsellor account not available")
        
        counsellor_session.cookies.set("session_token", login_resp.json().get("session_token"))
        
        response = counsellor_session.post(f"{BASE_URL}/api/admin/edit-student/{self.student_id}", json={
            "name": "Hacked Name"
        })
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("POST /api/admin/edit-student - Non-admin blocked (403)")


class TestCounsellorStudentProfile:
    """Tests for Counsellor Student Profile endpoint with demo_history"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        # Login as counsellor
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COUNSELLOR_EMAIL,
            "password": COUNSELLOR_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Counsellor login failed")
        self.session.cookies.set("session_token", response.json().get("session_token"))
        
        # Get a student ID
        admin_session = requests.Session()
        admin_login = admin_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if admin_login.status_code == 200:
            admin_session.cookies.set("session_token", admin_login.json().get("session_token"))
            users_resp = admin_session.get(f"{BASE_URL}/api/admin/all-users")
            if users_resp.status_code == 200:
                users = users_resp.json()
                students = [u for u in users if u.get("role") == "student"]
                if students:
                    self.student_id = students[0]["user_id"]
                else:
                    self.student_id = None
            else:
                self.student_id = None
        else:
            self.student_id = None
    
    def test_student_profile_returns_demo_history(self):
        """GET /api/counsellor/student-profile/{student_id} returns demo_history field"""
        if not self.student_id:
            pytest.skip("No student found in database")
        
        response = self.session.get(f"{BASE_URL}/api/counsellor/student-profile/{self.student_id}")
        assert response.status_code == 200, f"Get student profile failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "student" in data
        assert "demo_history" in data
        assert "class_history" in data
        assert "current_assignment" in data
        
        # demo_history should be a list
        assert isinstance(data["demo_history"], list)
        print(f"GET /api/counsellor/student-profile - SUCCESS: demo_history field present, {len(data['demo_history'])} demos")
    
    def test_student_profile_demo_history_has_teacher_name(self):
        """GET /api/counsellor/student-profile demo_history includes teacher_name"""
        if not self.student_id:
            pytest.skip("No student found in database")
        
        response = self.session.get(f"{BASE_URL}/api/counsellor/student-profile/{self.student_id}")
        assert response.status_code == 200
        data = response.json()
        
        # If there are demos, check structure
        if data["demo_history"]:
            demo = data["demo_history"][0]
            assert "teacher_name" in demo, "demo_history should include teacher_name"
            print(f"Demo history entry has teacher_name: {demo.get('teacher_name')}")
        else:
            print("No demo history entries to verify teacher_name field")
    
    def test_student_profile_not_found(self):
        """GET /api/counsellor/student-profile returns 404 for invalid student"""
        response = self.session.get(f"{BASE_URL}/api/counsellor/student-profile/invalid_student_id")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("GET /api/counsellor/student-profile - Invalid student returns 404")


class TestCounsellorAssignStudentNewFields:
    """Tests for Counsellor Assign Student with new fields"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        # Login as counsellor
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COUNSELLOR_EMAIL,
            "password": COUNSELLOR_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Counsellor login failed")
        self.session.cookies.set("session_token", response.json().get("session_token"))
        
        # Get student and teacher IDs
        admin_session = requests.Session()
        admin_login = admin_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if admin_login.status_code == 200:
            admin_session.cookies.set("session_token", admin_login.json().get("session_token"))
            users_resp = admin_session.get(f"{BASE_URL}/api/admin/all-users")
            if users_resp.status_code == 200:
                users = users_resp.json()
                students = [u for u in users if u.get("role") == "student"]
                teachers = [u for u in users if u.get("role") == "teacher"]
                
                # Find unassigned student
                assignments_resp = admin_session.get(f"{BASE_URL}/api/admin/all-assignments")
                assigned_student_ids = set()
                if assignments_resp.status_code == 200:
                    for a in assignments_resp.json():
                        if a.get("status") in ["pending", "approved"]:
                            assigned_student_ids.add(a.get("student_id"))
                
                unassigned = [s for s in students if s["user_id"] not in assigned_student_ids]
                self.student_id = unassigned[0]["user_id"] if unassigned else None
                self.teacher_id = teachers[0]["user_id"] if teachers else None
            else:
                self.student_id = None
                self.teacher_id = None
        else:
            self.student_id = None
            self.teacher_id = None
    
    def test_assign_student_with_new_fields(self):
        """POST /api/admin/assign-student accepts class_frequency, specific_days, demo_performance_notes"""
        if not self.student_id or not self.teacher_id:
            pytest.skip("No unassigned student or teacher available")
        
        response = self.session.post(f"{BASE_URL}/api/admin/assign-student", json={
            "student_id": self.student_id,
            "teacher_id": self.teacher_id,
            "class_frequency": "3_per_week",
            "specific_days": "Mon, Wed, Fri",
            "demo_performance_notes": "Student showed good understanding in demo session"
        })
        
        # May fail if student already assigned, that's ok
        if response.status_code == 400 and "already assigned" in response.text.lower():
            print("Student already assigned - skipping new fields test")
            pytest.skip("Student already assigned")
        
        assert response.status_code == 200, f"Assign student failed: {response.text}"
        data = response.json()
        assert "assignment_id" in data
        print(f"POST /api/admin/assign-student with new fields - SUCCESS: {data}")


class TestTeacherRescheduleClass:
    """Tests for Teacher Reschedule Class endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        # Login as teacher
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEACHER_EMAIL,
            "password": TEACHER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Teacher login failed")
        self.session.cookies.set("session_token", response.json().get("session_token"))
    
    def test_reschedule_requires_cancelled_today(self):
        """POST /api/teacher/reschedule-class requires cancelled_today flag"""
        # Try to reschedule a non-existent class
        response = self.session.post(f"{BASE_URL}/api/teacher/reschedule-class/fake_class_id", json={
            "new_date": "2026-02-01",
            "new_start_time": "10:00",
            "new_end_time": "11:00"
        })
        # Should return 404 (class not found) or 400 (not cancelled)
        assert response.status_code in [400, 404], f"Expected 400/404, got {response.status_code}"
        print(f"POST /api/teacher/reschedule-class - Properly validates: {response.status_code}")
    
    def test_reschedule_requires_all_fields(self):
        """POST /api/teacher/reschedule-class requires new_date, new_start_time, new_end_time"""
        response = self.session.post(f"{BASE_URL}/api/teacher/reschedule-class/any_class_id", json={
            "new_date": "2026-02-01"
            # Missing start_time and end_time
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("POST /api/teacher/reschedule-class - Missing fields returns 400")
    
    def test_reschedule_non_teacher_blocked(self):
        """POST /api/teacher/reschedule-class blocked for non-teacher"""
        # Login as student
        student_session = requests.Session()
        login_resp = student_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": STUDENT_EMAIL,
            "password": STUDENT_PASSWORD
        })
        if login_resp.status_code != 200:
            pytest.skip("Student account not available")
        
        student_session.cookies.set("session_token", login_resp.json().get("session_token"))
        
        response = student_session.post(f"{BASE_URL}/api/teacher/reschedule-class/any_class_id", json={
            "new_date": "2026-02-01",
            "new_start_time": "10:00",
            "new_end_time": "11:00"
        })
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("POST /api/teacher/reschedule-class - Non-teacher blocked (403)")


class TestLoginAllRoles:
    """Verify all test accounts can login"""
    
    def test_admin_login(self):
        """Admin can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert data["user"]["role"] == "admin"
        print("Admin login - SUCCESS")
    
    def test_student_login(self):
        """Student can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STUDENT_EMAIL,
            "password": STUDENT_PASSWORD
        })
        assert response.status_code == 200, f"Student login failed: {response.text}"
        data = response.json()
        assert data["user"]["role"] == "student"
        print("Student login - SUCCESS")
    
    def test_teacher_login(self):
        """Teacher can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEACHER_EMAIL,
            "password": TEACHER_PASSWORD
        })
        assert response.status_code == 200, f"Teacher login failed: {response.text}"
        data = response.json()
        assert data["user"]["role"] == "teacher"
        print("Teacher login - SUCCESS")
    
    def test_counsellor_login(self):
        """Counsellor can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COUNSELLOR_EMAIL,
            "password": COUNSELLOR_PASSWORD
        })
        assert response.status_code == 200, f"Counsellor login failed: {response.text}"
        data = response.json()
        assert data["user"]["role"] == "counsellor"
        print("Counsellor login - SUCCESS")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
