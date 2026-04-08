"""
Iteration 8 Tests: UI Overhaul Features
- Admin Dashboard: Credentials tab, Counsellors tab, Badge templates
- Teacher Dashboard: Grouped student view, Classes of the Day
- Backend endpoints: /admin/counsellor-tracking, /admin/badge-templates, /admin/reset-password
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAdminCredentialManagement:
    """Tests for Admin Credentials tab features"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin before each test"""
        self.session = requests.Session()
        login_res = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "info@kaimeralearning.com",
            "password": "solidarity&peace2023"
        })
        assert login_res.status_code == 200, f"Admin login failed: {login_res.text}"
        self.admin_user = login_res.json()
        yield
        self.session.close()
    
    def test_admin_get_all_users(self):
        """GET /api/admin/all-users - Admin can list all users"""
        res = self.session.get(f"{BASE_URL}/api/admin/all-users")
        assert res.status_code == 200, f"Failed: {res.text}"
        users = res.json()
        assert isinstance(users, list), "Should return list of users"
        assert len(users) > 0, "Should have at least one user"
        # Verify user structure
        user = users[0]
        assert "user_id" in user, "User should have user_id"
        assert "email" in user, "User should have email"
        assert "role" in user, "User should have role"
        assert "password_hash" not in user, "Password hash should be excluded"
        print(f"PASS: Got {len(users)} users")
    
    def test_admin_reset_password(self):
        """POST /api/admin/reset-password - Admin can reset user password"""
        # Reset password for teacher1
        res = self.session.post(f"{BASE_URL}/api/admin/reset-password", json={
            "email": "teacher1@kaimera.com",
            "new_password": "password123"  # Reset to original
        })
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        assert "message" in data, "Should return success message"
        assert "teacher" in data.get("role", ""), "Should return user role"
        print(f"PASS: Password reset - {data['message']}")
    
    def test_admin_reset_password_invalid_email(self):
        """POST /api/admin/reset-password - Invalid email returns 404"""
        res = self.session.post(f"{BASE_URL}/api/admin/reset-password", json={
            "email": "nonexistent@test.com",
            "new_password": "newpass123"
        })
        assert res.status_code == 404, f"Expected 404, got {res.status_code}"
        print("PASS: Invalid email returns 404")
    
    def test_admin_reset_password_missing_fields(self):
        """POST /api/admin/reset-password - Missing fields returns 400"""
        res = self.session.post(f"{BASE_URL}/api/admin/reset-password", json={
            "email": "teacher1@kaimera.com"
        })
        assert res.status_code == 400, f"Expected 400, got {res.status_code}"
        print("PASS: Missing password returns 400")
    
    def test_admin_get_user_detail(self):
        """GET /api/admin/user-detail/{user_id} - Admin can view user details"""
        # First get a user_id
        users_res = self.session.get(f"{BASE_URL}/api/admin/all-users")
        users = users_res.json()
        teacher = next((u for u in users if u.get("role") == "teacher"), None)
        assert teacher, "Should have at least one teacher"
        
        res = self.session.get(f"{BASE_URL}/api/admin/user-detail/{teacher['user_id']}")
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        assert "user" in data, "Should have user object"
        assert data["user"]["user_id"] == teacher["user_id"], "User ID should match"
        print(f"PASS: Got user detail for {data['user']['name']}")


