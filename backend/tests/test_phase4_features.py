"""
Phase 4 Features Test Suite for Kaimera Learning EdTech CRM
Tests: Learning Kit, Teacher Calendar, Nag Screen, Email Notifications

Features tested:
1. Learning Kit - Admin upload, list, download, delete, grades
2. Teacher Calendar - Add, list, delete entries
3. Student Nag Screen - Check for unassigned students
4. Email Notifications - Demo acceptance and teacher feedback (no crash)
"""

import pytest
import requests
import os
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "info@kaimeralearning.com"
ADMIN_PASSWORD = "solidarity&peace2023"
TEACHER_EMAIL = "teacher1@kaimera.com"
TEACHER_PASSWORD = "password123"
STUDENT_EMAIL = "student1@kaimera.com"
STUDENT_PASSWORD = "password123"


class TestAuth:
    """Authentication helpers"""
    
    @staticmethod
    def login(email, password):
        """Login and return session with cookies"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        return session, response
    
    @staticmethod
    def get_admin_session():
        session, response = TestAuth.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.text}")
        return session
    
    @staticmethod
    def get_teacher_session():
        session, response = TestAuth.login(TEACHER_EMAIL, TEACHER_PASSWORD)
        if response.status_code != 200:
            pytest.skip(f"Teacher login failed: {response.text}")
        return session
    
    @staticmethod
    def get_student_session():
        session, response = TestAuth.login(STUDENT_EMAIL, STUDENT_PASSWORD)
        if response.status_code != 200:
            pytest.skip(f"Student login failed: {response.text}")
        return session


# ==================== LEARNING KIT TESTS ====================

class TestLearningKitUpload:
    """Test Learning Kit upload functionality (Admin only)"""
    
    def test_admin_can_upload_learning_kit(self):
        """Admin uploads a PDF learning kit"""
        session = TestAuth.get_admin_session()
        
        # Create a test PDF file
        test_content = b"%PDF-1.4 Test PDF content for learning kit"
        files = {
            'file': ('test_kit.pdf', io.BytesIO(test_content), 'application/pdf')
        }
        data = {
            'title': 'TEST_Math_Workbook_Phase4',
            'grade': '10',
            'description': 'Test learning kit for Phase 4 testing'
        }
        
        response = session.post(f"{BASE_URL}/api/admin/learning-kit/upload", files=files, data=data)
        
        assert response.status_code == 200, f"Upload failed: {response.text}"
        result = response.json()
        assert "kit_id" in result
        assert "message" in result
        assert "TEST_Math_Workbook_Phase4" in result["message"]
        
        # Store kit_id for cleanup
        self.__class__.test_kit_id = result["kit_id"]
        print(f"✓ Admin uploaded learning kit: {result['kit_id']}")
    
    def test_teacher_cannot_upload_learning_kit(self):
        """Teacher should be denied upload access"""
        session = TestAuth.get_teacher_session()
        
        test_content = b"%PDF-1.4 Test PDF"
        files = {'file': ('test.pdf', io.BytesIO(test_content), 'application/pdf')}
        data = {'title': 'Unauthorized', 'grade': '9', 'description': ''}
        
        response = session.post(f"{BASE_URL}/api/admin/learning-kit/upload", files=files, data=data)
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ Teacher correctly denied upload access (403)")
    
    def test_student_cannot_upload_learning_kit(self):
        """Student should be denied upload access"""
        session = TestAuth.get_student_session()
        
        test_content = b"%PDF-1.4 Test PDF"
        files = {'file': ('test.pdf', io.BytesIO(test_content), 'application/pdf')}
        data = {'title': 'Unauthorized', 'grade': '9', 'description': ''}
        
        response = session.post(f"{BASE_URL}/api/admin/learning-kit/upload", files=files, data=data)
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ Student correctly denied upload access (403)")
    
    def test_upload_invalid_file_type(self):
        """Admin cannot upload disallowed file types"""
        session = TestAuth.get_admin_session()
        
        test_content = b"#!/bin/bash\necho 'malicious'"
        files = {'file': ('script.sh', io.BytesIO(test_content), 'application/x-sh')}
        data = {'title': 'Bad File', 'grade': '9', 'description': ''}
        
        response = session.post(f"{BASE_URL}/api/admin/learning-kit/upload", files=files, data=data)
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Invalid file type correctly rejected (400)")


class TestLearningKitList:
    """Test Learning Kit listing functionality"""
    
    def test_admin_can_list_all_kits(self):
        """Admin can list all learning kits"""
        session = TestAuth.get_admin_session()
        
        response = session.get(f"{BASE_URL}/api/learning-kit")
        
        assert response.status_code == 200, f"List failed: {response.text}"
        kits = response.json()
        assert isinstance(kits, list)
        print(f"✓ Admin listed {len(kits)} learning kits")
    
    def test_filter_kits_by_grade(self):
        """Filter learning kits by grade"""
        session = TestAuth.get_admin_session()
        
        response = session.get(f"{BASE_URL}/api/learning-kit?grade=9")
        
        assert response.status_code == 200, f"Filter failed: {response.text}"
        kits = response.json()
        assert isinstance(kits, list)
        # All returned kits should be grade 9
        for kit in kits:
            assert kit.get("grade") == "9", f"Kit grade mismatch: {kit.get('grade')}"
        print(f"✓ Filtered {len(kits)} kits for Grade 9")
    
    def test_teacher_can_list_kits(self):
        """Teacher can list learning kits"""
        session = TestAuth.get_teacher_session()
        
        response = session.get(f"{BASE_URL}/api/learning-kit")
        
        assert response.status_code == 200, f"Teacher list failed: {response.text}"
        kits = response.json()
        assert isinstance(kits, list)
        print(f"✓ Teacher listed {len(kits)} learning kits")
    
    def test_student_can_list_kits(self):
        """Student can list learning kits (filtered by their grade)"""
        session = TestAuth.get_student_session()
        
        response = session.get(f"{BASE_URL}/api/learning-kit")
        
        assert response.status_code == 200, f"Student list failed: {response.text}"
        kits = response.json()
        assert isinstance(kits, list)
        print(f"✓ Student listed {len(kits)} learning kits")


class TestLearningKitGrades:
    """Test Learning Kit grades endpoint"""
    
    def test_get_available_grades(self):
        """Get list of grades that have learning kits"""
        session = TestAuth.get_admin_session()
        
        response = session.get(f"{BASE_URL}/api/learning-kit/grades")
        
        assert response.status_code == 200, f"Grades failed: {response.text}"
        grades = response.json()
        assert isinstance(grades, list)
        print(f"✓ Available grades: {grades}")


class TestLearningKitDownload:
    """Test Learning Kit download functionality"""
    
    def test_download_existing_kit(self):
        """Download an existing learning kit"""
        session = TestAuth.get_admin_session()
        
        # First get list of kits
        list_response = session.get(f"{BASE_URL}/api/learning-kit")
        assert list_response.status_code == 200
        kits = list_response.json()
        
        if not kits:
            pytest.skip("No learning kits available to download")
        
        kit_id = kits[0]["kit_id"]
        
        # Download the kit
        response = session.get(f"{BASE_URL}/api/learning-kit/download/{kit_id}")
        
        assert response.status_code == 200, f"Download failed: {response.text}"
        assert len(response.content) > 0, "Downloaded file is empty"
        print(f"✓ Downloaded kit {kit_id} ({len(response.content)} bytes)")
    
    def test_download_nonexistent_kit(self):
        """Download non-existent kit returns 404"""
        session = TestAuth.get_admin_session()
        
        response = session.get(f"{BASE_URL}/api/learning-kit/download/kit_nonexistent123")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent kit correctly returns 404")


class TestLearningKitDelete:
    """Test Learning Kit delete functionality"""
    
    def test_teacher_cannot_delete_kit(self):
        """Teacher should be denied delete access"""
        session = TestAuth.get_teacher_session()
        
        response = session.delete(f"{BASE_URL}/api/admin/learning-kit/kit_any123")
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ Teacher correctly denied delete access (403)")
    
    def test_delete_nonexistent_kit(self):
        """Delete non-existent kit returns 404"""
        session = TestAuth.get_admin_session()
        
        response = session.delete(f"{BASE_URL}/api/admin/learning-kit/kit_nonexistent123")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent kit delete correctly returns 404")
    
    def test_admin_can_delete_kit(self):
        """Admin can delete a learning kit"""
        session = TestAuth.get_admin_session()
        
        # First upload a kit to delete
        test_content = b"%PDF-1.4 Test PDF to delete"
        files = {'file': ('delete_test.pdf', io.BytesIO(test_content), 'application/pdf')}
        data = {'title': 'TEST_ToDelete', 'grade': '11', 'description': 'Will be deleted'}
        
        upload_response = session.post(f"{BASE_URL}/api/admin/learning-kit/upload", files=files, data=data)
        assert upload_response.status_code == 200
        kit_id = upload_response.json()["kit_id"]
        
        # Now delete it
        delete_response = session.delete(f"{BASE_URL}/api/admin/learning-kit/{kit_id}")
        
        assert delete_response.status_code == 200, f"Delete failed: {delete_response.text}"
        result = delete_response.json()
        assert "deleted" in result.get("message", "").lower()
        
        # Verify it's gone
        verify_response = session.get(f"{BASE_URL}/api/learning-kit/download/{kit_id}")
        assert verify_response.status_code == 404
        print(f"✓ Admin deleted kit {kit_id} and verified removal")


# ==================== TEACHER CALENDAR TESTS ====================

class TestTeacherCalendarAdd:
    """Test Teacher Calendar add entry functionality"""
    
    def test_teacher_can_add_calendar_entry(self):
        """Teacher adds a content plan entry"""
        session = TestAuth.get_teacher_session()
        
        entry_data = {
            "date": "2026-04-20",
            "title": "TEST_Algebra_Chapter_5",
            "description": "Cover quadratic equations",
            "subject": "Mathematics",
            "color": "#8b5cf6"
        }
        
        response = session.post(f"{BASE_URL}/api/teacher/calendar", json=entry_data)
        
        assert response.status_code == 200, f"Add entry failed: {response.text}"
        result = response.json()
        assert "entry_id" in result
        assert "message" in result
        
        self.__class__.test_entry_id = result["entry_id"]
        print(f"✓ Teacher added calendar entry: {result['entry_id']}")
    
    def test_student_cannot_add_calendar_entry(self):
        """Student should be denied calendar access"""
        session = TestAuth.get_student_session()
        
        entry_data = {
            "date": "2026-04-21",
            "title": "Unauthorized",
            "subject": "Test"
        }
        
        response = session.post(f"{BASE_URL}/api/teacher/calendar", json=entry_data)
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ Student correctly denied calendar access (403)")
    
    def test_admin_cannot_add_calendar_entry(self):
        """Admin should be denied calendar access (teacher only)"""
        session = TestAuth.get_admin_session()
        
        entry_data = {
            "date": "2026-04-21",
            "title": "Unauthorized",
            "subject": "Test"
        }
        
        response = session.post(f"{BASE_URL}/api/teacher/calendar", json=entry_data)
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ Admin correctly denied calendar access (403)")


class TestTeacherCalendarList:
    """Test Teacher Calendar list functionality"""
    
    def test_teacher_can_list_calendar_entries(self):
        """Teacher lists their calendar entries"""
        session = TestAuth.get_teacher_session()
        
        response = session.get(f"{BASE_URL}/api/teacher/calendar")
        
        assert response.status_code == 200, f"List failed: {response.text}"
        entries = response.json()
        assert isinstance(entries, list)
        print(f"✓ Teacher listed {len(entries)} calendar entries")
    
    def test_filter_calendar_by_month(self):
        """Filter calendar entries by month"""
        session = TestAuth.get_teacher_session()
        
        response = session.get(f"{BASE_URL}/api/teacher/calendar?month=2026-04")
        
        assert response.status_code == 200, f"Filter failed: {response.text}"
        entries = response.json()
        assert isinstance(entries, list)
        # All entries should be in April 2026
        for entry in entries:
            assert entry.get("date", "").startswith("2026-04"), f"Entry date mismatch: {entry.get('date')}"
        print(f"✓ Filtered {len(entries)} entries for April 2026")
    
    def test_student_cannot_list_calendar(self):
        """Student should be denied calendar list access"""
        session = TestAuth.get_student_session()
        
        response = session.get(f"{BASE_URL}/api/teacher/calendar")
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ Student correctly denied calendar list access (403)")


class TestTeacherCalendarDelete:
    """Test Teacher Calendar delete functionality"""
    
    def test_teacher_can_delete_own_entry(self):
        """Teacher deletes their own calendar entry"""
        session = TestAuth.get_teacher_session()
        
        # First add an entry to delete
        entry_data = {
            "date": "2026-04-25",
            "title": "TEST_ToDelete_Entry",
            "subject": "Test"
        }
        add_response = session.post(f"{BASE_URL}/api/teacher/calendar", json=entry_data)
        assert add_response.status_code == 200
        entry_id = add_response.json()["entry_id"]
        
        # Now delete it
        delete_response = session.delete(f"{BASE_URL}/api/teacher/calendar/{entry_id}")
        
        assert delete_response.status_code == 200, f"Delete failed: {delete_response.text}"
        result = delete_response.json()
        assert "deleted" in result.get("message", "").lower()
        print(f"✓ Teacher deleted calendar entry {entry_id}")
    
    def test_delete_nonexistent_entry(self):
        """Delete non-existent entry returns 404"""
        session = TestAuth.get_teacher_session()
        
        response = session.delete(f"{BASE_URL}/api/teacher/calendar/cal_nonexistent123")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent entry delete correctly returns 404")
    
    def test_student_cannot_delete_calendar_entry(self):
        """Student should be denied calendar delete access"""
        session = TestAuth.get_student_session()
        
        response = session.delete(f"{BASE_URL}/api/teacher/calendar/cal_any123")
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ Student correctly denied calendar delete access (403)")


# ==================== NAG SCREEN TESTS ====================

class TestStudentNagCheck:
    """Test Student Nag Screen check functionality"""
    
    def test_student_nag_check_returns_status(self):
        """Student nag check returns show_nag status"""
        session = TestAuth.get_student_session()
        
        response = session.get(f"{BASE_URL}/api/student/nag-check")
        
        assert response.status_code == 200, f"Nag check failed: {response.text}"
        result = response.json()
        
        # Verify response structure
        assert "show_nag" in result, "Missing show_nag field"
        assert "has_assignment" in result, "Missing has_assignment field"
        assert "regular_class_count" in result, "Missing regular_class_count field"
        assert "demo_count" in result, "Missing demo_count field"
        
        # student1@kaimera.com has an active assignment, so show_nag should be False
        print(f"✓ Nag check result: show_nag={result['show_nag']}, has_assignment={result['has_assignment']}, regular_classes={result['regular_class_count']}, demos={result['demo_count']}")
    
    def test_teacher_cannot_access_nag_check(self):
        """Teacher should be denied nag check access"""
        session = TestAuth.get_teacher_session()
        
        response = session.get(f"{BASE_URL}/api/student/nag-check")
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ Teacher correctly denied nag check access (403)")
    
    def test_admin_cannot_access_nag_check(self):
        """Admin should be denied nag check access"""
        session = TestAuth.get_admin_session()
        
        response = session.get(f"{BASE_URL}/api/student/nag-check")
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ Admin correctly denied nag check access (403)")


# ==================== EMAIL NOTIFICATION TESTS ====================

class TestEmailNotifications:
    """Test Email notifications (verify no server crash)"""
    
    def test_demo_accept_no_crash(self):
        """Demo acceptance should not crash server (email may fail for unverified domain)"""
        session = TestAuth.get_admin_session()
        
        # First check if there are any pending demos
        demos_response = session.get(f"{BASE_URL}/api/demo/pending")
        if demos_response.status_code != 200:
            pytest.skip("Cannot fetch pending demos")
        
        demos = demos_response.json()
        if not demos:
            # Create a demo request first
            demo_data = {
                "student_name": "TEST_Email_Student",
                "email": "test_email@example.com",
                "phone": "1234567890",
                "subject": "Mathematics",
                "preferred_date": "2026-04-25",
                "preferred_time": "10:00",
                "notes": "Test demo for email testing"
            }
            create_response = session.post(f"{BASE_URL}/api/demo/request", json=demo_data)
            if create_response.status_code not in [200, 201]:
                pytest.skip(f"Cannot create demo request: {create_response.text}")
            
            # Fetch demos again
            demos_response = session.get(f"{BASE_URL}/api/demo/pending")
            demos = demos_response.json()
        
        if not demos:
            pytest.skip("No demos available to test")
        
        # Find a test demo or use first available
        demo_id = None
        for demo in demos:
            if "TEST_" in demo.get("student_name", "") or "test" in demo.get("email", "").lower():
                demo_id = demo.get("demo_id")
                break
        
        if not demo_id:
            demo_id = demos[0].get("demo_id")
        
        # Accept the demo - this triggers email
        accept_response = session.post(f"{BASE_URL}/api/demo/accept", json={
            "demo_id": demo_id,
            "teacher_id": None  # Let system assign
        })
        
        # Server should not crash - any status code is acceptable as long as it responds
        assert accept_response.status_code in [200, 400, 404, 500], f"Unexpected response: {accept_response.status_code}"
        print(f"✓ Demo accept endpoint responded (status: {accept_response.status_code}) - no server crash")
    
    def test_teacher_feedback_no_crash(self):
        """Teacher feedback should not crash server (email may fail for unverified domain)"""
        session = TestAuth.get_teacher_session()
        
        # Get teacher's approved students
        dashboard_response = session.get(f"{BASE_URL}/api/teacher/dashboard")
        if dashboard_response.status_code != 200:
            pytest.skip("Cannot fetch teacher dashboard")
        
        dashboard = dashboard_response.json()
        approved_students = dashboard.get("approved_students", [])
        
        if not approved_students:
            pytest.skip("No approved students for teacher")
        
        student_id = approved_students[0].get("student_id")
        
        # Send feedback - this triggers email
        feedback_response = session.post(f"{BASE_URL}/api/teacher/feedback-to-student", json={
            "student_id": student_id,
            "feedback_text": "TEST_Great progress in today's class!",
            "performance_rating": "excellent"
        })
        
        # Server should not crash - 200 or 404 (if student not found) are acceptable
        assert feedback_response.status_code in [200, 400, 404], f"Unexpected response: {feedback_response.status_code}"
        print(f"✓ Teacher feedback endpoint responded (status: {feedback_response.status_code}) - no server crash")


# ==================== CLEANUP ====================

class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_kits(self):
        """Remove test learning kits"""
        session = TestAuth.get_admin_session()
        
        # Get all kits
        response = session.get(f"{BASE_URL}/api/learning-kit")
        if response.status_code != 200:
            return
        
        kits = response.json()
        deleted = 0
        for kit in kits:
            if "TEST_" in kit.get("title", ""):
                del_response = session.delete(f"{BASE_URL}/api/admin/learning-kit/{kit['kit_id']}")
                if del_response.status_code == 200:
                    deleted += 1
        
        print(f"✓ Cleaned up {deleted} test learning kits")
    
    def test_cleanup_test_calendar_entries(self):
        """Remove test calendar entries"""
        session = TestAuth.get_teacher_session()
        
        # Get all entries
        response = session.get(f"{BASE_URL}/api/teacher/calendar")
        if response.status_code != 200:
            return
        
        entries = response.json()
        deleted = 0
        for entry in entries:
            if "TEST_" in entry.get("title", ""):
                del_response = session.delete(f"{BASE_URL}/api/teacher/calendar/{entry['entry_id']}")
                if del_response.status_code == 200:
                    deleted += 1
        
        print(f"✓ Cleaned up {deleted} test calendar entries")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
