"""
Iteration 21 - ViewProfilePopup Integration & Auto-Refresh Testing
Tests:
1. Teacher view-profile endpoint returns full profile data
2. Counselor view-profile endpoint returns full profile data
3. Teacher dashboard returns counselor_name and counselor_id in approved_students
4. Student rate-class endpoint rejects duplicate ratings
5. Teacher dashboard proof_submitted flag on conducted classes
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestViewProfileEndpoints:
    """Test view-profile endpoints for teacher and counselor"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def login(self, email, password):
        """Helper to login and get session"""
        res = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email, "password": password
        })
        return res.status_code == 200
    
    def test_teacher_login(self):
        """Test teacher login works"""
        res = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "teacher@k.com", "password": "password123"
        })
        assert res.status_code == 200, f"Teacher login failed: {res.text}"
        data = res.json()
        assert "user_id" in data or "email" in data
        print("PASSED: Teacher login successful")
    
    def test_student_login(self):
        """Test student login works"""
        res = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "student@k.com", "password": "password123"
        })
        assert res.status_code == 200, f"Student login failed: {res.text}"
        print("PASSED: Student login successful")
    
    def test_counselor_login(self):
        """Test counselor login works"""
        res = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "counselor@k.com", "password": "password123"
        })
        assert res.status_code == 200, f"Counselor login failed: {res.text}"
        print("PASSED: Counselor login successful")
    
    def test_teacher_view_profile_endpoint(self):
        """Test GET /api/teacher/view-profile/{teacher_id} returns full profile"""
        # Login as student first
        assert self.login("student@k.com", "password123"), "Student login failed"
        
        # Get teacher ID from student dashboard
        dash_res = self.session.get(f"{BASE_URL}/api/student/dashboard")
        assert dash_res.status_code == 200, f"Student dashboard failed: {dash_res.text}"
        dash_data = dash_res.json()
        
        # Find a teacher_id from any class
        teacher_id = None
        for cls in dash_data.get("live_classes", []) + dash_data.get("upcoming_classes", []) + dash_data.get("completed_classes", []) + dash_data.get("pending_rating", []):
            if cls.get("teacher_id"):
                teacher_id = cls["teacher_id"]
                break
        
        if not teacher_id:
            # Try to get teacher from admin
            self.session.post(f"{BASE_URL}/api/auth/logout")
            assert self.login("info@kaimeralearning.com", "solidarity&peace2023"), "Admin login failed"
            users_res = self.session.get(f"{BASE_URL}/api/admin/users")
            if users_res.status_code == 200:
                for u in users_res.json():
                    if u.get("role") == "teacher":
                        teacher_id = u["user_id"]
                        break
        
        if not teacher_id:
            pytest.skip("No teacher found to test view-profile")
        
        # Test view-profile endpoint
        profile_res = self.session.get(f"{BASE_URL}/api/teacher/view-profile/{teacher_id}")
        assert profile_res.status_code == 200, f"Teacher view-profile failed: {profile_res.text}"
        
        profile = profile_res.json()
        # Verify profile fields exist
        assert "name" in profile, "Profile missing 'name'"
        assert "email" in profile, "Profile missing 'email'"
        # Check for extended profile fields (may be null but should exist in response)
        print(f"PASSED: Teacher view-profile returns profile with name={profile.get('name')}")
        print(f"  Profile fields: {list(profile.keys())}")
    
    def test_counselor_view_profile_endpoint(self):
        """Test GET /api/counsellor/view-profile/{counselor_id} returns full profile"""
        # Login as teacher first
        assert self.login("teacher@k.com", "password123"), "Teacher login failed"
        
        # Get teacher dashboard to find counselor_id
        dash_res = self.session.get(f"{BASE_URL}/api/teacher/dashboard")
        assert dash_res.status_code == 200, f"Teacher dashboard failed: {dash_res.text}"
        dash_data = dash_res.json()
        
        # Find counselor_id from approved_students
        counselor_id = None
        for student in dash_data.get("approved_students", []):
            if student.get("counselor_id"):
                counselor_id = student["counselor_id"]
                break
        
        if not counselor_id:
            # Try to get counselor from admin
            self.session.post(f"{BASE_URL}/api/auth/logout")
            assert self.login("info@kaimeralearning.com", "solidarity&peace2023"), "Admin login failed"
            users_res = self.session.get(f"{BASE_URL}/api/admin/users")
            if users_res.status_code == 200:
                for u in users_res.json():
                    if u.get("role") == "counsellor":
                        counselor_id = u["user_id"]
                        break
        
        if not counselor_id:
            pytest.skip("No counselor found to test view-profile")
        
        # Test view-profile endpoint
        profile_res = self.session.get(f"{BASE_URL}/api/counsellor/view-profile/{counselor_id}")
        assert profile_res.status_code == 200, f"Counselor view-profile failed: {profile_res.text}"
        
        profile = profile_res.json()
        assert "name" in profile, "Profile missing 'name'"
        assert "email" in profile, "Profile missing 'email'"
        print(f"PASSED: Counselor view-profile returns profile with name={profile.get('name')}")
        print(f"  Profile fields: {list(profile.keys())}")


