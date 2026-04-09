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

## Architecture (Updated Apr 10, 2026)

### Backend Structure (Modular)
```
/app/backend/
  server.py              # Thin orchestrator (~90 lines)
  database.py            # Shared MongoDB connection
  models/schemas.py      # All Pydantic models
  services/auth.py       # Auth helpers + blocked user check
  services/helpers.py    # Code generators, email, OTP
  services/rating.py     # Teacher rating system
  tasks/background.py    # Cleanup + pre-class alerts
  routes/               # 10 route modules, 121 endpoints total
```

### Security Architecture (Implemented Apr 10, 2026)
1. **Blocked User Enforcement**: `get_current_user()` checks `is_blocked` flag, deletes sessions, returns 403
2. **Email Uniqueness**: MongoDB unique index on email + application-level checks on all create/edit endpoints
3. **Phone Uniqueness**: Application-level checks on register, create-user, create-student, create-teacher, edit-student, student profile update
4. **Session Invalidation**: Password reset deletes all user sessions; blocking a user deletes all sessions
5. **Credit Security**: Deduction floor prevents negative balance; atomic payment updates prevent double-crediting
6. **Proof Integrity**: One proof per class (single-day) or one proof per day (multi-day), tracked via `proof_date`
7. **Access Control**: Class status restricted to involved users; admin accounts protected from block/delete
8. **OTP Brute Force Protection**: Max 5 failed attempts per email, then OTP is invalidated
9. **Google OAuth**: Checks blocked status before allowing login
10. **Payment Race Condition Fix**: Atomic `$ne` filter on `payment_status` prevents concurrent double-credit

### Business Logic (Summary)
- Demo-First Constraint: Must complete demo before teacher assignment
- Single Charge Rule: Charge student wallet only on class creation
- Teacher Rating (0-5): Calculated from feedback average minus penalties
- Suspension: 5+ cancellations/month -> 3-day suspension
- Permission-Based Chat: Role-scoped messaging
- Locked Student Profile: Only admin can edit Grade/Institute/Goal

## DB Collections
users, user_sessions, otp_codes, class_sessions, student_teacher_assignments, transactions,
payment_transactions, complaints, class_proofs, feedback, notifications, system_pricing,
demo_requests, demo_extras, demo_feedback, history_logs, teacher_student_feedback,
renewal_meetings, counters, learning_kits, teacher_calendar, badge_templates,
teacher_rating_events, chat_messages

## Completed Work
- [Apr 10, 2026] **Security Hardening** — 12 fixes: blocked user enforcement, email/phone uniqueness, credit floor, session invalidation on password reset, class delete refunds, atomic payment updates, proof per-day tracking, OTP rate limiting, cross-account access restrictions. All verified (23/23 backend + all frontend tests passed).
- [Apr 10, 2026] **Backend Modular Refactor** — 5220-line server.py -> thin orchestrator + 10 route modules. All 121 endpoints preserved. 100% regression (56/56 tests).
- [Apr 9, 2026] Jitsi Screenshot CORS fix (captureLargeVideoScreenshot API) - TESTING PENDING
- Full EdTech CRM: 4-role dashboards, Operations Center, wallet, demo booking, chat, complaints, teacher rating/suspension, learning kits.

## Remaining Backlog
- P1: Verify Jitsi screenshot fix in live video class
- P2: Student progress PDF reports
- P2: Verify Resend domain for production email delivery
- P3: Real-time WebSocket notifications/chat
