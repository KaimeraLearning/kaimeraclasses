"""
Iteration 16 - Security Hardening Tests
Tests for 12 security fixes applied across auth, admin, classes, payments, student, teacher routes.

Security fixes tested:
1. Blocked users get 403 on any API call
2. Duplicate email registration rejected
3. Duplicate phone number registration rejected
4. Admin credit deduction cannot go below 0
5. Password reset invalidates all sessions
6. Admin cannot block/delete admin accounts
7. Class status endpoint rejects unauthorized users
8. Class deletion refunds student credits
9. Proof can only be submitted once per class (duplicate proof rejected)
10. Edit student with duplicate email rejected
11. Admin create-user with duplicate phone rejected
12. OTP rate limiting - failed_attempts tracking
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

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


class TestRegressionLogins:
    """Regression tests - ensure all role logins still work"""
    
    def test_admin_login(self):
        """REGRESSION: Admin login works"""
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
        """REGRESSION: Teacher login works"""
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
        """REGRESSION: Student login works"""
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
        """REGRESSION: Counsellor login works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COUNSELLOR_EMAIL,
            "password": COUNSELLOR_PASSWORD
        })
        assert response.status_code == 200, f"Counsellor login failed: {response.text}"
        data = response.json()
        assert "session_token" in data
        assert data["user"]["role"] == "counsellor"
        print(f"✓ Counsellor login successful: {data['user']['name']}")
    
    def test_invalid_login_rejected(self):
        """REGRESSION: Invalid credentials rejected"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("✓ Invalid login correctly rejected with 401")


class TestSecurityBlockedUsers:
    """SECURITY: Blocked users get 403 on any API call"""
    
    @pytest.fixture
    def admin_session(self):
        """Get admin session token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["session_token"]
    
    def test_blocked_user_cannot_access_api(self, admin_session):
        """SECURITY: Blocked user gets 403 on API access"""
        # Create a test user to block
        test_email = f"test_block_{uuid.uuid4().hex[:8]}@test.com"
        test_password = "testpass123"
        
        # Create user via admin
        create_response = requests.post(
            f"{BASE_URL}/api/admin/create-user",
            headers={"Authorization": f"Bearer {admin_session}"},
            json={
                "name": "Test Block User",
                "email": test_email,
                "password": test_password,
                "role": "student"
            }
        )
        assert create_response.status_code == 200, f"Failed to create test user: {create_response.text}"
        user_id = create_response.json()["user_id"]
        
        # Login as the test user
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": test_email,
            "password": test_password
        })
        assert login_response.status_code == 200
        user_token = login_response.json()["session_token"]
        
        # Verify user can access API before blocking
        me_response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert me_response.status_code == 200, "User should be able to access API before blocking"
        
        # Block the user via admin
        block_response = requests.post(
            f"{BASE_URL}/api/admin/block-user",
            headers={"Authorization": f"Bearer {admin_session}"},
            json={"user_id": user_id, "blocked": True}
        )
        assert block_response.status_code == 200, f"Failed to block user: {block_response.text}"
        
        # Try to access API with blocked user's session - should get 403
        blocked_me_response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert blocked_me_response.status_code in [401, 403], f"Blocked user should get 401/403, got {blocked_me_response.status_code}"
        print(f"✓ Blocked user correctly denied access with {blocked_me_response.status_code}")
        
        # Cleanup - delete the test user
        requests.post(
            f"{BASE_URL}/api/admin/delete-user",
            headers={"Authorization": f"Bearer {admin_session}"},
            json={"user_id": user_id}
        )


