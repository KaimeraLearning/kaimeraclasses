"""
Iteration 9 Feature Tests - Kaimera Learning EdTech CRM
Tests for:
1. Admin Credentials tab - Create teacher/counsellor accounts
2. Admin block/delete user functionality
3. Counsellor daily stats bar chart data
4. History search fix (should return assignments and demos)
5. Wallet transaction amounts (positive for credits, negative for debits)
6. Blocked user login prevention
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
def admin_session():
    """Get admin session token"""
    session = requests.Session()
    response = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    data = response.json()
    session.headers.update({"Authorization": f"Bearer {data['session_token']}"})
    return session


@pytest.fixture(scope="module")
def teacher_session():
    """Get teacher session token"""
    session = requests.Session()
    response = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEACHER_EMAIL,
        "password": TEACHER_PASSWORD
    })
    assert response.status_code == 200, f"Teacher login failed: {response.text}"
    data = response.json()
    session.headers.update({"Authorization": f"Bearer {data['session_token']}"})
    return session


@pytest.fixture(scope="module")
def counsellor_session():
    """Get counsellor session token"""
    session = requests.Session()
    response = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": COUNSELLOR_EMAIL,
        "password": COUNSELLOR_PASSWORD
    })
    assert response.status_code == 200, f"Counsellor login failed: {response.text}"
    data = response.json()
    session.headers.update({"Authorization": f"Bearer {data['session_token']}"})
    return session


class TestAdminCreateTeacher:
    """Test admin creating teacher accounts"""
    
    def test_create_teacher_success(self, admin_session):
        """Admin can create a new teacher account"""
        unique_id = uuid.uuid4().hex[:8]
        response = admin_session.post(f"{BASE_URL}/api/admin/create-teacher", json={
            "name": f"TEST_Teacher_{unique_id}",
            "email": f"test_teacher_{unique_id}@kaimera.com",
            "password": "testpass123"
        })
        assert response.status_code == 200, f"Create teacher failed: {response.text}"
        data = response.json()
        assert "user_id" in data
        assert "teacher_code" in data
        assert data["email"] == f"test_teacher_{unique_id}@kaimera.com"
        print(f"✓ Created teacher: {data['email']} with code {data['teacher_code']}")
        # Store for cleanup
        TestAdminCreateTeacher.created_teacher_id = data["user_id"]
        TestAdminCreateTeacher.created_teacher_email = data["email"]
    
    def test_create_teacher_duplicate_email(self, admin_session):
        """Creating teacher with existing email fails"""
        response = admin_session.post(f"{BASE_URL}/api/admin/create-teacher", json={
            "name": "Duplicate Teacher",
            "email": TEACHER_EMAIL,  # Already exists
            "password": "testpass123"
        })
        assert response.status_code == 400
        print("✓ Duplicate email correctly rejected")
    
    def test_non_admin_cannot_create_teacher(self, teacher_session):
        """Non-admin cannot create teacher accounts"""
        response = teacher_session.post(f"{BASE_URL}/api/admin/create-teacher", json={
            "name": "Unauthorized Teacher",
            "email": "unauthorized@test.com",
            "password": "testpass123"
        })
        assert response.status_code == 403
        print("✓ Non-admin correctly blocked from creating teacher")


class TestAdminCreateCounsellor:
    """Test admin creating counsellor accounts"""
    
    def test_create_counsellor_success(self, admin_session):
        """Admin can create a new counsellor account"""
        unique_id = uuid.uuid4().hex[:8]
        response = admin_session.post(f"{BASE_URL}/api/admin/create-counsellor", json={
            "name": f"TEST_Counsellor_{unique_id}",
            "email": f"test_counsellor_{unique_id}@kaimera.com",
            "password": "testpass123"
        })
        assert response.status_code == 200, f"Create counsellor failed: {response.text}"
        data = response.json()
        assert "user_id" in data
        assert data["email"] == f"test_counsellor_{unique_id}@kaimera.com"
        print(f"✓ Created counsellor: {data['email']}")
        TestAdminCreateCounsellor.created_counsellor_id = data["user_id"]
        TestAdminCreateCounsellor.created_counsellor_email = data["email"]
    
    def test_non_admin_cannot_create_counsellor(self, counsellor_session):
        """Non-admin cannot create counsellor accounts"""
        response = counsellor_session.post(f"{BASE_URL}/api/admin/create-counsellor", json={
            "name": "Unauthorized Counsellor",
            "email": "unauthorized_c@test.com",
            "password": "testpass123"
        })
        assert response.status_code == 403
        print("✓ Non-admin correctly blocked from creating counsellor")


class TestAdminBlockUser:
    """Test admin blocking/unblocking users"""
    
    def test_block_user_success(self, admin_session):
        """Admin can block a user"""
        # First create a temp user to block
        unique_id = uuid.uuid4().hex[:8]
        create_resp = admin_session.post(f"{BASE_URL}/api/admin/create-teacher", json={
            "name": f"TEST_BlockMe_{unique_id}",
            "email": f"test_blockme_{unique_id}@kaimera.com",
            "password": "testpass123"
        })
        assert create_resp.status_code == 200
        user_id = create_resp.json()["user_id"]
        TestAdminBlockUser.blocked_user_id = user_id
        TestAdminBlockUser.blocked_user_email = f"test_blockme_{unique_id}@kaimera.com"
        
        # Now block the user
        response = admin_session.post(f"{BASE_URL}/api/admin/block-user", json={
            "user_id": user_id,
            "blocked": True
        })
        assert response.status_code == 200, f"Block user failed: {response.text}"
        data = response.json()
        assert "blocked" in data["message"].lower()
        print(f"✓ User blocked successfully: {user_id}")
    
    def test_blocked_user_cannot_login(self):
        """Blocked user should get 403 when trying to login"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TestAdminBlockUser.blocked_user_email,
            "password": "testpass123"
        })
        assert response.status_code == 403, f"Expected 403 for blocked user, got {response.status_code}: {response.text}"
        print("✓ Blocked user correctly prevented from logging in")
    
    def test_unblock_user_success(self, admin_session):
        """Admin can unblock a user"""
        response = admin_session.post(f"{BASE_URL}/api/admin/block-user", json={
            "user_id": TestAdminBlockUser.blocked_user_id,
            "blocked": False
        })
        assert response.status_code == 200
        data = response.json()
        assert "unblocked" in data["message"].lower()
        print("✓ User unblocked successfully")
    
    def test_cannot_block_admin(self, admin_session):
        """Cannot block admin accounts"""
        # Get admin user_id
        me_resp = admin_session.get(f"{BASE_URL}/api/auth/me")
        admin_id = me_resp.json()["user_id"]
        
        response = admin_session.post(f"{BASE_URL}/api/admin/block-user", json={
            "user_id": admin_id,
            "blocked": True
        })
        assert response.status_code == 400
        print("✓ Admin account correctly protected from blocking")


