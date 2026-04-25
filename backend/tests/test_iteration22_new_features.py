"""
Iteration 22 - Testing New Features:
1. Learning Plans CRUD (admin)
2. Razorpay Payment Integration
3. Attendance System
4. Proof Guardrail (blocks assignment if proof pending)
5. @gmail.com validation on user creation
6. OTP verification for manually created users
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "info@kaimeralearning.com"
ADMIN_PASSWORD = "solidarity&peace2023"


class TestAdminAuth:
    """Admin authentication tests"""
    
    def test_admin_login_success(self):
        """Admin login with correct credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "session_token" in data, "No session token returned"
        assert data["user"]["role"] == "admin", "User is not admin"
        assert data["user"]["email"] == ADMIN_EMAIL
        print(f"✓ Admin login successful: {data['user']['name']}")
        return data["session_token"]
    
    def test_admin_login_wrong_password(self):
        """Admin login with wrong password should fail"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": "wrongpassword"
        })
        assert response.status_code == 401, "Should return 401 for wrong password"
        print("✓ Wrong password correctly rejected")


class TestLearningPlansCRUD:
    """Learning Plans CRUD operations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin token for authenticated requests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        self.token = response.json()["session_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_create_learning_plan(self):
        """Create a new learning plan"""
        plan_data = {
            "name": f"TEST_Plan_{uuid.uuid4().hex[:6]}",
            "price": 5000.0,
            "details": "Test learning plan with 10 sessions covering basic concepts"
        }
        response = requests.post(
            f"{BASE_URL}/api/admin/learning-plans",
            json=plan_data,
            headers=self.headers
        )
        assert response.status_code == 200, f"Create plan failed: {response.text}"
        data = response.json()
        assert "plan_id" in data, "No plan_id returned"
        assert data["message"] == "Learning plan created"
        print(f"✓ Learning plan created: {data['plan_id']}")
        return data["plan_id"]
    
    def test_list_learning_plans(self):
        """List all active learning plans"""
        response = requests.get(
            f"{BASE_URL}/api/admin/learning-plans",
            headers=self.headers
        )
        assert response.status_code == 200, f"List plans failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Listed {len(data)} learning plans")
        return data
    
    def test_create_and_update_learning_plan(self):
        """Create then update a learning plan"""
        # Create
        plan_data = {
            "name": f"TEST_UpdatePlan_{uuid.uuid4().hex[:6]}",
            "price": 3000.0,
            "details": "Original details"
        }
        create_res = requests.post(
            f"{BASE_URL}/api/admin/learning-plans",
            json=plan_data,
            headers=self.headers
        )
        assert create_res.status_code == 200
        plan_id = create_res.json()["plan_id"]
        
        # Update
        update_data = {
            "name": plan_data["name"] + "_Updated",
            "price": 4000.0,
            "details": "Updated details with more content"
        }
        update_res = requests.put(
            f"{BASE_URL}/api/admin/learning-plans/{plan_id}",
            json=update_data,
            headers=self.headers
        )
        assert update_res.status_code == 200, f"Update failed: {update_res.text}"
        assert update_res.json()["message"] == "Learning plan updated"
        print(f"✓ Learning plan updated: {plan_id}")
    
    def test_delete_learning_plan(self):
        """Create then delete (deactivate) a learning plan"""
        # Create
        plan_data = {
            "name": f"TEST_DeletePlan_{uuid.uuid4().hex[:6]}",
            "price": 2000.0,
            "details": "Plan to be deleted"
        }
        create_res = requests.post(
            f"{BASE_URL}/api/admin/learning-plans",
            json=plan_data,
            headers=self.headers
        )
        assert create_res.status_code == 200
        plan_id = create_res.json()["plan_id"]
        
        # Delete
        delete_res = requests.delete(
            f"{BASE_URL}/api/admin/learning-plans/{plan_id}",
            headers=self.headers
        )
        assert delete_res.status_code == 200, f"Delete failed: {delete_res.text}"
        assert delete_res.json()["message"] == "Learning plan deactivated"
        print(f"✓ Learning plan deactivated: {plan_id}")


