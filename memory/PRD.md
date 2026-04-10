# Kaimera Learning - EdTech CRM Platform PRD

## Original Problem Statement
Complete EdTech CRM/Management Platform with 4 roles: Admin, Counsellor, Teacher, Student.
Flow: Counsellor assigns Student -> Teacher approves -> Teacher creates class -> Video (Jitsi) -> Proofs -> Admin approves & credits teacher.

## Tech Stack
- Frontend: React + Shadcn/UI + Tailwind CSS + Recharts
- Backend: FastAPI (Python)
- Database: MongoDB (Motor async driver)
- Auth: Session-based + Emergent Google OAuth + Email OTP verification
- Payments: Stripe (test key, webhook handling)
- Video: Jitsi Meet (free, CDN-loaded)
- Email: Resend API (transactional + OTP emails)

## Architecture

### Backend Structure (Modular)
```
/app/backend/
  server.py              # Thin orchestrator (~90 lines)
  database.py            # Shared MongoDB connection
  models/schemas.py      # All Pydantic models
  services/auth.py       # Auth helpers + blocked user check + single device session
  services/helpers.py    # Code generators, email, OTP
  services/rating.py     # Teacher rating system
  tasks/background.py    # Cleanup + pre-class alerts
  routes/               # 10 route modules, 121 endpoints total
```

### Security Architecture
1. **Single Device Session**: `create_session()` deletes all existing sessions before creating new one
2. **Blocked User Enforcement**: `get_current_user()` checks `is_blocked`, purges sessions, returns 403
3. **Email/Phone Uniqueness**: DB index + app-level checks on all create/edit endpoints
4. **Credit Security**: Deduction floor, atomic payment updates, class delete refunds
5. **Proof Integrity**: One proof per class/day, tracked via `proof_date`
6. **OTP Brute Force Protection**: Max 5 failed attempts per email
7. **Session Invalidation**: Password reset and user blocking purge all sessions

### Chat System
- **Demo-aware contacts**: Chat contacts include teachers/students from accepted demo classes (not just formal assignments)
- **Permission scoping**: Teachers can message their assigned + demo students; Students can message assigned + demo teachers + counsellors
- Admin/Counsellor: global chat access

### Student Dashboard
- **Locked View** (not enrolled): Shows demo classes with Join button, Chat button, Profile, Wallet, Book Demo
- **Enrolled View**: Full dashboard with live/upcoming/completed/pending rating sections

## DB Collections
users, user_sessions, otp_codes, class_sessions, student_teacher_assignments, transactions,
payment_transactions, complaints, class_proofs, feedback, notifications, system_pricing,
demo_requests, demo_extras, demo_feedback, history_logs, teacher_student_feedback,
renewal_meetings, counters, learning_kits, teacher_calendar, badge_templates,
teacher_rating_events, chat_messages

## Completed Work
- [Apr 10, 2026] **3 Feature Updates**: Single device session enforcement, demo-based chat contacts (teacher accepts demo -> both see each other in chat), student locked view shows demo classes + Chat button. All verified (18/18 backend + all frontend passed).
- [Apr 10, 2026] **Security Hardening** — 12 fixes: blocked user enforcement, email/phone uniqueness, credit floor, session invalidation, class delete refunds, atomic payments, proof per-day, OTP rate limiting.
- [Apr 10, 2026] **Backend Modular Refactor** — 5220-line server.py -> thin orchestrator + 10 route modules. 121 endpoints preserved.
- Full EdTech CRM: 4-role dashboards, Operations Center, wallet, demo booking, chat, complaints, teacher rating/suspension, learning kits.

## Remaining Backlog
- P1: Verify Jitsi screenshot fix in live video class
- P2: Student progress PDF reports
- P2: Verify Resend domain for production email delivery
- P3: Real-time WebSocket notifications/chat
