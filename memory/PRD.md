# Kaimera Learning - EdTech CRM Platform PRD

## Original Problem Statement
Complete EdTech CRM/Management Platform with 4 roles: Admin, Counselor, Teacher, Student.
Flow: Counselor assigns Student -> Teacher approves -> Teacher creates class -> Video (Jitsi) -> Proofs -> Admin approves & credits teacher.

## Tech Stack
- Frontend: React + Shadcn/UI + Tailwind CSS + Recharts
- Backend: FastAPI (Python), Modular architecture (routes/, models/, services/, tasks/)
- Database: MongoDB (Motor async driver)
- Auth: Session-based (single device) + Emergent Google OAuth + Email OTP
- Payments: Stripe (webhook handling)
- Video: Jitsi Meet (CDN)
- Email: Resend API

## Architecture

### Backend: 10 route modules, 125+ endpoints
### Security: Single device sessions, blocked user enforcement, email/phone uniqueness, credit floor, atomic payments, bank lock, OTP rate limiting

### Profile System
- **Teacher**: KLAT Score (manual string input), bio, age, DOB, address, education, interests, teaching experience, profile picture, PDF resume, bank details (locked after first entry)
- **Counselor**: KL-CAT Score (manual string input), same personal fields, Counselor ID (KLC-XXXXXX)
- **Bank Details**: Visible to admin only, locked after first entry, admin-only override
- **star_rating**: Separate automated 1-5 rating (from feedback/penalties) - NOT the same as KLAT/KL-CAT

### Class Lifecycle
- Classes auto-move to conducted tab after end time passes
- Submit Proof button appears on conducted classes (hidden if already submitted)
- Cancel button disabled after click (prevents double-cancel/double-rating-deduction)

### Profile Popups
- Clicking teacher/counselor/student name anywhere shows full profile dialog
- Admin sees bank details; other roles don't
- Shows KLAT/KL-CAT, bio, education, experience, resume, badges, star rating

## Completed Work
- [Apr 10, 2026] **KLAT/KL-CAT manual scores**, cancel double-click prevention, class auto-conducted + proof visibility, profile popup with full details. All verified 100% (18/18 backend + all frontend).
- [Apr 10, 2026] Spelling fix (Counselor), proof screenshot upload, teacher/counselor profile system, removed preferred time, global error handling
- [Apr 10, 2026] Single device session, demo-based chat, student locked view with demo classes + Chat button
- [Apr 10, 2026] Security hardening (12 fixes) + Backend modular refactor (5220->90 line server.py)

## Remaining Backlog
- P1: Verify Jitsi screenshot fix in live video class
- P2: Student progress PDF reports
- P2: Verify Resend domain for production email delivery
- P3: Real-time WebSocket notifications/chat