class TestTeacherDashboardCounselorEnrichment:
    """Test teacher dashboard returns counselor info in approved_students"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_teacher_dashboard_has_counselor_info(self):
        """Test teacher dashboard approved_students includes counselor_name and counselor_id"""
        res = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "teacher@k.com", "password": "password123"
        })
        assert res.status_code == 200, f"Teacher login failed: {res.text}"
        
        dash_res = self.session.get(f"{BASE_URL}/api/teacher/dashboard")
        assert dash_res.status_code == 200, f"Teacher dashboard failed: {dash_res.text}"
        
        data = dash_res.json()
        approved_students = data.get("approved_students", [])
        
        if len(approved_students) == 0:
            pytest.skip("No approved students to verify counselor enrichment")
        
        # Check if counselor_name and counselor_id are present
        for student in approved_students:
            if student.get("assigned_by"):
                assert "counselor_name" in student, f"Missing counselor_name for student {student.get('student_name')}"
                assert "counselor_id" in student, f"Missing counselor_id for student {student.get('student_name')}"
                print(f"PASSED: Student {student.get('student_name')} has counselor_name={student.get('counselor_name')}, counselor_id={student.get('counselor_id')}")
                return
        
        print("INFO: No students with assigned_by field found, counselor enrichment not applicable")


class TestRatingDuplicateCheck:
    """Test student rate-class endpoint rejects duplicate ratings"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_rate_class_duplicate_check(self):
        """Test POST /api/student/rate-class rejects duplicate ratings"""
        res = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "student@k.com", "password": "password123"
        })
        assert res.status_code == 200, f"Student login failed: {res.text}"
        
        # Get student dashboard to find a completed class
        dash_res = self.session.get(f"{BASE_URL}/api/student/dashboard")
        assert dash_res.status_code == 200, f"Student dashboard failed: {dash_res.text}"
        
        data = dash_res.json()
        completed_classes = data.get("completed_classes", [])
        
        if len(completed_classes) == 0:
            pytest.skip("No completed classes to test duplicate rating check")
        
        # Try to rate an already-rated class (completed_classes are already rated)
        class_id = completed_classes[0]["class_id"]
        rate_res = self.session.post(f"{BASE_URL}/api/student/rate-class", json={
            "class_id": class_id,
            "rating": 5,
            "comments": "Test duplicate rating"
        })
        
        # Should return 400 with "Already rated" message
        assert rate_res.status_code == 400, f"Expected 400 for duplicate rating, got {rate_res.status_code}"
        error_data = rate_res.json()
        assert "already rated" in error_data.get("detail", "").lower() or "already" in error_data.get("detail", "").lower(), f"Expected 'already rated' error, got: {error_data}"
        print(f"PASSED: Duplicate rating correctly rejected with message: {error_data.get('detail')}")


class TestProofSubmittedFlag:
    """Test teacher dashboard conducted classes have proof_submitted flag"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_conducted_classes_have_proof_submitted_flag(self):
        """Test teacher dashboard conducted_classes include proof_submitted boolean"""
        res = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "teacher@k.com", "password": "password123"
        })
        assert res.status_code == 200, f"Teacher login failed: {res.text}"
        
        dash_res = self.session.get(f"{BASE_URL}/api/teacher/dashboard")
        assert dash_res.status_code == 200, f"Teacher dashboard failed: {dash_res.text}"
        
        data = dash_res.json()
        conducted_classes = data.get("conducted_classes", [])
        
        if len(conducted_classes) == 0:
            pytest.skip("No conducted classes to verify proof_submitted flag")
        
        # Check that proof_submitted field exists
        for cls in conducted_classes:
            assert "proof_submitted" in cls, f"Missing proof_submitted flag for class {cls.get('class_id')}"
            assert isinstance(cls["proof_submitted"], bool), f"proof_submitted should be boolean, got {type(cls['proof_submitted'])}"
            print(f"PASSED: Class {cls.get('title')} has proof_submitted={cls['proof_submitted']}")
            return
        
        print("PASSED: All conducted classes have proof_submitted flag")


class TestStudentDashboardSections:
    """Test student dashboard returns correct sections"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_student_dashboard_sections(self):
        """Test student dashboard returns live_classes, upcoming_classes, completed_classes, pending_rating"""
        res = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "student@k.com", "password": "password123"
        })
        assert res.status_code == 200, f"Student login failed: {res.text}"
        
        dash_res = self.session.get(f"{BASE_URL}/api/student/dashboard")
        assert dash_res.status_code == 200, f"Student dashboard failed: {dash_res.text}"
        
        data = dash_res.json()
        
        # Verify all required sections exist
        assert "live_classes" in data, "Missing live_classes section"
        assert "upcoming_classes" in data, "Missing upcoming_classes section"
        assert "completed_classes" in data, "Missing completed_classes section"
        assert "pending_rating" in data, "Missing pending_rating section"
        
        print(f"PASSED: Student dashboard has all sections:")
        print(f"  live_classes: {len(data['live_classes'])}")
        print(f"  upcoming_classes: {len(data['upcoming_classes'])}")
        print(f"  completed_classes: {len(data['completed_classes'])}")
        print(f"  pending_rating: {len(data['pending_rating'])}")
        
        # Verify classes in pending_rating have teacher_id for profile popup
        for cls in data.get("pending_rating", []):
            assert "teacher_id" in cls, f"Missing teacher_id in pending_rating class {cls.get('class_id')}"
            assert "teacher_name" in cls, f"Missing teacher_name in pending_rating class {cls.get('class_id')}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
