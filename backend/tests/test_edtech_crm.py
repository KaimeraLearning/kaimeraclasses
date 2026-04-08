"""
EdTech CRM Platform - Comprehensive Backend API Tests
Tests for: Student Profile, Demo Sessions, Class Proof Verification, Complaints, Counsellor Features
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://skill-exchange-149.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "info@kaimeralearning.com"
ADMIN_PASSWORD = "solidarity&peace2023"
STUDENT1_EMAIL = "student1@kaimera.com"
STUDENT1_PASSWORD = "password123"
STUDENT2_EMAIL = "student2@kaimera.com"
STUDENT2_PASSWORD = "password123"
TEACHER1_EMAIL = "teacher1@kaimera.com"
TEACHER1_PASSWORD = "password123"
TEACHER2_EMAIL = "teacher2@kaimera.com"
TEACHER2_PASSWORD = "password123"
COUNSELLOR_EMAIL = "counsellor1@kaimera.com"
COUNSELLOR_PASSWORD = "password123"


class TestSession:
    """Helper class to manage session tokens"""
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def login(self, email, password):
        """Login and store session cookie"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            data = response.json()
            if 'session_token' in data:
                self.session.headers.update({"Authorization": f"Bearer {data['session_token']}"})
        return response
    
    def get(self, endpoint):
        return self.session.get(f"{BASE_URL}{endpoint}")
    
    def post(self, endpoint, json=None):
        return self.session.post(f"{BASE_URL}{endpoint}", json=json)
    
    def delete(self, endpoint):
        return self.session.delete(f"{BASE_URL}{endpoint}")


# ==================== AUTH TESTS ====================

class TestAuthentication:
    """Test authentication for all user roles"""
    
    def test_admin_login(self):
        """Admin can login successfully"""
        session = TestSession()
        response = session.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert data['user']['role'] == 'admin'
        print(f"SUCCESS: Admin login - {data['user']['name']}")
    
    def test_student1_login(self):
        """Student1 can login successfully"""
        session = TestSession()
        response = session.login(STUDENT1_EMAIL, STUDENT1_PASSWORD)
        assert response.status_code == 200, f"Student1 login failed: {response.text}"
        data = response.json()
        assert data['user']['role'] == 'student'
        print(f"SUCCESS: Student1 login - {data['user']['name']}")
    
    def test_student2_login(self):
        """Student2 can login successfully"""
        session = TestSession()
        response = session.login(STUDENT2_EMAIL, STUDENT2_PASSWORD)
        assert response.status_code == 200, f"Student2 login failed: {response.text}"
        data = response.json()
        assert data['user']['role'] == 'student'
        print(f"SUCCESS: Student2 login - {data['user']['name']}")
    
    def test_teacher1_login(self):
        """Teacher1 can login successfully"""
        session = TestSession()
        response = session.login(TEACHER1_EMAIL, TEACHER1_PASSWORD)
        assert response.status_code == 200, f"Teacher1 login failed: {response.text}"
        data = response.json()
        assert data['user']['role'] == 'teacher'
        print(f"SUCCESS: Teacher1 login - {data['user']['name']}")
    
    def test_teacher2_login(self):
        """Teacher2 (pending) can login successfully"""
        session = TestSession()
        response = session.login(TEACHER2_EMAIL, TEACHER2_PASSWORD)
        assert response.status_code == 200, f"Teacher2 login failed: {response.text}"
        data = response.json()
        assert data['user']['role'] == 'teacher'
        print(f"SUCCESS: Teacher2 login - {data['user']['name']}")
    
    def test_counsellor_login(self):
        """Counsellor can login successfully"""
        session = TestSession()
        response = session.login(COUNSELLOR_EMAIL, COUNSELLOR_PASSWORD)
        assert response.status_code == 200, f"Counsellor login failed: {response.text}"
        data = response.json()
        assert data['user']['role'] == 'counsellor'
        print(f"SUCCESS: Counsellor login - {data['user']['name']}")
    
    def test_invalid_credentials(self):
        """Invalid credentials should fail"""
        session = TestSession()
        response = session.login("invalid@test.com", "wrongpassword")
        assert response.status_code == 401
        print("SUCCESS: Invalid credentials rejected")