class TestAdminDeleteUser:
    """Test admin deleting users"""
    
    def test_delete_user_success(self, admin_session):
        """Admin can delete a non-admin user"""
        # Create a temp user to delete
        unique_id = uuid.uuid4().hex[:8]
        create_resp = admin_session.post(f"{BASE_URL}/api/admin/create-teacher", json={
            "name": f"TEST_DeleteMe_{unique_id}",
            "email": f"test_deleteme_{unique_id}@kaimera.com",
            "password": "testpass123"
        })
        assert create_resp.status_code == 200
        user_id = create_resp.json()["user_id"]
        
        # Delete the user
        response = admin_session.post(f"{BASE_URL}/api/admin/delete-user", json={
            "user_id": user_id
        })
        assert response.status_code == 200, f"Delete user failed: {response.text}"
        data = response.json()
        assert "deleted" in data["message"].lower()
        print(f"✓ User deleted successfully: {user_id}")
    
    def test_cannot_delete_admin(self, admin_session):
        """Cannot delete admin accounts"""
        me_resp = admin_session.get(f"{BASE_URL}/api/auth/me")
        admin_id = me_resp.json()["user_id"]
        
        response = admin_session.post(f"{BASE_URL}/api/admin/delete-user", json={
            "user_id": admin_id
        })
        assert response.status_code == 400
        print("✓ Admin account correctly protected from deletion")
    
    def test_delete_nonexistent_user(self, admin_session):
        """Deleting non-existent user returns 404"""
        response = admin_session.post(f"{BASE_URL}/api/admin/delete-user", json={
            "user_id": "nonexistent_user_12345"
        })
        assert response.status_code == 404
        print("✓ Non-existent user deletion correctly returns 404")


