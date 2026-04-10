# Kaimera Learning - EdTech CRM Platform PRD

## Original Problem Statement
Complete EdTech CRM/Management Platform with 4 roles: Admin, Counselor, Teacher, Student.
Flow: Counselor assigns Student -> Teacher approves -> Teacher creates class -> Video (Jitsi) -> Proofs -> Admin approves & credits teacher.

## Tech Stack
- Frontend: React + Shadcn/UI + Tailwind CSS + Recharts
- Backend: FastAPI (Python), Modular architecture (routes/, models/, services/, tasks/)
- Database: MongoDB (Motor async driver)

## Key Fixes (Apr 10, 2026)

### Demo-First Assignment Flow (FIXED)
- Demo completion now properly transitions demo_request status to "completed" when demo class ends
- Assignment constraint checks: demo_requests.student_id, demo_requests.student_user_id, AND completed demo class_sessions
- Counselor can now successfully assign students after demo is conducted

### Class Lifecycle (FIXED)  
- Classes auto-move to conducted tab after end time passes (within same day)
- Submit Proof button visible on conducted classes (hidden if already submitted)
- Cancel button disabled after click (prevents double-cancel/double-rating-deduction)
- Backend rejects cancel on already-cancelled class (400 error)

### Profile System
- KLAT Score (Teacher) / KL-CAT Score (Counselor) — manual text fields, separate from star_rating
- Full profile: bio, age, DOB, address, education, interests, experience, profile pic, resume
- Bank details locked after first entry, admin-only override
- Profile popups show full details when clicking names

### Security
- Single device sessions, blocked user enforcement, email/phone uniqueness
- Credit floor, atomic payments, class delete refunds, proof per-day tracking

## Completed Work (Latest First)
- [Apr 10] Fixed counselor assignment after demo + proof button visibility + demo auto-completion
- [Apr 10] KLAT/KL-CAT manual scores, cancel double-click prevention, profile popups
- [Apr 10] Spelling (Counselor), proof screenshot, teacher/counselor profiles, error handling
- [Apr 10] Single device session, demo-based chat, student locked view
- [Apr 10] Security hardening (12 fixes) + Backend modular refactor

## Remaining Backlog
- P1: Verify Jitsi screenshot fix in live video class
- P2: Student progress PDF reports
- P2: Verify Resend domain for production email delivery
- P3: Real-time WebSocket notifications/chat