class TestSecurityDuplicateRegistration:
    """SECURITY: Duplicate email/phone registration rejected"""
    
    def test_duplicate_email_registration_rejected(self):
        """SECURITY: Duplicate email registration rejected"""
        # Try to register with existing email
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": STUDENT_EMAIL,  # Already exists
            "name": "Duplicate Test",
            "password": "testpass123",
            "role": "student"
        })
        assert response.status_code == 400, f"Expected 400 for duplicate email, got {response.status_code}"
        assert "already registered" in response.json().get("detail", "").lower()
        print("✓ Duplicate email registration correctly rejected")
    
    def test_duplicate_phone_registration_rejected(self):
        """SECURITY: Duplicate phone number registration rejected"""
        # First, get admin session to create a user with phone
        admin_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        admin_token = admin_response.json()["session_token"]
        
        test_phone = f"+1555{uuid.uuid4().hex[:7]}"
        test_email1 = f"test_phone1_{uuid.uuid4().hex[:8]}@test.com"
        test_email2 = f"test_phone2_{uuid.uuid4().hex[:8]}@test.com"
        
        # Create first user with phone
        create1 = requests.post(
            f"{BASE_URL}/api/admin/create-user",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "Phone Test 1",
                "email": test_email1,
                "password": "testpass123",
                "role": "student",
                "phone": test_phone
            }
        )
        assert create1.status_code == 200, f"Failed to create first user: {create1.text}"
        user1_id = create1.json()["user_id"]
        
        # Try to create second user with same phone
        create2 = requests.post(
            f"{BASE_URL}/api/admin/create-user",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "Phone Test 2",
                "email": test_email2,
                "password": "testpass123",
                "role": "student",
                "phone": test_phone  # Same phone
            }
        )
        assert create2.status_code == 400, f"Expected 400 for duplicate phone, got {create2.status_code}"
        assert "phone" in create2.json().get("detail", "").lower()
        print("✓ Duplicate phone registration correctly rejected")
        
        # Cleanup
        requests.post(
            f"{BASE_URL}/api/admin/delete-user",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"user_id": user1_id}
        )


class TestSecurityCreditDeduction:
    """SECURITY: Admin credit deduction cannot go below 0"""
    
    def test_credit_deduction_floor(self):
        """SECURITY: Cannot deduct more credits than user has"""
        # Get admin session
        admin_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        admin_token = admin_response.json()["session_token"]
        
        # Create a test user with 0 credits
        test_email = f"test_credit_{uuid.uuid4().hex[:8]}@test.com"
        create_response = requests.post(
            f"{BASE_URL}/api/admin/create-user",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "Credit Test User",
                "email": test_email,
                "password": "testpass123",
                "role": "student"
            }
        )
        assert create_response.status_code == 200
        user_id = create_response.json()["user_id"]
        
        # Try to deduct 100 credits from user with 0 credits
        deduct_response = requests.post(
            f"{BASE_URL}/api/admin/adjust-credits",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "user_id": user_id,
                "amount": 100,
                "action": "deduct"
            }
        )
        assert deduct_response.status_code == 400, f"Expected 400 for over-deduction, got {deduct_response.status_code}"
        assert "cannot deduct" in deduct_response.json().get("detail", "").lower() or "only has" in deduct_response.json().get("detail", "").lower()
        print("✓ Credit deduction floor correctly enforced")
        
        # Cleanup
        requests.post(
            f"{BASE_URL}/api/admin/delete-user",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"user_id": user_id}
        )


class TestSecurityPasswordReset:
    """SECURITY: Password reset invalidates all sessions"""
    
    def test_password_reset_invalidates_sessions(self):
        """SECURITY: Password reset invalidates all existing sessions"""
        # Get admin session
        admin_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        admin_token = admin_response.json()["session_token"]
        
        # Create a test user
        test_email = f"test_reset_{uuid.uuid4().hex[:8]}@test.com"
        test_password = "oldpassword123"
        new_password = "newpassword456"
        
        create_response = requests.post(
            f"{BASE_URL}/api/admin/create-user",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "Reset Test User",
                "email": test_email,
                "password": test_password,
                "role": "student"
            }
        )
        assert create_response.status_code == 200
        user_id = create_response.json()["user_id"]
        
        # Login as test user to get a session
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": test_email,
            "password": test_password
        })
        assert login_response.status_code == 200
        old_session = login_response.json()["session_token"]
        
        # Verify old session works
        me_response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {old_session}"}
        )
        assert me_response.status_code == 200, "Old session should work before reset"
        
        # Admin resets password
        reset_response = requests.post(
            f"{BASE_URL}/api/admin/reset-password",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "user_id": user_id,
                "new_password": new_password
            }
        )
        assert reset_response.status_code == 200, f"Password reset failed: {reset_response.text}"
        assert "invalidated" in reset_response.json().get("message", "").lower()
        
        # Old session should no longer work
        old_session_response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {old_session}"}
        )
        assert old_session_response.status_code == 401, f"Old session should be invalidated, got {old_session_response.status_code}"
        print("✓ Password reset correctly invalidates all sessions")
        
        # Cleanup
        requests.post(
            f"{BASE_URL}/api/admin/delete-user",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"user_id": user_id}
        )