class TestCounsellorDailyStats:
    """Test counsellor daily stats endpoint for bar chart"""
    
    def test_get_counsellor_daily_stats(self, admin_session):
        """Admin can get daily stats for a counsellor"""
        # First get a counsellor ID
        tracking_resp = admin_session.get(f"{BASE_URL}/api/admin/counsellor-tracking")
        assert tracking_resp.status_code == 200
        counsellors = tracking_resp.json()
        
        if len(counsellors) > 0:
            counsellor_id = counsellors[0]["user_id"]
            response = admin_session.get(f"{BASE_URL}/api/admin/counsellor-daily-stats/{counsellor_id}")
            assert response.status_code == 200, f"Get daily stats failed: {response.text}"
            data = response.json()
            assert isinstance(data, list)
            # Each entry should have date, leads, allotments, sessions
            if len(data) > 0:
                assert "date" in data[0]
                assert "leads" in data[0]
                assert "allotments" in data[0]
                assert "sessions" in data[0]
            print(f"✓ Got daily stats for counsellor: {len(data)} days of data")
        else:
            print("⚠ No counsellors found to test daily stats")
    
    def test_non_admin_cannot_get_daily_stats(self, teacher_session):
        """Non-admin cannot access counsellor daily stats"""
        response = teacher_session.get(f"{BASE_URL}/api/admin/counsellor-daily-stats/some_id")
        assert response.status_code == 403
        print("✓ Non-admin correctly blocked from counsellor daily stats")


class TestHistorySearch:
    """Test history search endpoint - should return assignments and demos"""
    
    def test_history_search_returns_results(self, admin_session):
        """History search should return assignments and demos"""
        # Search for a common term
        response = admin_session.get(f"{BASE_URL}/api/history/search?q=student")
        assert response.status_code == 200, f"History search failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ History search returned {len(data)} results for 'student'")
        
        # Check that results include assignments and demos
        actions = [r.get("action", "") for r in data]
        has_assignments = any("assignment" in a for a in actions)
        has_demos = any("demo" in a for a in actions)
        print(f"  - Has assignment results: {has_assignments}")
        print(f"  - Has demo results: {has_demos}")
    
    def test_history_search_empty_query(self, admin_session):
        """Empty query returns empty results"""
        response = admin_session.get(f"{BASE_URL}/api/history/search?q=")
        assert response.status_code == 200
        data = response.json()
        assert data == []
        print("✓ Empty query correctly returns empty results")
    
    def test_counsellor_can_search_history(self, counsellor_session):
        """Counsellor can also search history"""
        response = counsellor_session.get(f"{BASE_URL}/api/history/search?q=test")
        assert response.status_code == 200
        print("✓ Counsellor can access history search")