class TestAdminBadgeTemplates:
    """Tests for Admin Badge template management"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin before each test"""
        self.session = requests.Session()
        login_res = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "info@kaimeralearning.com",
            "password": "solidarity&peace2023"
        })
        assert login_res.status_code == 200, f"Admin login failed: {login_res.text}"
        yield
        self.session.close()
    
    def test_get_badge_templates(self):
        """GET /api/admin/badge-templates - Admin can list badge templates"""
        res = self.session.get(f"{BASE_URL}/api/admin/badge-templates")
        assert res.status_code == 200, f"Failed: {res.text}"
        templates = res.json()
        assert isinstance(templates, list), "Should return list"
        print(f"PASS: Got {len(templates)} badge templates")
    
    def test_create_badge_template(self):
        """POST /api/admin/badge-template - Admin can create badge template"""
        import uuid
        badge_name = f"TEST_Badge_{uuid.uuid4().hex[:6]}"
        res = self.session.post(f"{BASE_URL}/api/admin/badge-template", json={
            "name": badge_name,
            "description": "Test badge for iteration 8"
        })
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        assert "message" in data, "Should return success message"
        print(f"PASS: Created badge template '{badge_name}'")
        
        # Verify it appears in list
        list_res = self.session.get(f"{BASE_URL}/api/admin/badge-templates")
        templates = list_res.json()
        found = any(t["name"] == badge_name for t in templates)
        assert found, "Created badge should appear in list"
        print("PASS: Badge template verified in list")
    
    def test_create_duplicate_badge_template(self):
        """POST /api/admin/badge-template - Duplicate name returns 400"""
        import uuid
        badge_name = f"TEST_Dup_{uuid.uuid4().hex[:6]}"
        # Create first
        self.session.post(f"{BASE_URL}/api/admin/badge-template", json={"name": badge_name})
        # Try duplicate
        res = self.session.post(f"{BASE_URL}/api/admin/badge-template", json={"name": badge_name})
        assert res.status_code == 400, f"Expected 400, got {res.status_code}"
        print("PASS: Duplicate badge returns 400")
    
    def test_delete_badge_template(self):
        """DELETE /api/admin/badge-template/{badge_id} - Admin can delete template"""
        import uuid
        badge_name = f"TEST_Del_{uuid.uuid4().hex[:6]}"
        # Create
        self.session.post(f"{BASE_URL}/api/admin/badge-template", json={"name": badge_name})
        # Get badge_id
        list_res = self.session.get(f"{BASE_URL}/api/admin/badge-templates")
        templates = list_res.json()
        badge = next((t for t in templates if t["name"] == badge_name), None)
        assert badge, "Badge should exist"
        
        # Delete
        del_res = self.session.delete(f"{BASE_URL}/api/admin/badge-template/{badge['badge_id']}")
        assert del_res.status_code == 200, f"Failed: {del_res.text}"
        print(f"PASS: Deleted badge template '{badge_name}'")


class TestAdminCounsellorTracking:
    """Tests for Admin Counsellor tracking tab"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin before each test"""
        self.session = requests.Session()
        login_res = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "info@kaimeralearning.com",
            "password": "solidarity&peace2023"
        })
        assert login_res.status_code == 200, f"Admin login failed: {login_res.text}"
        yield
        self.session.close()
    
    def test_get_counsellor_tracking(self):
        """GET /api/admin/counsellor-tracking - Admin can view counsellor stats"""
        res = self.session.get(f"{BASE_URL}/api/admin/counsellor-tracking")
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        assert isinstance(data, list), "Should return list of counsellors"
        
        if len(data) > 0:
            counsellor = data[0]
            assert "user_id" in counsellor, "Should have user_id"
            assert "name" in counsellor, "Should have name"
            assert "total_assignments" in counsellor, "Should have total_assignments"
            assert "active_assignments" in counsellor, "Should have active_assignments"
            assert "pending_assignments" in counsellor, "Should have pending_assignments"
            assert "rejected_assignments" in counsellor, "Should have rejected_assignments"
            print(f"PASS: Got tracking for {len(data)} counsellors")
            print(f"  First counsellor: {counsellor['name']} - {counsellor['total_assignments']} total assignments")
        else:
            print("PASS: No counsellors found (empty list returned)")