class TestGmailValidation:
    """@gmail.com validation on user creation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        self.token = response.json()["session_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_create_user_non_gmail_rejected(self):
        """Creating user with non-gmail email should be rejected"""
        user_data = {
            "name": "Test User",
            "email": "test@yahoo.com",
            "password": "password123",
            "role": "student"
        }
        response = requests.post(
            f"{BASE_URL}/api/admin/create-user",
            json=user_data,
            headers=self.headers
        )
        assert response.status_code == 400, f"Should reject non-gmail: {response.text}"
        data = response.json()
        assert "gmail.com" in data["detail"].lower(), f"Error should mention gmail: {data['detail']}"
        print(f"✓ Non-gmail email correctly rejected: {data['detail']}")
    
    def test_create_teacher_non_gmail_rejected(self):
        """Creating teacher with non-gmail email should be rejected"""
        teacher_data = {
            "name": "Test Teacher",
            "email": "teacher@outlook.com",
            "password": "password123"
        }
        response = requests.post(
            f"{BASE_URL}/api/admin/create-teacher",
            json=teacher_data,
            headers=self.headers
        )
        assert response.status_code == 400, f"Should reject non-gmail: {response.text}"
        data = response.json()
        assert "gmail.com" in data["detail"].lower()
        print(f"✓ Non-gmail teacher email correctly rejected")
    
    def test_create_student_non_gmail_rejected(self):
        """Creating student with non-gmail email should be rejected"""
        student_data = {
            "name": "Test Student",
            "email": "student@hotmail.com",
            "password": "password123"
        }
        response = requests.post(
            f"{BASE_URL}/api/admin/create-student",
            json=student_data,
            headers=self.headers
        )
        assert response.status_code == 400, f"Should reject non-gmail: {response.text}"
        data = response.json()
        assert "gmail.com" in data["detail"].lower()
        print(f"✓ Non-gmail student email correctly rejected")
    
    def test_create_user_gmail_accepted(self):
        """Creating user with @gmail.com email should work (sends OTP)"""
        unique_email = f"test_{uuid.uuid4().hex[:8]}@gmail.com"
        user_data = {
            "name": "Test Gmail User",
            "email": unique_email,
            "password": "password123",
            "role": "student"
        }
        response = requests.post(
            f"{BASE_URL}/api/admin/create-user",
            json=user_data,
            headers=self.headers
        )
        assert response.status_code == 200, f"Gmail user creation failed: {response.text}"
        data = response.json()
        assert "user_id" in data, "No user_id returned"
        assert "OTP" in data["message"] or "created" in data["message"].lower()
        print(f"✓ Gmail user created: {data['user_id']}")


class TestOTPVerification:
    """OTP verification for self-signup"""
    
    def test_send_otp_non_gmail_rejected(self):
        """Sending OTP to non-gmail should be rejected"""
        response = requests.post(
            f"{BASE_URL}/api/auth/send-otp",
            json={"email": "test@yahoo.com"}
        )
        assert response.status_code == 400, f"Should reject non-gmail: {response.text}"
        data = response.json()
        assert "gmail.com" in data["detail"].lower()
        print(f"✓ OTP to non-gmail correctly rejected")
    
    def test_send_otp_gmail_accepted(self):
        """Sending OTP to gmail should work"""
        unique_email = f"test_{uuid.uuid4().hex[:8]}@gmail.com"
        response = requests.post(
            f"{BASE_URL}/api/auth/send-otp",
            json={"email": unique_email}
        )
        assert response.status_code == 200, f"OTP send failed: {response.text}"
        data = response.json()
        assert "sent" in data["message"].lower() or "otp" in data["message"].lower()
        print(f"✓ OTP sent to gmail: {unique_email}")
    
    def test_verify_otp_invalid(self):
        """Verifying with invalid OTP should fail"""
        response = requests.post(
            f"{BASE_URL}/api/auth/verify-otp",
            json={"email": "test@gmail.com", "otp": "000000"}
        )
        assert response.status_code == 400, f"Should reject invalid OTP: {response.text}"
        print(f"✓ Invalid OTP correctly rejected")


class TestAttendanceSystem:
    """Attendance marking and history"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        self.admin_token = response.json()["session_token"]
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
    
    def test_attendance_mark_requires_teacher(self):
        """Marking attendance requires teacher role"""
        response = requests.post(
            f"{BASE_URL}/api/attendance/mark",
            json={"student_id": "test", "date": "2026-01-15", "status": "present"},
            headers=self.admin_headers
        )
        # Admin should not be able to mark attendance (teacher only)
        assert response.status_code == 403, f"Should require teacher role: {response.text}"
        print(f"✓ Attendance marking correctly requires teacher role")
    
    def test_attendance_student_endpoint_requires_student(self):
        """Student attendance history requires student role"""
        response = requests.get(
            f"{BASE_URL}/api/attendance/student",
            headers=self.admin_headers
        )
        # Admin should not access student attendance endpoint
        assert response.status_code == 403, f"Should require student role: {response.text}"
        print(f"✓ Student attendance endpoint correctly requires student role")
    
    def test_attendance_teacher_endpoint_requires_teacher(self):
        """Teacher attendance history requires teacher role"""
        response = requests.get(
            f"{BASE_URL}/api/attendance/teacher",
            headers=self.admin_headers
        )
        # Admin should not access teacher attendance endpoint
        assert response.status_code == 403, f"Should require teacher role: {response.text}"
        print(f"✓ Teacher attendance endpoint correctly requires teacher role")