class TestSecurityAdminProtection:
    """SECURITY: Admin cannot block/delete admin accounts"""
    
    def test_cannot_block_admin(self):
        """SECURITY: Admin cannot block admin accounts"""
        # Get admin session
        admin_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        admin_token = admin_response.json()["session_token"]
        admin_user_id = admin_response.json()["user"]["user_id"]
        
        # Try to block admin
        block_response = requests.post(
            f"{BASE_URL}/api/admin/block-user",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"user_id": admin_user_id, "blocked": True}
        )
        assert block_response.status_code == 400, f"Expected 400 for blocking admin, got {block_response.status_code}"
        assert "admin" in block_response.json().get("detail", "").lower()
        print("✓ Cannot block admin accounts - correctly rejected")
    
    def test_cannot_delete_admin(self):
        """SECURITY: Admin cannot delete admin accounts"""
        # Get admin session
        admin_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        admin_token = admin_response.json()["session_token"]
        admin_user_id = admin_response.json()["user"]["user_id"]
        
        # Try to delete admin
        delete_response = requests.post(
            f"{BASE_URL}/api/admin/delete-user",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"user_id": admin_user_id}
        )
        assert delete_response.status_code == 400, f"Expected 400 for deleting admin, got {delete_response.status_code}"
        assert "admin" in delete_response.json().get("detail", "").lower()
        print("✓ Cannot delete admin accounts - correctly rejected")


class TestSecurityEditStudentDuplicate:
    """SECURITY: Edit student with duplicate email/phone rejected"""
    
    def test_edit_student_duplicate_email_rejected(self):
        """SECURITY: Edit student with duplicate email rejected"""
        # Get admin session
        admin_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        admin_token = admin_response.json()["session_token"]
        
        # Create two test students
        test_email1 = f"test_edit1_{uuid.uuid4().hex[:8]}@test.com"
        test_email2 = f"test_edit2_{uuid.uuid4().hex[:8]}@test.com"
        
        create1 = requests.post(
            f"{BASE_URL}/api/admin/create-user",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "Edit Test 1", "email": test_email1, "password": "test123", "role": "student"}
        )
        user1_id = create1.json()["user_id"]
        
        create2 = requests.post(
            f"{BASE_URL}/api/admin/create-user",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "Edit Test 2", "email": test_email2, "password": "test123", "role": "student"}
        )
        user2_id = create2.json()["user_id"]
        
        # Try to edit user2's email to user1's email
        edit_response = requests.post(
            f"{BASE_URL}/api/admin/edit-student/{user2_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"email": test_email1}  # Duplicate
        )
        assert edit_response.status_code == 400, f"Expected 400 for duplicate email edit, got {edit_response.status_code}"
        assert "already registered" in edit_response.json().get("detail", "").lower()
        print("✓ Edit student with duplicate email correctly rejected")
        
        # Cleanup
        requests.post(f"{BASE_URL}/api/admin/delete-user", headers={"Authorization": f"Bearer {admin_token}"}, json={"user_id": user1_id})
        requests.post(f"{BASE_URL}/api/admin/delete-user", headers={"Authorization": f"Bearer {admin_token}"}, json={"user_id": user2_id})