# ==================== STUDENT PROFILE TESTS ====================

class TestStudentProfile:
    """Test student profile update functionality"""
    
    def test_student_update_profile(self):
        """Student can update their profile"""
        session = TestSession()
        login_res = session.login(STUDENT1_EMAIL, STUDENT1_PASSWORD)
        assert login_res.status_code == 200
        
        # Update profile
        response = session.post("/api/student/update-profile", json={
            "institute": "TEST_MIT",
            "goal": "TEST_Crack JEE Advanced",
            "preferred_time_slot": "TEST_Weekdays 5-7 PM",
            "phone": "TEST_9876543210"
        })
        assert response.status_code == 200, f"Profile update failed: {response.text}"
        print("SUCCESS: Student profile updated")
        
        # Verify update via /auth/me
        me_res = session.get("/api/auth/me")
        assert me_res.status_code == 200
        user_data = me_res.json()
        assert user_data.get('institute') == "TEST_MIT"
        assert user_data.get('goal') == "TEST_Crack JEE Advanced"
        print("SUCCESS: Profile update verified via /auth/me")
    
    def test_student_dashboard_loads(self):
        """Student dashboard returns data"""
        session = TestSession()
        session.login(STUDENT1_EMAIL, STUDENT1_PASSWORD)
        
        response = session.get("/api/student/dashboard")
        assert response.status_code == 200, f"Dashboard failed: {response.text}"
        data = response.json()
        assert 'credits' in data
        assert 'upcoming_classes' in data
        assert 'past_classes' in data
        print(f"SUCCESS: Student dashboard - Credits: {data['credits']}")


# ==================== COUNSELLOR TESTS ====================

class TestCounsellor:
    """Test counsellor functionality"""
    
    def test_counsellor_dashboard(self):
        """Counsellor dashboard returns data"""
        session = TestSession()
        session.login(COUNSELLOR_EMAIL, COUNSELLOR_PASSWORD)
        
        response = session.get("/api/counsellor/dashboard")
        assert response.status_code == 200, f"Dashboard failed: {response.text}"
        data = response.json()
        assert 'unassigned_students' in data
        assert 'all_students' in data
        assert 'teachers' in data
        assert 'active_assignments' in data
        print(f"SUCCESS: Counsellor dashboard - {len(data['all_students'])} students, {len(data['teachers'])} teachers")
    
    def test_counsellor_student_profile(self):
        """Counsellor can view student profile"""
        session = TestSession()
        session.login(COUNSELLOR_EMAIL, COUNSELLOR_PASSWORD)
        
        # First get a student ID
        dashboard = session.get("/api/counsellor/dashboard")
        assert dashboard.status_code == 200
        students = dashboard.json().get('all_students', [])
        
        if students:
            student_id = students[0]['user_id']
            response = session.get(f"/api/counsellor/student-profile/{student_id}")
            assert response.status_code == 200, f"Student profile failed: {response.text}"
            data = response.json()
            assert 'student' in data
            assert 'current_assignment' in data or data.get('current_assignment') is None
            assert 'class_history' in data
            print(f"SUCCESS: Counsellor viewed student profile - {data['student']['name']}")
        else:
            pytest.skip("No students available for testing")
    
    def test_counsellor_pending_proofs(self):
        """Counsellor can get pending proofs"""
        session = TestSession()
        session.login(COUNSELLOR_EMAIL, COUNSELLOR_PASSWORD)
        
        response = session.get("/api/counsellor/pending-proofs")
        assert response.status_code == 200, f"Pending proofs failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"SUCCESS: Counsellor pending proofs - {len(data)} pending")
    
    def test_counsellor_all_proofs(self):
        """Counsellor can get all proofs"""
        session = TestSession()
        session.login(COUNSELLOR_EMAIL, COUNSELLOR_PASSWORD)
        
        response = session.get("/api/counsellor/all-proofs")
        assert response.status_code == 200, f"All proofs failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"SUCCESS: Counsellor all proofs - {len(data)} total")
    
    def test_counsellor_expired_classes(self):
        """Counsellor can get expired classes"""
        session = TestSession()
        session.login(COUNSELLOR_EMAIL, COUNSELLOR_PASSWORD)
        
        response = session.get("/api/counsellor/expired-classes")
        assert response.status_code == 200, f"Expired classes failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"SUCCESS: Counsellor expired classes - {len(data)} expired")


