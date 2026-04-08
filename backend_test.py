#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for Kaimera Learning
Tests all critical flows including payment, booking, and user management
"""

import requests
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Use the public endpoint from frontend .env
BASE_URL = "https://skill-exchange-149.preview.emergentagent.com/api"

class KaimeraAPITester:
    def __init__(self):
        self.base_url = BASE_URL
        self.admin_token = None
        self.student1_token = None
        self.student2_token = None
        self.teacher1_token = None
        self.teacher2_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
        else:
            print(f"❌ {name} - {details}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details
        })

    def make_request(self, method: str, endpoint: str, data: Dict = None, 
                    token: str = None, expected_status: int = 200) -> tuple[bool, Dict]:
        """Make API request and return success status and response data"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if token:
            headers['Authorization'] = f'Bearer {token}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            try:
                response_data = response.json()
            except:
                response_data = {"status_code": response.status_code, "text": response.text}

            return success, response_data

        except Exception as e:
            return False, {"error": str(e)}

    def test_authentication(self):
        """Test authentication endpoints"""
        print("\n🔐 Testing Authentication...")
        
        # Test admin login
        success, data = self.make_request('POST', 'auth/login', {
            'email': 'info@kaimeralearning.com',
            'password': 'solidarity&peace2023'
        })
        
        if success and 'session_token' in data:
            self.admin_token = data['session_token']
            self.log_test("Admin Login", True)
        else:
            self.log_test("Admin Login", False, f"Response: {data}")

        # Test student1 login
        success, data = self.make_request('POST', 'auth/login', {
            'email': 'student1@kaimera.com',
            'password': 'password123'
        })
        
        if success and 'session_token' in data:
            self.student1_token = data['session_token']
            self.log_test("Student1 Login", True)
        else:
            self.log_test("Student1 Login", False, f"Response: {data}")

        # Test student2 login
        success, data = self.make_request('POST', 'auth/login', {
            'email': 'student2@kaimera.com',
            'password': 'password123'
        })
        
        if success and 'session_token' in data:
            self.student2_token = data['session_token']
            self.log_test("Student2 Login", True)
        else:
            self.log_test("Student2 Login", False, f"Response: {data}")

        # Test teacher1 login
        success, data = self.make_request('POST', 'auth/login', {
            'email': 'teacher1@kaimera.com',
            'password': 'password123'
        })
        
        if success and 'session_token' in data:
            self.teacher1_token = data['session_token']
            self.log_test("Teacher1 Login", True)
        else:
            self.log_test("Teacher1 Login", False, f"Response: {data}")

        # Test teacher2 login
        success, data = self.make_request('POST', 'auth/login', {
            'email': 'teacher2@kaimera.com',
            'password': 'password123'
        })
        
        if success and 'session_token' in data:
            self.teacher2_token = data['session_token']
            self.log_test("Teacher2 Login", True)
        else:
            self.log_test("Teacher2 Login", False, f"Response: {data}")

    def test_user_profiles(self):
        """Test user profile endpoints"""
        print("\n👤 Testing User Profiles...")
        
        # Test admin profile
        if self.admin_token:
            success, data = self.make_request('GET', 'auth/me', token=self.admin_token)
            if success and data.get('role') == 'admin':
                self.log_test("Admin Profile", True)
            else:
                self.log_test("Admin Profile", False, f"Response: {data}")

        # Test student profile
        if self.student1_token:
            success, data = self.make_request('GET', 'auth/me', token=self.student1_token)
            if success and data.get('role') == 'student':
                self.log_test("Student Profile", True)
            else:
                self.log_test("Student Profile", False, f"Response: {data}")

    def test_class_management(self):
        """Test class creation and management"""
        print("\n📚 Testing Class Management...")
        
        if not self.teacher1_token:
            self.log_test("Class Creation", False, "No teacher token available")
            return

        # Create a test class
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        class_data = {
            'title': 'Test Math Class',
            'subject': 'Mathematics',
            'class_type': 'group',
            'date': tomorrow,
            'start_time': '14:00',
            'end_time': '15:00',
            'credits_required': 15.0,
            'max_students': 5
        }
        
        success, data = self.make_request('POST', 'classes/create', class_data, 
                                        token=self.teacher1_token, expected_status=200)
        
        if success and 'class' in data:
            self.test_class_id = data['class']['class_id']
            self.log_test("Class Creation", True)
        else:
            self.log_test("Class Creation", False, f"Response: {data}")

        # Test teacher dashboard
        success, data = self.make_request('GET', 'teacher/dashboard', token=self.teacher1_token)
        if success and 'classes' in data:
            self.log_test("Teacher Dashboard", True)
        else:
            self.log_test("Teacher Dashboard", False, f"Response: {data}")

    def test_class_browsing(self):
        """Test class browsing functionality"""
        print("\n🔍 Testing Class Browsing...")
        
        if not self.student1_token:
            self.log_test("Browse Classes", False, "No student token available")
            return

        success, data = self.make_request('GET', 'classes/browse', token=self.student1_token)
        if success and isinstance(data, list):
            self.available_classes = data
            self.log_test("Browse Classes", True)
        else:
            self.log_test("Browse Classes", False, f"Response: {data}")

    def test_student_dashboard(self):
        """Test student dashboard"""
        print("\n📊 Testing Student Dashboard...")
        
        if not self.student1_token:
            self.log_test("Student Dashboard", False, "No student token available")
            return

        success, data = self.make_request('GET', 'student/dashboard', token=self.student1_token)
        if success and 'credits' in data:
            self.student1_credits = data['credits']
            self.log_test("Student Dashboard", True)
        else:
            self.log_test("Student Dashboard", False, f"Response: {data}")

    def test_class_booking(self):
        """Test class booking functionality"""
        print("\n📝 Testing Class Booking...")
        
        if not self.student1_token or not hasattr(self, 'available_classes'):
            self.log_test("Class Booking", False, "Prerequisites not met")
            return

        # Find a bookable class
        bookable_class = None
        for cls in self.available_classes:
            if cls['enrolled_students'].__len__() < cls['max_students']:
                bookable_class = cls
                break

        if not bookable_class:
            self.log_test("Class Booking", False, "No bookable classes available")
            return

        # Test booking
        success, data = self.make_request('POST', 'classes/book', 
                                        {'class_id': bookable_class['class_id']}, 
                                        token=self.student1_token)
        
        if success:
            self.booked_class_id = bookable_class['class_id']
            self.log_test("Class Booking", True)
        else:
            self.log_test("Class Booking", False, f"Response: {data}")

    def test_insufficient_credits_scenario(self):
        """Test booking with insufficient credits"""
        print("\n💳 Testing Insufficient Credits Scenario...")
        
        if not self.student2_token:
            self.log_test("Insufficient Credits Test", False, "No student2 token available")
            return

        # Student2 has only 10 credits, try to book a 15 credit class
        if hasattr(self, 'test_class_id'):
            success, data = self.make_request('POST', 'classes/book', 
                                            {'class_id': self.test_class_id}, 
                                            token=self.student2_token, expected_status=400)
            
            if success and 'Insufficient credits' in data.get('detail', ''):
                self.log_test("Insufficient Credits Test", True)
            else:
                self.log_test("Insufficient Credits Test", False, f"Response: {data}")

    def test_booking_cancellation(self):
        """Test booking cancellation and refund"""
        print("\n❌ Testing Booking Cancellation...")
        
        if not self.student1_token or not hasattr(self, 'booked_class_id'):
            self.log_test("Booking Cancellation", False, "No booking to cancel")
            return

        success, data = self.make_request('POST', f'classes/cancel/{self.booked_class_id}', 
                                        token=self.student1_token)
        
        if success:
            self.log_test("Booking Cancellation", True)
        else:
            self.log_test("Booking Cancellation", False, f"Response: {data}")

    def test_payment_endpoints(self):
        """Test payment-related endpoints"""
        print("\n💰 Testing Payment Endpoints...")
        
        if not self.student1_token:
            self.log_test("Payment Checkout", False, "No student token available")
            return

        # Test checkout creation
        origin_url = "https://skill-exchange-149.preview.emergentagent.com"
        success, data = self.make_request('POST', f'payments/checkout?package_id=small&origin_url={origin_url}', 
                                        token=self.student1_token)
        
        if success and 'url' in data:
            self.checkout_session_id = data.get('session_id')
            self.log_test("Payment Checkout Creation", True)
        else:
            self.log_test("Payment Checkout Creation", False, f"Response: {data}")

    def test_admin_functions(self):
        """Test admin functionality"""
        print("\n👑 Testing Admin Functions...")
        
        if not self.admin_token:
            self.log_test("Admin Functions", False, "No admin token available")
            return

        # Test get all teachers
        success, data = self.make_request('GET', 'admin/teachers', token=self.admin_token)
        if success and isinstance(data, list):
            self.log_test("Admin Get Teachers", True)
        else:
            self.log_test("Admin Get Teachers", False, f"Response: {data}")

        # Test get all classes
        success, data = self.make_request('GET', 'admin/classes', token=self.admin_token)
        if success and isinstance(data, list):
            self.log_test("Admin Get Classes", True)
        else:
            self.log_test("Admin Get Classes", False, f"Response: {data}")

        # Test get transactions
        success, data = self.make_request('GET', 'admin/transactions', token=self.admin_token)
        if success and isinstance(data, list):
            self.log_test("Admin Get Transactions", True)
        else:
            self.log_test("Admin Get Transactions", False, f"Response: {data}")

    def test_teacher_approval(self):
        """Test teacher approval process"""
        print("\n✅ Testing Teacher Approval...")
        
        if not self.admin_token or not self.teacher2_token:
            self.log_test("Teacher Approval", False, "Missing required tokens")
            return

        # Get teacher2 user_id first
        success, teacher_data = self.make_request('GET', 'auth/me', token=self.teacher2_token)
        if not success:
            self.log_test("Teacher Approval", False, "Could not get teacher2 data")
            return

        teacher2_id = teacher_data.get('user_id')
        
        # Approve teacher2
        success, data = self.make_request('POST', 'admin/approve-teacher', 
                                        {'user_id': teacher2_id, 'approved': True}, 
                                        token=self.admin_token)
        
        if success:
            self.log_test("Teacher Approval", True)
        else:
            self.log_test("Teacher Approval", False, f"Response: {data}")

    def run_all_tests(self):
        """Run comprehensive test suite"""
        print("🚀 Starting Kaimera Learning API Tests...")
        print(f"Testing against: {self.base_url}")
        
        # Initialize test data
        self.test_class_id = None
        self.booked_class_id = None
        self.available_classes = []
        self.student1_credits = 0
        self.checkout_session_id = None
        
        # Run tests in order
        self.test_authentication()
        self.test_user_profiles()
        self.test_class_management()
        self.test_class_browsing()
        self.test_student_dashboard()
        self.test_class_booking()
        self.test_insufficient_credits_scenario()
        self.test_booking_cancellation()
        self.test_payment_endpoints()
        self.test_admin_functions()
        self.test_teacher_approval()
        
        # Print summary
        print(f"\n📊 Test Summary:")
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        # Return results for further analysis
        return {
            "total_tests": self.tests_run,
            "passed_tests": self.tests_passed,
            "success_rate": (self.tests_passed/self.tests_run)*100,
            "detailed_results": self.test_results
        }

def main():
    """Main test execution"""
    tester = KaimeraAPITester()
    results = tester.run_all_tests()
    
    # Exit with appropriate code
    if results["success_rate"] < 80:
        print("\n❌ Critical issues found - success rate below 80%")
        return 1
    else:
        print("\n✅ Tests completed successfully")
        return 0

if __name__ == "__main__":
    sys.exit(main())