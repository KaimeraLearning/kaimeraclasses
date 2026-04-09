"""
Iteration 10 Tests: Operations Center Refactoring
Tests for:
- Admin login and Operations Center access
- Unified /admin/create-user endpoint (student, teacher, counsellor)
- Transaction filtering with daily revenue view
- OTP send/verify endpoints
- Role-based login (teacher, student, counsellor)
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAdminLogin:
    """Test admin login and session"""
    
    def test_admin_login_success(self):
        """Admin can login with correct credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "info@kaimeralearning.com",
            "password": "solidarity&peace2023"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "user" in data
        assert data["user"]["role"] == "admin"
        assert "session_token" in data
        print(f"✓ Admin login successful: {data['user']['name']}")
    
    def test_admin_login_wrong_password(self):
        """Admin login fails with wrong password"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "info@kaimeralearning.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("✓ Admin login correctly rejected with wrong password")


class TestUnifiedCreateUser:
    """Test the unified /admin/create-user endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin before each test"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "info@kaimeralearning.com",
            "password": "solidarity&peace2023"
        })
        assert response.status_code == 200
        self.cookies = response.cookies
        self.session_token = response.json().get("session_token")
        yield
        # Cleanup will be done in individual tests
    
    def test_create_teacher_via_unified_endpoint(self):
        """Admin creates teacher via unified endpoint"""
        unique_email = f"TEST_teacher_{int(time.time())}@test.com"
        response = requests.post(
            f"{BASE_URL}/api/admin/create-user",
            json={
                "role": "teacher",
                "name": "Test Teacher Unified",
                "email": unique_email,
                "password": "testpass123"
            },
            cookies=self.cookies
        )
        assert response.status_code == 200, f"Create teacher failed: {response.text}"
        data = response.json()
        assert "credentials" in data
        assert data["credentials"]["email"] == unique_email.lower()
        assert "code" in data["credentials"]  # teacher_code
        assert data["credentials"]["code"].startswith("KL-T")
        print(f"✓ Teacher created via unified endpoint: {data['credentials']['code']}")
        
        # Cleanup
        cleanup = requests.post(
            f"{BASE_URL}/api/admin/delete-user",
            json={"user_id": data["user_id"]},
            cookies=self.cookies
        )
        assert cleanup.status_code == 200
        print("✓ Test teacher cleaned up")
    
    def test_create_student_via_unified_endpoint(self):
        """Admin creates student via unified endpoint with student-specific fields"""
        unique_email = f"TEST_student_{int(time.time())}@test.com"
        response = requests.post(
            f"{BASE_URL}/api/admin/create-user",
            json={
                "role": "student",
                "name": "Test Student Unified",
                "email": unique_email,
                "password": "testpass123",
                "grade": "10",
                "city": "Mumbai",
                "state": "Maharashtra",
                "institute": "Test School"
            },
            cookies=self.cookies
        )
        assert response.status_code == 200, f"Create student failed: {response.text}"
        data = response.json()
        assert "credentials" in data
        assert data["credentials"]["email"] == unique_email.lower()
        assert "code" in data["credentials"]  # student_code
        assert data["credentials"]["code"].startswith("KL-S")
        print(f"✓ Student created via unified endpoint: {data['credentials']['code']}")
        
        # Cleanup
        cleanup = requests.post(
            f"{BASE_URL}/api/admin/delete-user",
            json={"user_id": data["user_id"]},
            cookies=self.cookies
        )
        assert cleanup.status_code == 200
        print("✓ Test student cleaned up")
    
    def test_create_counsellor_via_unified_endpoint(self):
        """Admin creates counsellor via unified endpoint"""
        unique_email = f"TEST_counsellor_{int(time.time())}@test.com"
        response = requests.post(
            f"{BASE_URL}/api/admin/create-user",
            json={
                "role": "counsellor",
                "name": "Test Counsellor Unified",
                "email": unique_email,
                "password": "testpass123"
            },
            cookies=self.cookies
        )
        assert response.status_code == 200, f"Create counsellor failed: {response.text}"
        data = response.json()
        assert "credentials" in data
        assert data["credentials"]["email"] == unique_email.lower()
        # Counsellors don't have a code
        print(f"✓ Counsellor created via unified endpoint")
        
        # Cleanup
        cleanup = requests.post(
            f"{BASE_URL}/api/admin/delete-user",
            json={"user_id": data["user_id"]},
            cookies=self.cookies
        )
        assert cleanup.status_code == 200
        print("✓ Test counsellor cleaned up")
    
    def test_create_user_duplicate_email_fails(self):
        """Creating user with existing email fails"""
        response = requests.post(
            f"{BASE_URL}/api/admin/create-user",
            json={
                "role": "student",
                "name": "Duplicate Test",
                "email": "info@kaimeralearning.com",  # Admin email
                "password": "testpass123"
            },
            cookies=self.cookies
        )
        assert response.status_code == 400
        assert "already registered" in response.json().get("detail", "").lower()
        print("✓ Duplicate email correctly rejected")
    
    def test_create_user_invalid_role_fails(self):
        """Creating user with invalid role fails"""
        response = requests.post(
            f"{BASE_URL}/api/admin/create-user",
            json={
                "role": "superadmin",  # Invalid role
                "name": "Invalid Role Test",
                "email": f"TEST_invalid_{int(time.time())}@test.com",
                "password": "testpass123"
            },
            cookies=self.cookies
        )
        assert response.status_code == 400
        print("✓ Invalid role correctly rejected")