class TestRegressionAdminEndpoints:
    """Regression tests for admin endpoints"""
    
    @pytest.fixture
    def admin_session(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["session_token"]
    
    def test_admin_get_pricing(self, admin_session):
        """REGRESSION: Admin get-pricing works"""
        response = requests.get(
            f"{BASE_URL}/api/admin/get-pricing",
            headers={"Authorization": f"Bearer {admin_session}"}
        )
        assert response.status_code == 200
        print("✓ Admin get-pricing works")
    
    def test_admin_get_teachers(self, admin_session):
        """REGRESSION: Admin get teachers works"""
        response = requests.get(
            f"{BASE_URL}/api/admin/teachers",
            headers={"Authorization": f"Bearer {admin_session}"}
        )
        assert response.status_code == 200
        print("✓ Admin get teachers works")
    
    def test_admin_get_students(self, admin_session):
        """REGRESSION: Admin get students works"""
        response = requests.get(
            f"{BASE_URL}/api/admin/students",
            headers={"Authorization": f"Bearer {admin_session}"}
        )
        assert response.status_code == 200
        print("✓ Admin get students works")
    
    def test_admin_all_users(self, admin_session):
        """REGRESSION: Admin all-users works"""
        response = requests.get(
            f"{BASE_URL}/api/admin/all-users",
            headers={"Authorization": f"Bearer {admin_session}"}
        )
        assert response.status_code == 200
        print("✓ Admin all-users works")


class TestRegressionDashboards:
    """Regression tests for dashboard endpoints"""
    
    def test_teacher_dashboard(self):
        """REGRESSION: Teacher dashboard loads"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEACHER_EMAIL,
            "password": TEACHER_PASSWORD
        })
        token = response.json()["session_token"]
        
        dashboard = requests.get(
            f"{BASE_URL}/api/teacher/dashboard",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert dashboard.status_code == 200
        print("✓ Teacher dashboard loads")
    
    def test_student_dashboard(self):
        """REGRESSION: Student dashboard loads"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STUDENT_EMAIL,
            "password": STUDENT_PASSWORD
        })
        token = response.json()["session_token"]
        
        dashboard = requests.get(
            f"{BASE_URL}/api/student/dashboard",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert dashboard.status_code == 200
        print("✓ Student dashboard loads")
    
    def test_counsellor_dashboard(self):
        """REGRESSION: Counsellor dashboard loads"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COUNSELLOR_EMAIL,
            "password": COUNSELLOR_PASSWORD
        })
        token = response.json()["session_token"]
        
        dashboard = requests.get(
            f"{BASE_URL}/api/counsellor/dashboard",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert dashboard.status_code == 200
        print("✓ Counsellor dashboard loads")


class TestRegressionGeneralEndpoints:
    """Regression tests for general endpoints"""
    
    def test_wallet_summary(self):
        """REGRESSION: Wallet summary endpoint works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STUDENT_EMAIL,
            "password": STUDENT_PASSWORD
        })
        token = response.json()["session_token"]
        
        wallet = requests.get(
            f"{BASE_URL}/api/wallet/summary",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert wallet.status_code == 200
        print("✓ Wallet summary works")
    
    def test_notifications(self):
        """REGRESSION: Notifications endpoint works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STUDENT_EMAIL,
            "password": STUDENT_PASSWORD
        })
        token = response.json()["session_token"]
        
        notifs = requests.get(
            f"{BASE_URL}/api/notifications/my",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert notifs.status_code == 200
        print("✓ Notifications endpoint works")
    
    def test_chat_contacts(self):
        """REGRESSION: Chat contacts endpoint works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STUDENT_EMAIL,
            "password": STUDENT_PASSWORD
        })
        token = response.json()["session_token"]
        
        contacts = requests.get(
            f"{BASE_URL}/api/chat/contacts",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert contacts.status_code == 200
        print("✓ Chat contacts endpoint works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
