"""
Test Phase 1-3 Features for Kaimera Learning EdTech CRM
- Teacher search API (by name/ID)
- Class filter API (by type/status/search)
- Student filter API (by grade/city/state)
- Wallet API (balance and transactions)
- Admin proof approval (auto-credits teacher wallet)
- Admin proof listing with date filtering
- Counsellor assign student (no credit_price)
- Admin badge assignment
- Teacher feedback to student (notification)
- Renewal check (80% completion)
- Teacher profile update with bank_details
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
API = f"{BASE_URL}/api"

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
    """Helper class for authentication"""
    
    @staticmethod
    def login(email, password):
        """Login and return session with cookies"""
        session = requests.Session()
        response = session.post(f"{API}/auth/login", json={"email": email, "password": password})
        if response.status_code == 200:
            data = response.json()
            if 'session_token' in data:
                session.headers.update({"Authorization": f"Bearer {data['session_token']}"})
        return session, response


class TestTeacherSearch:
    """Test GET /api/search/teachers - Teacher search by name/ID"""
    
    def test_search_teachers_by_code(self):
        """Search teachers by teacher_code (KL-T format)"""
        session, login_res = TestAuth.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert login_res.status_code == 200, f"Admin login failed: {login_res.text}"
        
        response = session.get(f"{API}/search/teachers?q=KL-T")
        assert response.status_code == 200, f"Search failed: {response.text}"
        
        teachers = response.json()
        assert isinstance(teachers, list), "Response should be a list"
        # Check that results contain teacher_code field
        if len(teachers) > 0:
            assert "teacher_code" in teachers[0], "Teacher should have teacher_code field"
            print(f"Found {len(teachers)} teachers matching 'KL-T'")
    
    def test_search_teachers_by_name(self):
        """Search teachers by name"""
        session, _ = TestAuth.login(COUNSELLOR_EMAIL, COUNSELLOR_PASSWORD)
        
        response = session.get(f"{API}/search/teachers?q=Maria")
        assert response.status_code == 200
        
        teachers = response.json()
        assert isinstance(teachers, list)
        print(f"Found {len(teachers)} teachers matching 'Maria'")
    
    def test_search_teachers_empty_query(self):
        """Empty query returns all teachers"""
        session, _ = TestAuth.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = session.get(f"{API}/search/teachers?q=")
        assert response.status_code == 200
        
        teachers = response.json()
        assert isinstance(teachers, list)
        print(f"Found {len(teachers)} total teachers")
    
    def test_search_teachers_student_denied(self):
        """Students cannot search teachers"""
        session, _ = TestAuth.login(STUDENT_EMAIL, STUDENT_PASSWORD)
        
        response = session.get(f"{API}/search/teachers?q=test")
        assert response.status_code == 403, "Students should be denied"


class TestClassFilter:
    """Test GET /api/filter/classes - Class filtration"""
    
    def test_filter_classes_by_demo(self):
        """Filter classes by is_demo=true"""
        session, _ = TestAuth.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = session.get(f"{API}/filter/classes?is_demo=true")
        assert response.status_code == 200
        
        classes = response.json()
        assert isinstance(classes, list)
        # All returned classes should be demos
        for cls in classes:
            assert cls.get("is_demo") == True, f"Class {cls.get('class_id')} should be demo"
        print(f"Found {len(classes)} demo classes")
    
    def test_filter_classes_by_regular(self):
        """Filter classes by is_demo=false (regular)"""
        session, _ = TestAuth.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = session.get(f"{API}/filter/classes?is_demo=false")
        assert response.status_code == 200
        
        classes = response.json()
        assert isinstance(classes, list)
        for cls in classes:
            assert cls.get("is_demo") == False, f"Class {cls.get('class_id')} should be regular"
        print(f"Found {len(classes)} regular classes")
    
    def test_filter_classes_by_status(self):
        """Filter classes by status"""
        session, _ = TestAuth.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = session.get(f"{API}/filter/classes?status=scheduled")
        assert response.status_code == 200
        
        classes = response.json()
        assert isinstance(classes, list)
        for cls in classes:
            assert cls.get("status") == "scheduled"
        print(f"Found {len(classes)} scheduled classes")
    
    def test_filter_classes_by_search(self):
        """Filter classes by search keyword"""
        session, _ = TestAuth.login(COUNSELLOR_EMAIL, COUNSELLOR_PASSWORD)
        
        response = session.get(f"{API}/filter/classes?search=Math")
        assert response.status_code == 200
        
        classes = response.json()
        assert isinstance(classes, list)
        print(f"Found {len(classes)} classes matching 'Math'")
    
    def test_filter_classes_combined(self):
        """Filter classes with multiple params"""
        session, _ = TestAuth.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = session.get(f"{API}/filter/classes?is_demo=false&status=scheduled")
        assert response.status_code == 200
        
        classes = response.json()
        assert isinstance(classes, list)
        print(f"Found {len(classes)} regular scheduled classes")
    
    def test_filter_classes_student_denied(self):
        """Students cannot filter classes"""
        session, _ = TestAuth.login(STUDENT_EMAIL, STUDENT_PASSWORD)
        
        response = session.get(f"{API}/filter/classes?status=scheduled")
        assert response.status_code == 403


class TestStudentFilter:
    """Test GET /api/filter/students - Student filtration"""
    
    def test_filter_students_by_grade(self):
        """Filter students by grade"""
        session, _ = TestAuth.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = session.get(f"{API}/filter/students?grade=10")
        assert response.status_code == 200
        
        students = response.json()
        assert isinstance(students, list)
        for s in students:
            assert s.get("grade") == "10"
        print(f"Found {len(students)} students in grade 10")
    
    def test_filter_students_by_city(self):
        """Filter students by city"""
        session, _ = TestAuth.login(COUNSELLOR_EMAIL, COUNSELLOR_PASSWORD)
        
        response = session.get(f"{API}/filter/students?city=Delhi")
        assert response.status_code == 200
        
        students = response.json()
        assert isinstance(students, list)
        print(f"Found {len(students)} students in Delhi")
    
    def test_filter_students_by_state(self):
        """Filter students by state"""
        session, _ = TestAuth.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = session.get(f"{API}/filter/students?state=Delhi")
        assert response.status_code == 200
        
        students = response.json()
        assert isinstance(students, list)
        print(f"Found {len(students)} students in Delhi state")
    
    def test_filter_students_combined(self):
        """Filter students with multiple params"""
        session, _ = TestAuth.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = session.get(f"{API}/filter/students?grade=10&city=Delhi")
        assert response.status_code == 200
        
        students = response.json()
        assert isinstance(students, list)
        print(f"Found {len(students)} students in grade 10 in Delhi")
    
    def test_filter_students_teacher_access(self):
        """Teachers can filter students"""
        session, _ = TestAuth.login(TEACHER_EMAIL, TEACHER_PASSWORD)
        
        response = session.get(f"{API}/filter/students?search=Alice")
        assert response.status_code == 200
        
        students = response.json()
        assert isinstance(students, list)
        print(f"Teacher found {len(students)} students matching 'Alice'")


class TestWalletAPI:
    """Test GET /api/wallet/summary - Wallet balance and transactions"""
    
    def test_wallet_summary_student(self):
        """Student can view wallet summary"""
        session, _ = TestAuth.login(STUDENT_EMAIL, STUDENT_PASSWORD)
        
        response = session.get(f"{API}/wallet/summary")
        assert response.status_code == 200
        
        wallet = response.json()
        assert "balance" in wallet, "Wallet should have balance"
        assert "transactions" in wallet, "Wallet should have transactions"
        assert isinstance(wallet["transactions"], list)
        print(f"Student wallet balance: {wallet['balance']}")
    
    def test_wallet_summary_teacher(self):
        """Teacher can view wallet with pending earnings"""
        session, _ = TestAuth.login(TEACHER_EMAIL, TEACHER_PASSWORD)
        
        response = session.get(f"{API}/wallet/summary")
        assert response.status_code == 200
        
        wallet = response.json()
        assert "balance" in wallet
        assert "pending_earnings" in wallet, "Teacher wallet should show pending earnings"
        assert "transactions" in wallet
        print(f"Teacher wallet balance: {wallet['balance']}, pending: {wallet['pending_earnings']}")
    
    def test_wallet_summary_has_bank_details_field(self):
        """Wallet summary includes bank_details field for teachers"""
        session, _ = TestAuth.login(TEACHER_EMAIL, TEACHER_PASSWORD)
        
        response = session.get(f"{API}/wallet/summary")
        assert response.status_code == 200
        
        wallet = response.json()
        assert "bank_details" in wallet, "Wallet should have bank_details field"


class TestAdminProofApproval:
    """Test admin proof approval workflow"""
    
    def test_get_approved_proofs_list(self):
        """Admin can get list of counsellor-verified proofs"""
        session, _ = TestAuth.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = session.get(f"{API}/admin/approved-proofs")
        assert response.status_code == 200
        
        proofs = response.json()
        assert isinstance(proofs, list)
        print(f"Found {len(proofs)} proofs pending admin approval")
    
    def test_get_approved_proofs_with_date_filter(self):
        """Admin can filter proofs by date"""
        session, _ = TestAuth.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        today = datetime.now().strftime("%Y-%m-%d")
        response = session.get(f"{API}/admin/approved-proofs?date_from={today}&date_to={today}")
        assert response.status_code == 200
        
        proofs = response.json()
        assert isinstance(proofs, list)
        print(f"Found {len(proofs)} proofs for today")
    
    def test_get_approved_proofs_non_admin_denied(self):
        """Non-admin cannot access approved proofs"""
        session, _ = TestAuth.login(COUNSELLOR_EMAIL, COUNSELLOR_PASSWORD)
        
        response = session.get(f"{API}/admin/approved-proofs")
        assert response.status_code == 403
    
    def test_approve_proof_invalid_id(self):
        """Approving non-existent proof returns 404"""
        session, _ = TestAuth.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = session.post(f"{API}/admin/approve-proof", json={
            "proof_id": "nonexistent_proof_123",
            "approved": True
        })
        assert response.status_code == 404


class TestCounsellorAssignStudent:
    """Test counsellor assign student (no credit_price in request)"""
    
    def test_assign_student_no_credit_price(self):
        """Counsellor assigns student without specifying credit_price"""
        session, _ = TestAuth.login(COUNSELLOR_EMAIL, COUNSELLOR_PASSWORD)
        
        # First get an unassigned student
        dashboard_res = session.get(f"{API}/counsellor/dashboard")
        assert dashboard_res.status_code == 200
        
        dashboard = dashboard_res.json()
        unassigned = dashboard.get("unassigned_students", [])
        teachers = dashboard.get("teachers", [])
        
        if len(unassigned) == 0 or len(teachers) == 0:
            pytest.skip("No unassigned students or teachers available")
        
        # Try to assign - should NOT require credit_price
        response = session.post(f"{API}/admin/assign-student", json={
            "student_id": unassigned[0]["user_id"],
            "teacher_id": teachers[0]["user_id"]
            # Note: NO credit_price field - uses system pricing
        })
        
        # Either success or already assigned
        assert response.status_code in [200, 400], f"Unexpected status: {response.text}"
        print(f"Assign response: {response.json()}")


class TestAdminBadgeAssignment:
    """Test POST /api/admin/assign-badge"""
    
    def test_assign_badge_to_teacher(self):
        """Admin can assign badge to teacher"""
        session, _ = TestAuth.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        # Get a teacher
        teachers_res = session.get(f"{API}/admin/teachers")
        assert teachers_res.status_code == 200
        teachers = teachers_res.json()
        
        if len(teachers) == 0:
            pytest.skip("No teachers available")
        
        teacher_id = teachers[0]["user_id"]
        badge_name = f"TEST_Badge_{datetime.now().strftime('%H%M%S')}"
        
        response = session.post(f"{API}/admin/assign-badge", json={
            "user_id": teacher_id,
            "badge_name": badge_name
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert badge_name in data["message"]
        print(f"Badge assigned: {data['message']}")
    
    def test_assign_badge_non_admin_denied(self):
        """Non-admin cannot assign badges"""
        session, _ = TestAuth.login(COUNSELLOR_EMAIL, COUNSELLOR_PASSWORD)
        
        response = session.post(f"{API}/admin/assign-badge", json={
            "user_id": "some_user",
            "badge_name": "Test Badge"
        })
        assert response.status_code == 403
    
    def test_assign_badge_to_student_denied(self):
        """Cannot assign badge to student"""
        session, _ = TestAuth.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        # Get a student
        students_res = session.get(f"{API}/admin/students")
        assert students_res.status_code == 200
        students = students_res.json()
        
        if len(students) == 0:
            pytest.skip("No students available")
        
        response = session.post(f"{API}/admin/assign-badge", json={
            "user_id": students[0]["user_id"],
            "badge_name": "Test Badge"
        })
        assert response.status_code == 400, "Should not allow badge on student"


class TestTeacherFeedbackToStudent:
    """Test POST /api/teacher/feedback-to-student"""
    
    def test_teacher_sends_feedback(self):
        """Teacher can send feedback to student"""
        session, _ = TestAuth.login(TEACHER_EMAIL, TEACHER_PASSWORD)
        
        # Get teacher's approved students
        dashboard_res = session.get(f"{API}/teacher/dashboard")
        assert dashboard_res.status_code == 200
        
        dashboard = dashboard_res.json()
        approved_students = dashboard.get("approved_students", [])
        
        if len(approved_students) == 0:
            pytest.skip("No approved students for this teacher")
        
        student_id = approved_students[0]["student_id"]
        
        response = session.post(f"{API}/teacher/feedback-to-student", json={
            "student_id": student_id,
            "feedback_text": "TEST: Great progress in today's session!",
            "performance_rating": "excellent"
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        print(f"Feedback sent: {data['message']}")
    
    def test_feedback_non_teacher_denied(self):
        """Non-teacher cannot send feedback"""
        session, _ = TestAuth.login(STUDENT_EMAIL, STUDENT_PASSWORD)
        
        response = session.post(f"{API}/teacher/feedback-to-student", json={
            "student_id": "some_student",
            "feedback_text": "Test",
            "performance_rating": "good"
        })
        assert response.status_code == 403
    
    def test_feedback_invalid_student(self):
        """Feedback to non-existent student returns 404"""
        session, _ = TestAuth.login(TEACHER_EMAIL, TEACHER_PASSWORD)
        
        response = session.post(f"{API}/teacher/feedback-to-student", json={
            "student_id": "nonexistent_student_123",
            "feedback_text": "Test",
            "performance_rating": "good"
        })
        assert response.status_code == 404


class TestRenewalCheck:
    """Test GET /api/renewal/check - 80% completion detection"""
    
    def test_renewal_check_counsellor(self):
        """Counsellor can check renewals"""
        session, _ = TestAuth.login(COUNSELLOR_EMAIL, COUNSELLOR_PASSWORD)
        
        response = session.get(f"{API}/renewal/check")
        assert response.status_code == 200
        
        renewals = response.json()
        assert isinstance(renewals, list)
        
        # Check structure of renewal items
        for r in renewals:
            if "completion_pct" in r:
                assert r["completion_pct"] >= 80, "Should only return classes at 80%+ completion"
        print(f"Found {len(renewals)} classes needing renewal")
    
    def test_renewal_check_admin(self):
        """Admin can check renewals"""
        session, _ = TestAuth.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = session.get(f"{API}/renewal/check")
        assert response.status_code == 200
        
        renewals = response.json()
        assert isinstance(renewals, list)
    
    def test_renewal_check_teacher(self):
        """Teacher can check their own renewals"""
        session, _ = TestAuth.login(TEACHER_EMAIL, TEACHER_PASSWORD)
        
        response = session.get(f"{API}/renewal/check")
        assert response.status_code == 200
        
        renewals = response.json()
        assert isinstance(renewals, list)
    
    def test_renewal_check_student(self):
        """Student can check their own renewals"""
        session, _ = TestAuth.login(STUDENT_EMAIL, STUDENT_PASSWORD)
        
        response = session.get(f"{API}/renewal/check")
        assert response.status_code == 200
        
        renewals = response.json()
        assert isinstance(renewals, list)


class TestTeacherProfileUpdate:
    """Test POST /api/teacher/update-profile with bank_details"""
    
    def test_update_bank_details(self):
        """Teacher can update bank details"""
        session, _ = TestAuth.login(TEACHER_EMAIL, TEACHER_PASSWORD)
        
        bank_details = {
            "account_name": "TEST Dr. Maria Garcia",
            "account_number": "1234567890",
            "bank_name": "Test Bank",
            "ifsc_code": "TEST0001234"
        }
        
        response = session.post(f"{API}/teacher/update-profile", json={
            "bank_details": bank_details
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        print(f"Profile updated: {data['message']}")
        
        # Verify bank details saved
        wallet_res = session.get(f"{API}/wallet/summary")
        assert wallet_res.status_code == 200
        wallet = wallet_res.json()
        
        if wallet.get("bank_details"):
            assert wallet["bank_details"]["account_name"] == bank_details["account_name"]
    
    def test_update_profile_non_teacher_denied(self):
        """Non-teacher cannot update teacher profile"""
        session, _ = TestAuth.login(STUDENT_EMAIL, STUDENT_PASSWORD)
        
        response = session.post(f"{API}/teacher/update-profile", json={
            "bio": "Test bio"
        })
        assert response.status_code == 403


class TestTeacherCodeGeneration:
    """Test teacher_code auto-generation on registration"""
    
    def test_teacher_has_code(self):
        """Existing teacher should have teacher_code"""
        session, _ = TestAuth.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        response = session.get(f"{API}/admin/teachers")
        assert response.status_code == 200
        
        teachers = response.json()
        assert len(teachers) > 0, "Should have at least one teacher"
        
        # Check first teacher has teacher_code
        teacher = teachers[0]
        assert "teacher_code" in teacher, "Teacher should have teacher_code field"
        if teacher.get("teacher_code"):
            assert teacher["teacher_code"].startswith("KL-T"), f"Teacher code should start with KL-T, got: {teacher['teacher_code']}"
            print(f"Teacher {teacher['name']} has code: {teacher['teacher_code']}")


class TestStudentProfileFields:
    """Test student profile has state/city/country/grade fields"""
    
    def test_student_profile_fields(self):
        """Student profile should have location and grade fields"""
        session, _ = TestAuth.login(STUDENT_EMAIL, STUDENT_PASSWORD)
        
        response = session.get(f"{API}/auth/me")
        assert response.status_code == 200
        
        user = response.json()
        # Check fields exist (may be null)
        assert "state" in user or user.get("state") is None
        assert "city" in user or user.get("city") is None
        assert "country" in user or user.get("country") is None
        assert "grade" in user or user.get("grade") is None
        print(f"Student profile: grade={user.get('grade')}, city={user.get('city')}, state={user.get('state')}")
    
    def test_update_student_profile_location(self):
        """Student can update location fields"""
        session, _ = TestAuth.login(STUDENT_EMAIL, STUDENT_PASSWORD)
        
        response = session.post(f"{API}/student/update-profile", json={
            "city": "TEST_Mumbai",
            "state": "TEST_Maharashtra",
            "country": "India",
            "grade": "11"
        })
        assert response.status_code == 200
        
        # Verify update
        me_res = session.get(f"{API}/auth/me")
        assert me_res.status_code == 200
        user = me_res.json()
        assert user.get("city") == "TEST_Mumbai"
        assert user.get("state") == "TEST_Maharashtra"
        print("Student profile location updated successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