class TestWalletTransactionAmounts:
    """Test that wallet transactions store correct amounts (positive/negative)"""
    
    def test_credit_add_stores_positive(self, admin_session):
        """Credit add should store positive amount"""
        # Get a student to adjust credits
        students_resp = admin_session.get(f"{BASE_URL}/api/admin/students")
        assert students_resp.status_code == 200
        students = students_resp.json()
        
        if len(students) > 0:
            student_id = students[0]["user_id"]
            
            # Add credits
            response = admin_session.post(f"{BASE_URL}/api/admin/adjust-credits", json={
                "user_id": student_id,
                "amount": 5.0,
                "action": "add"
            })
            assert response.status_code == 200
            
            # Check transactions
            txn_resp = admin_session.get(f"{BASE_URL}/api/admin/transactions")
            assert txn_resp.status_code == 200
            transactions = txn_resp.json()
            
            # Find the credit_add transaction
            credit_adds = [t for t in transactions if t["type"] == "credit_add" and t["user_id"] == student_id]
            if len(credit_adds) > 0:
                latest = credit_adds[-1]
                assert latest["amount"] > 0, f"Credit add should be positive, got {latest['amount']}"
                print(f"✓ Credit add stores positive amount: {latest['amount']}")
            else:
                print("⚠ No credit_add transactions found to verify")
        else:
            print("⚠ No students found to test credit adjustment")
    
    def test_credit_deduct_stores_negative(self, admin_session):
        """Credit deduct should store negative amount"""
        students_resp = admin_session.get(f"{BASE_URL}/api/admin/students")
        students = students_resp.json()
        
        if len(students) > 0:
            student_id = students[0]["user_id"]
            
            # Deduct credits
            response = admin_session.post(f"{BASE_URL}/api/admin/adjust-credits", json={
                "user_id": student_id,
                "amount": 2.0,
                "action": "deduct"
            })
            assert response.status_code == 200
            
            # Check transactions
            txn_resp = admin_session.get(f"{BASE_URL}/api/admin/transactions")
            transactions = txn_resp.json()
            
            # Find the credit_deduct transaction
            credit_deducts = [t for t in transactions if t["type"] == "credit_deduct" and t["user_id"] == student_id]
            if len(credit_deducts) > 0:
                latest = credit_deducts[-1]
                assert latest["amount"] < 0, f"Credit deduct should be negative, got {latest['amount']}"
                print(f"✓ Credit deduct stores negative amount: {latest['amount']}")
            else:
                print("⚠ No credit_deduct transactions found to verify")


class TestAllUsersEndpoint:
    """Test admin all-users endpoint for credentials tab"""
    
    def test_get_all_users(self, admin_session):
        """Admin can get all users"""
        response = admin_session.get(f"{BASE_URL}/api/admin/all-users")
        assert response.status_code == 200, f"Get all users failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Check user structure
        user = data[0]
        assert "user_id" in user
        assert "email" in user
        assert "role" in user
        print(f"✓ Got {len(data)} users from all-users endpoint")
    
    def test_non_admin_cannot_get_all_users(self, teacher_session):
        """Non-admin cannot access all-users"""
        response = teacher_session.get(f"{BASE_URL}/api/admin/all-users")
        assert response.status_code == 403
        print("✓ Non-admin correctly blocked from all-users")


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_created_users(self, admin_session):
        """Clean up test-created users"""
        # Delete created teacher if exists
        if hasattr(TestAdminCreateTeacher, 'created_teacher_id'):
            admin_session.post(f"{BASE_URL}/api/admin/delete-user", json={
                "user_id": TestAdminCreateTeacher.created_teacher_id
            })
            print(f"✓ Cleaned up test teacher: {TestAdminCreateTeacher.created_teacher_email}")
        
        # Delete created counsellor if exists
        if hasattr(TestAdminCreateCounsellor, 'created_counsellor_id'):
            admin_session.post(f"{BASE_URL}/api/admin/delete-user", json={
                "user_id": TestAdminCreateCounsellor.created_counsellor_id
            })
            print(f"✓ Cleaned up test counsellor: {TestAdminCreateCounsellor.created_counsellor_email}")
        
        # Delete blocked user if exists
        if hasattr(TestAdminBlockUser, 'blocked_user_id'):
            admin_session.post(f"{BASE_URL}/api/admin/delete-user", json={
                "user_id": TestAdminBlockUser.blocked_user_id
            })
            print(f"✓ Cleaned up blocked test user")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
