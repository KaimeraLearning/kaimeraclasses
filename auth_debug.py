#!/usr/bin/env python3
"""
Debug Authentication Issues
"""

import requests
import json

BASE_URL = "https://skill-exchange-149.preview.emergentagent.com/api"

def test_auth_debug():
    print("🔍 Debugging Authentication Issues...")
    
    # Test admin login
    print("\n1. Testing Admin Login:")
    response = requests.post(f"{BASE_URL}/auth/login", json={
        'email': 'info@kaimeralearning.com',
        'password': 'solidarity&peace2023'
    })
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        admin_data = response.json()
        admin_token = admin_data['session_token']
        print(f"Admin User: {admin_data['user']}")
        
        # Test admin profile
        print("\n2. Testing Admin Profile:")
        profile_response = requests.get(f"{BASE_URL}/auth/me", 
                                      headers={'Authorization': f'Bearer {admin_token}'})
        print(f"Status: {profile_response.status_code}")
        if profile_response.status_code == 200:
            profile_data = profile_response.json()
            print(f"Profile: {profile_data}")
        else:
            print(f"Error: {profile_response.text}")
    else:
        print(f"Login failed: {response.text}")
    
    # Test student1 login
    print("\n3. Testing Student1 Login:")
    response = requests.post(f"{BASE_URL}/auth/login", json={
        'email': 'student1@kaimera.com',
        'password': 'password123'
    })
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        student_data = response.json()
        student_token = student_data['session_token']
        print(f"Student User: {student_data['user']}")
        
        # Test student profile
        print("\n4. Testing Student Profile:")
        profile_response = requests.get(f"{BASE_URL}/auth/me", 
                                      headers={'Authorization': f'Bearer {student_token}'})
        print(f"Status: {profile_response.status_code}")
        if profile_response.status_code == 200:
            profile_data = profile_response.json()
            print(f"Profile: {profile_data}")
        else:
            print(f"Error: {profile_response.text}")
    else:
        print(f"Login failed: {response.text}")

if __name__ == "__main__":
    test_auth_debug()