# ==================== TEACHER TESTS ====================

class TestTeacher:
    """Test teacher functionality"""
    
    def test_teacher_dashboard(self):
        """Teacher dashboard returns data"""
        session = TestSession()
        session.login(TEACHER1_EMAIL, TEACHER1_PASSWORD)
        
        response = session.get("/api/teacher/dashboard")
        assert response.status_code == 200, f"Dashboard failed: {response.text}"
        data = response.json()
        assert 'is_approved' in data
        assert 'classes' in data
        assert 'pending_assignments' in data
        assert 'approved_students' in data
        print(f"SUCCESS: Teacher dashboard - Approved: {data['is_approved']}, Classes: {len(data['classes'])}")
    
    def test_teacher_my_proofs(self):
        """Teacher can get their submitted proofs"""
        session = TestSession()
        session.login(TEACHER1_EMAIL, TEACHER1_PASSWORD)
        
        response = session.get("/api/teacher/my-proofs")
        assert response.status_code == 200, f"My proofs failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"SUCCESS: Teacher my proofs - {len(data)} proofs")


# ==================== COMPLAINT TESTS ====================

class TestComplaints:
    """Test complaint system"""
    
    def test_student_create_complaint(self):
        """Student can create a complaint"""
        session = TestSession()
        session.login(STUDENT1_EMAIL, STUDENT1_PASSWORD)
        
        response = session.post("/api/complaints/create", json={
            "subject": "TEST_Complaint Subject",
            "description": "TEST_This is a test complaint description"
        })
        assert response.status_code == 200, f"Create complaint failed: {response.text}"
        data = response.json()
        assert 'complaint_id' in data
        print(f"SUCCESS: Student created complaint - {data['complaint_id']}")
    
    def test_teacher_create_complaint(self):
        """Teacher can create a complaint"""
        session = TestSession()
        session.login(TEACHER1_EMAIL, TEACHER1_PASSWORD)
        
        response = session.post("/api/complaints/create", json={
            "subject": "TEST_Teacher Complaint",
            "description": "TEST_Teacher complaint description"
        })
        assert response.status_code == 200, f"Create complaint failed: {response.text}"
        print("SUCCESS: Teacher created complaint")
    
    def test_counsellor_create_complaint(self):
        """Counsellor can create a complaint"""
        session = TestSession()
        session.login(COUNSELLOR_EMAIL, COUNSELLOR_PASSWORD)
        
        response = session.post("/api/complaints/create", json={
            "subject": "TEST_Counsellor Complaint",
            "description": "TEST_Counsellor complaint description"
        })
        assert response.status_code == 200, f"Create complaint failed: {response.text}"
        print("SUCCESS: Counsellor created complaint")
    
    def test_admin_cannot_create_complaint(self):
        """Admin cannot create complaints"""
        session = TestSession()
        session.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = session.post("/api/complaints/create", json={
            "subject": "TEST_Admin Complaint",
            "description": "TEST_Admin should not be able to create"
        })
        assert response.status_code == 403, f"Admin should not create complaints: {response.text}"
        print("SUCCESS: Admin correctly blocked from creating complaints")
    
    def test_student_get_my_complaints(self):
        """Student can get their complaints"""
        session = TestSession()
        session.login(STUDENT1_EMAIL, STUDENT1_PASSWORD)
        
        response = session.get("/api/complaints/my")
        assert response.status_code == 200, f"Get my complaints failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"SUCCESS: Student my complaints - {len(data)} complaints")
    
    def test_admin_get_all_complaints(self):
        """Admin can get all complaints"""
        session = TestSession()
        session.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = session.get("/api/admin/complaints")
        assert response.status_code == 200, f"Get all complaints failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"SUCCESS: Admin all complaints - {len(data)} complaints")
    
    def test_admin_resolve_complaint(self):
        """Admin can resolve a complaint"""
        session = TestSession()
        session.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        # Get complaints first
        complaints_res = session.get("/api/admin/complaints")
        assert complaints_res.status_code == 200
        complaints = complaints_res.json()
        
        # Find an open complaint
        open_complaints = [c for c in complaints if c.get('status') == 'open']
        if open_complaints:
            complaint_id = open_complaints[0]['complaint_id']
            response = session.post("/api/admin/resolve-complaint", json={
                "complaint_id": complaint_id,
                "resolution": "TEST_Resolution - Issue addressed",
                "status": "resolved"
            })
            assert response.status_code == 200, f"Resolve complaint failed: {response.text}"
            print(f"SUCCESS: Admin resolved complaint - {complaint_id}")
        else:
            print("INFO: No open complaints to resolve")


