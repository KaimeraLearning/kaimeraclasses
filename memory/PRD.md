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

### Backend Structure (Modular - Refactored)
```
/app/backend/
  server.py              # Thin orchestrator (~90 lines) - CORS, startup, routers
  database.py            # Shared MongoDB connection (client + db)
  models/
    schemas.py           # All Pydantic request/response models
  services/
    auth.py              # get_current_user, hash_password, verify_password, create_session, seed_admin
    helpers.py           # generate_teacher_code, generate_student_code, send_email, generate_otp
    rating.py            # recalc_teacher_rating, record_rating_event
  tasks/
    background.py        # background_cleanup_task, background_preclass_alert_task
  routes/
    auth.py              # 7 endpoints - register, login, logout, session, me, OTP
    admin.py             # 38 endpoints - user mgmt, pricing, assignments, proofs, badges, purge
    teacher.py           # 18 endpoints - dashboard, rating, proofs, calendar, feedback
    student.py           # 6 endpoints - dashboard, profile, rate-class, enrollment, feedback
    classes.py           # 10 endpoints - CRUD, booking, start/end, cancel
    chat.py              # 4 endpoints - send, contacts, conversations, messages
    counsellor.py        # 8 endpoints - dashboard, proofs, reassign, search, student-profile
    demo.py              # 8 endpoints - request, assign, accept, feedback, live-sheet
    payments.py          # 3 endpoints - checkout, status, webhook
    general.py           # 19 endpoints - notifications, complaints, wallet, history, search, filter, renewal, learning kit
```
Total: **121 API endpoints**

### 1. Enrollment & Assignment Chain
- **Demo-First Constraint**: Counsellors cannot assign a student to a teacher until a demo class is marked successful
- **Matured Lead Logic**: Lead is MATURED when: (Demo Conducted) + (Assigned to same Demo Teacher) + (First regular class started)
- **Teacher Rating Filter**: Counsellor assignment modal filters teachers by Star Rating (1-5) buttons

### 2. Financial & Duplication Logic
- **Single Charge Rule**: NO charge on lead acceptance. Charge student wallet ONLY when teacher creates class (price_per_day x duration_days)
- **Insufficient Funds Trigger**: If Student_Wallet < Class_Cost -> error: "Action Failed: Insufficient funds"
- **Duplicate Prevention**: Only 1 active class per student-teacher pair at a time
- **System Pricing**: 4 global rates set by Admin (Demo Student Rate, Class Student Rate, Demo Teacher Credit, Class Teacher Pay)

### 3. Smart Dashboard & Session State
- **Teacher Dashboard**: Tabbed layout - Today's Sessions / Upcoming / Conducted Classes
- **Student Dashboard**: Live classes section / Pending Rating / Upcoming / Completed Classes
- **Multi-Day Logic**: Class with N days auto-tracks current_day. After final day -> Completed status -> prompts student rating
- **Cleanup**: Sessions auto-complete when past end_date

### 4. Teacher Rating & Penalty System
- **Star Rating (0-5)**: Calculated from student feedback average minus penalties
- **Cancellation Impact**: Every teacher cancellation records a rating event, -0.2 per cancellation
- **Bad Feedback Impact**: Student rating <=2 records bad_feedback event, -0.3 per bad feedback
- **Suspension Trigger**: 5+ cancellations/month -> 3-day account suspension (dashboard blocked, shows "Suspended" screen)
- **Visibility**: Detailed ratings (avg feedback, monthly cancellations, bad feedbacks, penalty) visible to Admin, Counsellor, and teacher themselves

### 5. Permission-Based Chat
- **Teachers**: Can only search/message their assigned students
- **Students**: Can only message their assigned teacher or any counsellor
- **Admin/Counsellor**: Global access to message any user
- **Identity**: User IDs (Student Code/Teacher Code) displayed in chat header + message bubbles

### Admin Dashboard = "Operations Center"
- User Management: Identity Creator, Staff & Student Directory, Credentials & Access
- Financials: Transaction Ledger, Proofs & Approvals, System Pricing (+ Purge System)
- Reports: Counsellor Tracking, Class Overview, Complaints

### Student Profile Security
- **Locked Profile**: Students cannot change Grade/Institute/Goal - only Admin can edit
- **Book Demo Hidden**: After demo is conducted, Book Demo tab/banner disappears
- **Auto-Delete**: 24h warning -> 48h total deletion for idle students (no demo/class)

## DB Collections
users, user_sessions, otp_codes, class_sessions, student_teacher_assignments, transactions,
payment_transactions, complaints, class_proofs, feedback, notifications, system_pricing,
demo_requests, demo_extras, demo_feedback, history_logs, teacher_student_feedback,
renewal_meetings, counters, learning_kits, teacher_calendar, badge_templates,
teacher_rating_events, chat_messages

## Completed Work
- [Apr 10, 2026] **Backend Modular Refactor COMPLETE** - 5220-line monolithic server.py refactored into 10 route modules + services + models + tasks. All 121 endpoints preserved. 100% regression pass (56/56 backend tests, all frontend dashboards verified).
- [Apr 9, 2026] Jitsi Screenshot CORS fix applied (captureLargeVideoScreenshot API) - TESTING PENDING
- Full EdTech CRM with all 4 role dashboards, Operations Center, wallet system, demo booking, chat, complaints, teacher rating/suspension, learning kits, etc.

## Remaining Backlog
- P1: Verify Jitsi screenshot fix works in live video class
- P2: Student progress PDF reports
- P2: Verify Resend domain for production email delivery
- P3: Real-time WebSocket notifications/chat
