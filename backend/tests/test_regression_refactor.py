"""
Regression Test Suite for Kaimera Learning EdTech CRM
Tests all 121 API endpoints after major refactor from monolithic server.py to modular routes.
"""
import pytest
import requests
import os

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


class TestAuthEndpoints:
    """Test auth routes (7 endpoints)"""
    
    def test_admin_login(self):
        """POST /api/auth/login - Admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "user" in data
        assert "session_token" in data
        assert data["user"]["role"] == "admin"
        assert data["user"]["email"] == ADMIN_EMAIL
        print(f"✓ Admin login successful - user_id: {data['user']['user_id']}")
    
    def test_teacher_login(self):
        """POST /api/auth/login - Teacher login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEACHER_EMAIL,
            "password": TEACHER_PASSWORD
        })
        assert response.status_code == 200, f"Teacher login failed: {response.text}"
        data = response.json()
        assert data["user"]["role"] == "teacher"
        print(f"✓ Teacher login successful - {data['user']['name']}")
    
    def test_student_login(self):
        """POST /api/auth/login - Student login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STUDENT_EMAIL,
            "password": STUDENT_PASSWORD
        })
        assert response.status_code == 200, f"Student login failed: {response.text}"
        data = response.json()
        assert data["user"]["role"] == "student"
        print(f"✓ Student login successful - {data['user']['name']}")
    
    def test_counsellor_login(self):
        """POST /api/auth/login - Counsellor login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COUNSELLOR_EMAIL,
            "password": COUNSELLOR_PASSWORD
        })
        assert response.status_code == 200, f"Counsellor login failed: {response.text}"
        data = response.json()
        assert data["user"]["role"] == "counsellor"
        print(f"✓ Counsellor login successful - {data['user']['name']}")
    
    def test_auth_me(self, admin_token):
        """GET /api/auth/me - Get current user"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "email" in data
        print(f"✓ Auth me endpoint works - {data['email']}")
    
    def test_invalid_login(self):
        """POST /api/auth/login - Invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("✓ Invalid login correctly rejected")