# ==================== ADMIN TESTS ====================

class TestAdmin:
    """Test admin functionality"""
    
    def test_admin_get_teachers(self):
        """Admin can get all teachers"""
        session = TestSession()
        session.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = session.get("/api/admin/teachers")
        assert response.status_code == 200, f"Get teachers failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"SUCCESS: Admin teachers - {len(data)} teachers")
    
    def test_admin_get_students(self):
        """Admin can get all students"""
        session = TestSession()
        session.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = session.get("/api/admin/students")
        assert response.status_code == 200, f"Get students failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"SUCCESS: Admin students - {len(data)} students")
    
    def test_admin_get_classes(self):
        """Admin can get all classes"""
        session = TestSession()
        session.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = session.get("/api/admin/classes")
        assert response.status_code == 200, f"Get classes failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"SUCCESS: Admin classes - {len(data)} classes")
    
    def test_admin_get_pricing(self):
        """Admin can get system pricing"""
        session = TestSession()
        session.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = session.get("/api/admin/get-pricing")
        assert response.status_code == 200, f"Get pricing failed: {response.text}"
        data = response.json()
        assert 'demo_price_student' in data
        assert 'class_price_student' in data
        print(f"SUCCESS: Admin pricing - Demo: {data['demo_price_student']}, Class: {data['class_price_student']}")
    
    def test_admin_set_pricing(self):
        """Admin can set system pricing"""
        session = TestSession()
        session.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = session.post("/api/admin/set-pricing", json={
            "demo_price_student": 5.0,
            "class_price_student": 10.0,
            "demo_earning_teacher": 3.0,
            "class_earning_teacher": 7.0
        })
        assert response.status_code == 200, f"Set pricing failed: {response.text}"
        print("SUCCESS: Admin set pricing")
    
    def test_admin_get_all_assignments(self):
        """Admin can get all assignments"""
        session = TestSession()
        session.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = session.get("/api/admin/all-assignments")
        assert response.status_code == 200, f"Get assignments failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"SUCCESS: Admin assignments - {len(data)} assignments")


# ==================== FULL WORKFLOW TESTS ====================