class TestTeacherDashboardEndpoints:
    """Tests for Teacher Dashboard grouped view endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as teacher before each test"""
        self.session = requests.Session()
        login_res = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "teacher1@kaimera.com",
            "password": "password123"
        })
        assert login_res.status_code == 200, f"Teacher login failed: {login_res.text}"
        self.teacher_user = login_res.json()
        yield
        self.session.close()
    
    def test_teacher_grouped_classes(self):
        """GET /api/teacher/grouped-classes - Teacher gets grouped student view"""
        res = self.session.get(f"{BASE_URL}/api/teacher/grouped-classes")
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        
        # Verify structure
        assert "today" in data, "Should have 'today' key for classes of the day"
        assert "by_student" in data, "Should have 'by_student' key for grouped view"
        assert "ended_count" in data, "Should have 'ended_count' key"
        
        assert isinstance(data["today"], list), "'today' should be a list"
        assert isinstance(data["by_student"], list), "'by_student' should be a list"
        
        print(f"PASS: Got grouped classes - {len(data['today'])} today, {len(data['by_student'])} student groups")
        
        # If there are student groups, verify structure
        if len(data["by_student"]) > 0:
            group = data["by_student"][0]
            assert "student_id" in group, "Group should have student_id"
            assert "student_name" in group, "Group should have student_name"
            assert "classes" in group, "Group should have classes list"
            print(f"  First student group: {group['student_name']} with {len(group['classes'])} classes")
    
    def test_teacher_dashboard(self):
        """GET /api/teacher/dashboard - Teacher dashboard data"""
        res = self.session.get(f"{BASE_URL}/api/teacher/dashboard")
        assert res.status_code == 200, f"Failed: {res.text}"
        data = res.json()
        
        assert "pending_assignments" in data, "Should have pending_assignments"
        assert "approved_students" in data, "Should have approved_students"
        print(f"PASS: Teacher dashboard - {len(data.get('pending_assignments', []))} pending, {len(data.get('approved_students', []))} approved")


class TestNonAdminAccessDenied:
    """Tests that non-admin users cannot access admin endpoints"""
    
    def test_teacher_cannot_access_counsellor_tracking(self):
        """Teacher cannot access /api/admin/counsellor-tracking"""
        session = requests.Session()
        session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "teacher1@kaimera.com",
            "password": "password123"
        })
        res = session.get(f"{BASE_URL}/api/admin/counsellor-tracking")
        assert res.status_code == 403, f"Expected 403, got {res.status_code}"
        print("PASS: Teacher denied access to counsellor tracking")
        session.close()
    
    def test_student_cannot_access_badge_templates(self):
        """Student cannot access /api/admin/badge-templates"""
        session = requests.Session()
        session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "student1@kaimera.com",
            "password": "password123"
        })
        res = session.get(f"{BASE_URL}/api/admin/badge-templates")
        assert res.status_code == 403, f"Expected 403, got {res.status_code}"
        print("PASS: Student denied access to badge templates")
        session.close()
    
    def test_teacher_cannot_reset_password(self):
        """Teacher cannot access /api/admin/reset-password"""
        session = requests.Session()
        session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "teacher1@kaimera.com",
            "password": "password123"
        })
        res = session.post(f"{BASE_URL}/api/admin/reset-password", json={
            "email": "student1@kaimera.com",
            "new_password": "hacked123"
        })
        assert res.status_code == 403, f"Expected 403, got {res.status_code}"
        print("PASS: Teacher denied access to reset password")
        session.close()


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_badges(self):
        """Remove TEST_ prefixed badge templates"""
        session = requests.Session()
        session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "info@kaimeralearning.com",
            "password": "solidarity&peace2023"
        })
        
        # Get all templates
        res = session.get(f"{BASE_URL}/api/admin/badge-templates")
        templates = res.json()
        
        # Delete TEST_ prefixed ones
        deleted = 0
        for t in templates:
            if t["name"].startswith("TEST_"):
                session.delete(f"{BASE_URL}/api/admin/badge-template/{t['badge_id']}")
                deleted += 1
        
        print(f"PASS: Cleaned up {deleted} test badge templates")
        session.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