class TestTransactionFiltering:
    """Test transaction filtering with daily revenue view"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "info@kaimeralearning.com",
            "password": "solidarity&peace2023"
        })
        assert response.status_code == 200
        self.cookies = response.cookies
    
    def test_get_transactions_default(self):
        """Get all transactions (default view)"""
        response = requests.get(
            f"{BASE_URL}/api/admin/transactions",
            cookies=self.cookies
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} transactions (default view)")
    
    def test_get_transactions_daily_view(self):
        """Get transactions with daily revenue aggregation"""
        response = requests.get(
            f"{BASE_URL}/api/admin/transactions?view=daily",
            cookies=self.cookies
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            # Check daily aggregation structure
            first_day = data[0]
            assert "date" in first_day
            assert "total_revenue" in first_day
            assert "total_credits_added" in first_day
            assert "total_deductions" in first_day
            assert "count" in first_day
            print(f"✓ Daily view returns {len(data)} days with correct structure")
        else:
            print("✓ Daily view returns empty list (no transactions)")
    
    def test_get_transactions_filter_by_role(self):
        """Filter transactions by role"""
        response = requests.get(
            f"{BASE_URL}/api/admin/transactions?role=teacher",
            cookies=self.cookies
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # All returned transactions should be from teachers
        for txn in data:
            if "user_role" in txn:
                assert txn["user_role"] == "teacher", f"Expected teacher, got {txn['user_role']}"
        print(f"✓ Role filter returns {len(data)} teacher transactions")
    
    def test_get_transactions_filter_by_date_range(self):
        """Filter transactions by date range"""
        response = requests.get(
            f"{BASE_URL}/api/admin/transactions?date_from=2026-01-01&date_to=2026-12-31",
            cookies=self.cookies
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Date range filter returns {len(data)} transactions")


class TestOTPEndpoints:
    """Test OTP send and verify endpoints"""
    
    def test_send_otp_success(self):
        """Send OTP to new email"""
        unique_email = f"TEST_otp_{int(time.time())}@test.com"
        response = requests.post(
            f"{BASE_URL}/api/auth/send-otp",
            json={"email": unique_email}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "otp" in data["message"].lower() or "sent" in data["message"].lower()
        print(f"✓ OTP sent to {unique_email}")
    
    def test_send_otp_existing_email_fails(self):
        """Send OTP to existing email fails"""
        response = requests.post(
            f"{BASE_URL}/api/auth/send-otp",
            json={"email": "info@kaimeralearning.com"}  # Admin email
        )
        assert response.status_code == 400
        assert "already registered" in response.json().get("detail", "").lower()
        print("✓ OTP correctly rejected for existing email")
    
    def test_verify_otp_invalid_code(self):
        """Verify OTP with invalid code fails"""
        response = requests.post(
            f"{BASE_URL}/api/auth/verify-otp",
            json={
                "email": "nonexistent@test.com",
                "otp": "000000"
            }
        )
        assert response.status_code == 400
        print("✓ Invalid OTP correctly rejected")


class TestRoleBasedLogin:
    """Test login for different roles"""
    
    def test_teacher_login(self):
        """Teacher can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "teacher1@kaimera.com",
            "password": "password123"
        })
        assert response.status_code == 200, f"Teacher login failed: {response.text}"
        data = response.json()
        assert data["user"]["role"] == "teacher"
        print(f"✓ Teacher login successful: {data['user']['name']}")
    
    def test_student_login(self):
        """Student can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "student1@kaimera.com",
            "password": "password123"
        })
        assert response.status_code == 200, f"Student login failed: {response.text}"
        data = response.json()
        assert data["user"]["role"] == "student"
        print(f"✓ Student login successful: {data['user']['name']}")
    
    def test_counsellor_login(self):
        """Counsellor can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "counsellor1@kaimera.com",
            "password": "password123"
        })
        assert response.status_code == 200, f"Counsellor login failed: {response.text}"
        data = response.json()
        assert data["user"]["role"] == "counsellor"
        print(f"✓ Counsellor login successful: {data['user']['name']}")