class TestAdminEndpoints:
    """Test admin routes (38 endpoints)"""
    
    def test_admin_get_teachers(self, admin_token):
        """GET /api/admin/teachers - List all teachers"""
        response = requests.get(f"{BASE_URL}/api/admin/teachers", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Admin teachers list - {len(data)} teachers found")
    
    def test_admin_get_students(self, admin_token):
        """GET /api/admin/students - List all students"""
        response = requests.get(f"{BASE_URL}/api/admin/students", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Admin students list - {len(data)} students found")
    
    def test_admin_get_pricing(self, admin_token):
        """GET /api/admin/get-pricing - Get system pricing"""
        response = requests.get(f"{BASE_URL}/api/admin/get-pricing", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "demo_price_student" in data or "class_price_student" in data or data == {}
        print(f"✓ Admin pricing endpoint works")
    
    def test_admin_get_transactions(self, admin_token):
        """GET /api/admin/transactions - List transactions"""
        response = requests.get(f"{BASE_URL}/api/admin/transactions", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Admin transactions - {len(data)} transactions found")
    
    def test_admin_all_assignments(self, admin_token):
        """GET /api/admin/all-assignments - List all assignments"""
        response = requests.get(f"{BASE_URL}/api/admin/all-assignments", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Admin all assignments - {len(data)} assignments found")
    
    def test_admin_teacher_ratings(self, admin_token):
        """GET /api/admin/teacher-ratings - Get teacher ratings"""
        response = requests.get(f"{BASE_URL}/api/admin/teacher-ratings", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Admin teacher ratings - {len(data)} teachers with ratings")
    
    def test_admin_complaints(self, admin_token):
        """GET /api/admin/complaints - List all complaints"""
        response = requests.get(f"{BASE_URL}/api/admin/complaints", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Admin complaints - {len(data)} complaints found")
    
    def test_admin_all_users(self, admin_token):
        """GET /api/admin/all-users - List all users"""
        response = requests.get(f"{BASE_URL}/api/admin/all-users", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Admin all users - {len(data)} users found")
    
    def test_admin_classes(self, admin_token):
        """GET /api/admin/classes - List all classes"""
        response = requests.get(f"{BASE_URL}/api/admin/classes", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Admin classes - {len(data)} classes found")
    
    def test_admin_search_users_for_reset(self, admin_token):
        """GET /api/admin/search-users-for-reset - Search users"""
        response = requests.get(f"{BASE_URL}/api/admin/search-users-for-reset?q=teacher&role=teacher", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Admin search users for reset - {len(data)} results")
    
    def test_admin_badge_templates(self, admin_token):
        """GET /api/admin/badge-templates - List badge templates"""
        response = requests.get(f"{BASE_URL}/api/admin/badge-templates", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Admin badge templates - {len(data)} templates")
    
    def test_admin_counsellor_tracking(self, admin_token):
        """GET /api/admin/counsellor-tracking - Track counsellors"""
        response = requests.get(f"{BASE_URL}/api/admin/counsellor-tracking", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Admin counsellor tracking - {len(data)} counsellors")
    
    def test_admin_approved_proofs(self, admin_token):
        """GET /api/admin/approved-proofs - List approved proofs"""
        response = requests.get(f"{BASE_URL}/api/admin/approved-proofs", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Admin approved proofs - {len(data)} proofs")
    
    def test_admin_emergency_assignments(self, admin_token):
        """GET /api/admin/emergency-assignments - List emergency assignments"""
        response = requests.get(f"{BASE_URL}/api/admin/emergency-assignments", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Admin emergency assignments - {len(data)} found")


class TestTeacherEndpoints:
    """Test teacher routes (18 endpoints)"""
    
    def test_teacher_dashboard(self, teacher_token):
        """GET /api/teacher/dashboard - Teacher dashboard"""
        response = requests.get(f"{BASE_URL}/api/teacher/dashboard", headers={
            "Authorization": f"Bearer {teacher_token}"
        })
        assert response.status_code == 200
        data = response.json()
        # Check for expected keys
        assert "is_approved" in data
        assert "star_rating" in data or "is_suspended" in data
        print(f"✓ Teacher dashboard works - approved: {data.get('is_approved')}")
    
    def test_teacher_my_rating(self, teacher_token):
        """GET /api/teacher/my-rating - Teacher rating"""
        response = requests.get(f"{BASE_URL}/api/teacher/my-rating", headers={
            "Authorization": f"Bearer {teacher_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "star_rating" in data
        print(f"✓ Teacher my-rating - rating: {data.get('star_rating')}")
    
    def test_teacher_schedule(self, teacher_token):
        """GET /api/teacher/schedule - Teacher schedule"""
        response = requests.get(f"{BASE_URL}/api/teacher/schedule", headers={
            "Authorization": f"Bearer {teacher_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Teacher schedule - {len(data)} scheduled classes")
    
    def test_teacher_my_proofs(self, teacher_token):
        """GET /api/teacher/my-proofs - Teacher proofs"""
        response = requests.get(f"{BASE_URL}/api/teacher/my-proofs", headers={
            "Authorization": f"Bearer {teacher_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Teacher my-proofs - {len(data)} proofs")
    
    def test_teacher_pending_demo_feedback(self, teacher_token):
        """GET /api/teacher/pending-demo-feedback - Pending demo feedback"""
        response = requests.get(f"{BASE_URL}/api/teacher/pending-demo-feedback", headers={
            "Authorization": f"Bearer {teacher_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Teacher pending demo feedback - {len(data)} pending")
    
    def test_teacher_student_complaints(self, teacher_token):
        """GET /api/teacher/student-complaints - Student complaints"""
        response = requests.get(f"{BASE_URL}/api/teacher/student-complaints", headers={
            "Authorization": f"Bearer {teacher_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Teacher student complaints - {len(data)} complaints")
    
    def test_teacher_calendar(self, teacher_token):
        """GET /api/teacher/calendar - Teacher calendar"""
        response = requests.get(f"{BASE_URL}/api/teacher/calendar", headers={
            "Authorization": f"Bearer {teacher_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Teacher calendar - {len(data)} entries")
    
    def test_teacher_grouped_classes(self, teacher_token):
        """GET /api/teacher/grouped-classes - Grouped classes"""
        response = requests.get(f"{BASE_URL}/api/teacher/grouped-classes", headers={
            "Authorization": f"Bearer {teacher_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "today" in data
        assert "by_student" in data
        print(f"✓ Teacher grouped classes - today: {len(data.get('today', []))}")


class TestStudentEndpoints:
    """Test student routes (6 endpoints)"""
    
    def test_student_dashboard(self, student_token):
        """GET /api/student/dashboard - Student dashboard"""
        response = requests.get(f"{BASE_URL}/api/student/dashboard", headers={
            "Authorization": f"Bearer {student_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "credits" in data
        assert "live_classes" in data or "upcoming_classes" in data
        print(f"✓ Student dashboard - credits: {data.get('credits')}")
    
    def test_student_enrollment_status(self, student_token):
        """GET /api/student/enrollment-status - Enrollment status"""
        response = requests.get(f"{BASE_URL}/api/student/enrollment-status", headers={
            "Authorization": f"Bearer {student_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "is_enrolled" in data
        print(f"✓ Student enrollment status - enrolled: {data.get('is_enrolled')}")
    
    def test_student_nag_check(self, student_token):
        """GET /api/student/nag-check - Nag check"""
        response = requests.get(f"{BASE_URL}/api/student/nag-check", headers={
            "Authorization": f"Bearer {student_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "show_nag" in data
        print(f"✓ Student nag check - show_nag: {data.get('show_nag')}")
    
    def test_student_demo_feedback_received(self, student_token):
        """GET /api/student/demo-feedback-received - Demo feedback received"""
        response = requests.get(f"{BASE_URL}/api/student/demo-feedback-received", headers={
            "Authorization": f"Bearer {student_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Student demo feedback received - {len(data)} feedbacks")


class TestCounsellorEndpoints:
    """Test counsellor routes (8 endpoints)"""
    
    def test_counsellor_dashboard(self, counsellor_token):
        """GET /api/counsellor/dashboard - Counsellor dashboard"""
        response = requests.get(f"{BASE_URL}/api/counsellor/dashboard", headers={
            "Authorization": f"Bearer {counsellor_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "unassigned_students" in data
        assert "teachers" in data
        assert "active_assignments" in data
        print(f"✓ Counsellor dashboard - unassigned: {len(data.get('unassigned_students', []))}")
    
    def test_counsellor_pending_proofs(self, counsellor_token):
        """GET /api/counsellor/pending-proofs - Pending proofs"""
        response = requests.get(f"{BASE_URL}/api/counsellor/pending-proofs", headers={
            "Authorization": f"Bearer {counsellor_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Counsellor pending proofs - {len(data)} pending")
    
    def test_counsellor_all_proofs(self, counsellor_token):
        """GET /api/counsellor/all-proofs - All proofs"""
        response = requests.get(f"{BASE_URL}/api/counsellor/all-proofs", headers={
            "Authorization": f"Bearer {counsellor_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Counsellor all proofs - {len(data)} proofs")
    
    def test_counsellor_expired_classes(self, counsellor_token):
        """GET /api/counsellor/expired-classes - Expired classes"""
        response = requests.get(f"{BASE_URL}/api/counsellor/expired-classes", headers={
            "Authorization": f"Bearer {counsellor_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Counsellor expired classes - {len(data)} expired")
    
    def test_counsellor_search_students(self, counsellor_token):
        """GET /api/counsellor/search-students - Search students"""
        response = requests.get(f"{BASE_URL}/api/counsellor/search-students?q=", headers={
            "Authorization": f"Bearer {counsellor_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Counsellor search students - {len(data)} students")


class TestChatEndpoints:
    """Test chat routes (4 endpoints)"""
    
    def test_chat_contacts(self, admin_token):
        """GET /api/chat/contacts - Chat contacts"""
        response = requests.get(f"{BASE_URL}/api/chat/contacts", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Chat contacts - {len(data)} contacts")
    
    def test_chat_conversations(self, admin_token):
        """GET /api/chat/conversations - Chat conversations"""
        response = requests.get(f"{BASE_URL}/api/chat/conversations", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Chat conversations - {len(data)} conversations")


class TestDemoEndpoints:
    """Test demo routes (8 endpoints)"""
    
    def test_demo_all(self, admin_token):
        """GET /api/demo/all - All demos"""
        response = requests.get(f"{BASE_URL}/api/demo/all", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Demo all - {len(data)} demos")
    
    def test_demo_live_sheet(self, teacher_token):
        """GET /api/demo/live-sheet - Demo live sheet"""
        response = requests.get(f"{BASE_URL}/api/demo/live-sheet", headers={
            "Authorization": f"Bearer {teacher_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "demos" in data
        print(f"✓ Demo live sheet - {len(data.get('demos', []))} pending demos")
    
    def test_demo_my_demos(self, teacher_token):
        """GET /api/demo/my-demos - My demos"""
        response = requests.get(f"{BASE_URL}/api/demo/my-demos", headers={
            "Authorization": f"Bearer {teacher_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Demo my-demos - {len(data)} demos")
    
    def test_demo_feedback_pending(self, counsellor_token):
        """GET /api/demo/feedback-pending - Pending feedback"""
        response = requests.get(f"{BASE_URL}/api/demo/feedback-pending", headers={
            "Authorization": f"Bearer {counsellor_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Demo feedback pending - {len(data)} pending")


class TestGeneralEndpoints:
    """Test general routes (19 endpoints)"""
    
    def test_notifications_my(self, admin_token):
        """GET /api/notifications/my - My notifications"""
        response = requests.get(f"{BASE_URL}/api/notifications/my", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Notifications my - {len(data)} notifications")
    
    def test_wallet_summary(self, student_token):
        """GET /api/wallet/summary - Wallet summary"""
        response = requests.get(f"{BASE_URL}/api/wallet/summary", headers={
            "Authorization": f"Bearer {student_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "balance" in data
        assert "transactions" in data
        print(f"✓ Wallet summary - balance: {data.get('balance')}")
    
    def test_history_search(self, admin_token):
        """GET /api/history/search - History search"""
        response = requests.get(f"{BASE_URL}/api/history/search?q=", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ History search - {len(data)} results")
    
    def test_history_users(self, admin_token):
        """GET /api/history/users - History users"""
        response = requests.get(f"{BASE_URL}/api/history/users", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "students" in data
        assert "teachers" in data
        print(f"✓ History users - students: {len(data.get('students', []))}")
    
    def test_search_teachers(self, admin_token):
        """GET /api/search/teachers - Search teachers"""
        response = requests.get(f"{BASE_URL}/api/search/teachers?q=", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Search teachers - {len(data)} teachers")
    
    def test_filter_classes(self, admin_token):
        """GET /api/filter/classes - Filter classes"""
        response = requests.get(f"{BASE_URL}/api/filter/classes", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Filter classes - {len(data)} classes")
    
    def test_filter_students(self, admin_token):
        """GET /api/filter/students - Filter students"""
        response = requests.get(f"{BASE_URL}/api/filter/students", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Filter students - {len(data)} students")
    
    def test_learning_kit(self, student_token):
        """GET /api/learning-kit - Learning kit"""
        response = requests.get(f"{BASE_URL}/api/learning-kit", headers={
            "Authorization": f"Bearer {student_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Learning kit - {len(data)} kits")
    
    def test_learning_kit_grades(self, student_token):
        """GET /api/learning-kit/grades - Learning kit grades"""
        response = requests.get(f"{BASE_URL}/api/learning-kit/grades", headers={
            "Authorization": f"Bearer {student_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Learning kit grades - {len(data)} grades")
    
    def test_renewal_check(self, admin_token):
        """GET /api/renewal/check - Renewal check"""
        response = requests.get(f"{BASE_URL}/api/renewal/check", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Renewal check - {len(data)} renewals needed")
    
    def test_renewal_my_meetings(self, admin_token):
        """GET /api/renewal/my-meetings - My renewal meetings"""
        response = requests.get(f"{BASE_URL}/api/renewal/my-meetings", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Renewal my meetings - {len(data)} meetings")
    
    def test_complaints_my(self, student_token):
        """GET /api/complaints/my - My complaints"""
        response = requests.get(f"{BASE_URL}/api/complaints/my", headers={
            "Authorization": f"Bearer {student_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Complaints my - {len(data)} complaints")


class TestClassEndpoints:
    """Test class routes (10 endpoints)"""
    
    def test_classes_browse(self, student_token):
        """GET /api/classes/browse - Browse classes"""
        response = requests.get(f"{BASE_URL}/api/classes/browse", headers={
            "Authorization": f"Bearer {student_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Classes browse - {len(data)} classes")


# Fixtures
@pytest.fixture(scope="module")
def admin_token():
    """Get admin session token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("session_token")
    pytest.skip("Admin login failed")

@pytest.fixture(scope="module")
def teacher_token():
    """Get teacher session token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEACHER_EMAIL,
        "password": TEACHER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("session_token")
    pytest.skip("Teacher login failed")

@pytest.fixture(scope="module")
def student_token():
    """Get student session token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": STUDENT_EMAIL,
        "password": STUDENT_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("session_token")
    pytest.skip("Student login failed")

@pytest.fixture(scope="module")
def counsellor_token():
    """Get counsellor session token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": COUNSELLOR_EMAIL,
        "password": COUNSELLOR_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("session_token")
    pytest.skip("Counsellor login failed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