class TestRazorpayPayments:
    """Razorpay payment integration"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        self.admin_token = response.json()["session_token"]
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
    
    def test_admin_payments_endpoint(self):
        """Admin can view all payments"""
        response = requests.get(
            f"{BASE_URL}/api/admin/payments",
            headers=self.admin_headers
        )
        assert response.status_code == 200, f"Admin payments failed: {response.text}"
        data = response.json()
        assert "payments" in data, "Response should have payments array"
        assert "total_revenue" in data, "Response should have total_revenue"
        print(f"✓ Admin payments endpoint working: {len(data['payments'])} payments, ₹{data['total_revenue']} revenue")
    
    def test_admin_payments_with_filters(self):
        """Admin can filter payments by student name and date"""
        response = requests.get(
            f"{BASE_URL}/api/admin/payments?student_name=test&date_from=2026-01-01&date_to=2026-12-31",
            headers=self.admin_headers
        )
        assert response.status_code == 200, f"Filtered payments failed: {response.text}"
        data = response.json()
        assert "payments" in data
        print(f"✓ Admin payments filtering working")
    
    def test_create_order_requires_assignment(self):
        """Creating payment order requires valid assignment_id"""
        response = requests.post(
            f"{BASE_URL}/api/payments/create-order",
            json={"assignment_id": "invalid_assignment"},
            headers=self.admin_headers
        )
        # Should fail because assignment doesn't exist
        assert response.status_code == 404, f"Should return 404 for invalid assignment: {response.text}"
        print(f"✓ Payment order creation correctly validates assignment")


class TestProofGuardrail:
    """Proof guardrail - blocks assignment if previous proof pending"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        self.admin_token = response.json()["session_token"]
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
    
    def test_assign_student_endpoint_exists(self):
        """Assign student endpoint exists and requires valid data"""
        response = requests.post(
            f"{BASE_URL}/api/admin/assign-student",
            json={
                "student_id": "invalid_student",
                "teacher_id": "invalid_teacher"
            },
            headers=self.admin_headers
        )
        # Should fail because student/teacher don't exist
        assert response.status_code == 404, f"Should return 404 for invalid IDs: {response.text}"
        print(f"✓ Assign student endpoint validates student/teacher existence")


class TestAdminDashboardEndpoints:
    """Admin dashboard data endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        self.admin_token = response.json()["session_token"]
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
    
    def test_admin_all_users(self):
        """Admin can list all users"""
        response = requests.get(
            f"{BASE_URL}/api/admin/all-users",
            headers=self.admin_headers
        )
        assert response.status_code == 200, f"All users failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Admin all-users: {len(data)} users")
    
    def test_admin_teachers(self):
        """Admin can list all teachers"""
        response = requests.get(
            f"{BASE_URL}/api/admin/teachers",
            headers=self.admin_headers
        )
        assert response.status_code == 200, f"Teachers list failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Admin teachers: {len(data)} teachers")
    
    def test_admin_students(self):
        """Admin can list all students"""
        response = requests.get(
            f"{BASE_URL}/api/admin/students",
            headers=self.admin_headers
        )
        assert response.status_code == 200, f"Students list failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Admin students: {len(data)} students")
    
    def test_admin_transactions(self):
        """Admin can view transactions"""
        response = requests.get(
            f"{BASE_URL}/api/admin/transactions",
            headers=self.admin_headers
        )
        assert response.status_code == 200, f"Transactions failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Admin transactions: {len(data)} transactions")
    
    def test_admin_transactions_daily_view(self):
        """Admin can view daily transaction summary"""
        response = requests.get(
            f"{BASE_URL}/api/admin/transactions?view=daily",
            headers=self.admin_headers
        )
        assert response.status_code == 200, f"Daily transactions failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Admin daily transactions: {len(data)} days")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