class TestAdminEndpointsAccess:
    """Test admin-only endpoints are protected"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as teacher (non-admin)"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "teacher1@kaimera.com",
            "password": "password123"
        })
        assert response.status_code == 200
        self.teacher_cookies = response.cookies
    
    def test_create_user_non_admin_fails(self):
        """Non-admin cannot access create-user endpoint"""
        response = requests.post(
            f"{BASE_URL}/api/admin/create-user",
            json={
                "role": "student",
                "name": "Unauthorized Test",
                "email": f"TEST_unauth_{int(time.time())}@test.com",
                "password": "testpass123"
            },
            cookies=self.teacher_cookies
        )
        assert response.status_code == 403
        print("✓ Non-admin correctly blocked from create-user")
    
    def test_transactions_non_admin_fails(self):
        """Non-admin cannot access transactions endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/admin/transactions",
            cookies=self.teacher_cookies
        )
        assert response.status_code == 403
        print("✓ Non-admin correctly blocked from transactions")


class TestAllUsersEndpoint:
    """Test /admin/all-users endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "info@kaimeralearning.com",
            "password": "solidarity&peace2023"
        })
        assert response.status_code == 200
        self.cookies = response.cookies
    
    def test_get_all_users(self):
        """Admin can get all users"""
        response = requests.get(
            f"{BASE_URL}/api/admin/all-users",
            cookies=self.cookies
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Check user structure
        user = data[0]
        assert "user_id" in user
        assert "email" in user
        assert "name" in user
        assert "role" in user
        print(f"✓ Got {len(data)} users from all-users endpoint")


class TestCounsellorTracking:
    """Test counsellor tracking endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "info@kaimeralearning.com",
            "password": "solidarity&peace2023"
        })
        assert response.status_code == 200
        self.cookies = response.cookies
    
    def test_get_counsellor_tracking(self):
        """Admin can get counsellor tracking data"""
        response = requests.get(
            f"{BASE_URL}/api/admin/counsellor-tracking",
            cookies=self.cookies
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} counsellors in tracking")


class TestClassesEndpoint:
    """Test /admin/classes endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "info@kaimeralearning.com",
            "password": "solidarity&peace2023"
        })
        assert response.status_code == 200
        self.cookies = response.cookies
    
    def test_get_all_classes(self):
        """Admin can get all classes"""
        response = requests.get(
            f"{BASE_URL}/api/admin/classes",
            cookies=self.cookies
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} classes from admin endpoint")


class TestComplaintsEndpoint:
    """Test /admin/complaints endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "info@kaimeralearning.com",
            "password": "solidarity&peace2023"
        })
        assert response.status_code == 200
        self.cookies = response.cookies
    
    def test_get_all_complaints(self):
        """Admin can get all complaints"""
        response = requests.get(
            f"{BASE_URL}/api/admin/complaints",
            cookies=self.cookies
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} complaints from admin endpoint")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