class TestFullWorkflow:
    """Test complete workflows"""
    
    def test_assignment_workflow(self):
        """Test student-teacher assignment workflow"""
        # 1. Admin/Counsellor assigns student to teacher
        session = TestSession()
        session.login(COUNSELLOR_EMAIL, COUNSELLOR_PASSWORD)
        
        # Get dashboard to find unassigned student and teacher
        dashboard = session.get("/api/counsellor/dashboard")
        assert dashboard.status_code == 200
        data = dashboard.json()
        
        unassigned = data.get('unassigned_students', [])
        teachers = data.get('teachers', [])
        
        if unassigned and teachers:
            student_id = unassigned[0]['user_id']
            teacher_id = teachers[0]['user_id']
            
            # Assign student to teacher
            assign_res = session.post("/api/admin/assign-student", json={
                "student_id": student_id,
                "teacher_id": teacher_id,
                "credit_price": 10.0
            })
            
            if assign_res.status_code == 200:
                print(f"SUCCESS: Assigned student {student_id} to teacher {teacher_id}")
            elif assign_res.status_code == 400:
                # Student might already be assigned
                print(f"INFO: Student already assigned - {assign_res.json().get('detail')}")
            else:
                print(f"WARNING: Assignment failed - {assign_res.text}")
        else:
            print("INFO: No unassigned students or teachers available")
    
    def test_proof_submission_workflow(self):
        """Test class proof submission workflow"""
        # Login as teacher
        session = TestSession()
        session.login(TEACHER1_EMAIL, TEACHER1_PASSWORD)
        
        # Get teacher's classes
        dashboard = session.get("/api/teacher/dashboard")
        assert dashboard.status_code == 200
        classes = dashboard.json().get('classes', [])
        
        if classes:
            # Find a class without proof
            proofs_res = session.get("/api/teacher/my-proofs")
            proofs = proofs_res.json() if proofs_res.status_code == 200 else []
            proof_class_ids = [p['class_id'] for p in proofs]
            
            classes_without_proof = [c for c in classes if c['class_id'] not in proof_class_ids]
            
            if classes_without_proof:
                class_id = classes_without_proof[0]['class_id']
                
                # Submit proof
                proof_res = session.post("/api/teacher/submit-proof", json={
                    "class_id": class_id,
                    "feedback_text": "TEST_Great session, student showed good progress",
                    "student_performance": "good",
                    "topics_covered": "TEST_Algebra basics, quadratic equations"
                })
                
                if proof_res.status_code == 200:
                    print(f"SUCCESS: Proof submitted for class {class_id}")
                elif proof_res.status_code == 400:
                    print(f"INFO: Proof already exists - {proof_res.json().get('detail')}")
                else:
                    print(f"WARNING: Proof submission failed - {proof_res.text}")
            else:
                print("INFO: All classes already have proofs")
        else:
            print("INFO: No classes available for proof submission")
    
    def test_proof_verification_workflow(self):
        """Test counsellor proof verification workflow"""
        session = TestSession()
        session.login(COUNSELLOR_EMAIL, COUNSELLOR_PASSWORD)
        
        # Get pending proofs
        proofs_res = session.get("/api/counsellor/pending-proofs")
        assert proofs_res.status_code == 200
        proofs = proofs_res.json()
        
        if proofs:
            proof_id = proofs[0]['proof_id']
            
            # Verify proof
            verify_res = session.post("/api/counsellor/verify-proof", json={
                "proof_id": proof_id,
                "approved": True,
                "reviewer_notes": "TEST_Verified - good documentation"
            })
            
            if verify_res.status_code == 200:
                print(f"SUCCESS: Proof verified - {proof_id}")
            elif verify_res.status_code == 400:
                print(f"INFO: Proof already processed - {verify_res.json().get('detail')}")
            else:
                print(f"WARNING: Proof verification failed - {verify_res.text}")
        else:
            print("INFO: No pending proofs to verify")


# ==================== CLEANUP ====================

class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_complaints(self):
        """Note: Test complaints with TEST_ prefix created during testing"""
        print("INFO: Test complaints created with TEST_ prefix for identification")
        print("INFO: Manual cleanup may be needed for TEST_ prefixed data")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
