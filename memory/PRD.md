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

## Architecture (Updated Apr 9, 2026)

### 1. Enrollment & Assignment Chain
- **Demo-First Constraint**: Counsellors cannot assign a student to a teacher until a demo class is marked successful
- **Matured Lead Logic**: Lead is MATURED when: (Demo Conducted) + (Assigned to same Demo Teacher) + (First regular class started)
- **Teacher Rating Filter**: Counsellor assignment modal filters teachers by Star Rating (1-5) buttons

### 2. Financial & Duplication Logic
- **Single Charge Rule**: NO charge on lead acceptance. Charge student wallet ONLY when teacher creates class (price_per_day × duration_days)
- **Insufficient Funds Trigger**: If Student_Wallet < Class_Cost → error: "Action Failed: Insufficient funds"
- **Duplicate Prevention**: Only 1 active class per student-teacher pair at a time
- **System Pricing**: 4 global rates set by Admin (Demo Student Rate, Class Student Rate, Demo Teacher Credit, Class Teacher Pay)

### 3. Smart Dashboard & Session State
- **Teacher Dashboard**: Tabbed layout — Today's Sessions / Upcoming / Conducted Classes
- **Student Dashboard**: Live classes section / Pending Rating / Upcoming / Completed Classes
- **Multi-Day Logic**: Class with N days auto-tracks current_day. After final day → Completed status → prompts student rating
- **Cleanup**: Sessions auto-complete when past end_date

### 4. Teacher Rating & Penalty System
- **Star Rating (0-5)**: Calculated from student feedback average minus penalties
- **Cancellation Impact**: Every teacher cancellation records a rating event, -0.2 per cancellation
- **Bad Feedback Impact**: Student rating <=2 records bad_feedback event, -0.3 per bad feedback
- **Suspension Trigger**: 5+ cancellations/month → 3-day account suspension (dashboard blocked, shows "Suspended" screen)
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
- **Locked Profile**: Students cannot change Grade/Institute/Goal — only Admin can edit
- **Book Demo Hidden**: After demo is conducted, Book Demo tab/banner disappears
- **Auto-Delete**: 24h warning → 48h total deletion for idle students (no demo/class)

## Key API Endpoints

### Auth
POST /api/auth/register, /login, /send-otp, /verify-otp, /me, /logout

### Admin
POST /api/admin/create-user, /block-user, /delete-user, /reset-password, /purge-system
POST /api/admin/set-pricing, GET /get-pricing
POST /api/admin/edit-student/{user_id}
GET /api/admin/teacher-ratings (all teacher ratings)

### Teacher
GET /api/teacher/dashboard → {todays_sessions, upcoming_classes, conducted_classes, star_rating, is_suspended}
POST /api/teacher/cancel-class/{id} → records rating event, refunds student
GET /api/teacher/my-rating → {star_rating, rating_details, recent_events}
POST /api/teacher/submit-demo-feedback (mandatory)
GET /api/teacher/pending-demo-feedback, /schedule, /reschedule-class

### Student
GET /api/student/dashboard → {live_classes, upcoming_classes, completed_classes, pending_rating}
POST /api/student/rate-class → {class_id, rating(1-5), comments} → impacts teacher rating
POST /api/student/update-profile (locked: only contact fields)

### Counsellor
GET /api/counsellor/dashboard → includes demo_teacher_name + demo_feedback on unassigned students

### Chat
POST /api/chat/send → scoped permission check
GET /api/chat/contacts → role-based filtered contacts
GET /api/chat/conversations → grouped by partner
GET /api/chat/messages/{partner_id} → auto marks as read

### Classes
POST /api/classes/create → insufficient funds check + duplicate prevention + multi-day charging

## DB Collections
users, user_sessions, otp_codes, class_sessions, student_teacher_assignments, transactions,
payment_transactions, complaints, class_proofs, feedback, notifications, system_pricing,
demo_requests, demo_extras, demo_feedback, history_logs, teacher_student_feedback,
renewal_meetings, counters, learning_kits, teacher_calendar, badge_templates,
teacher_rating_events, chat_messages

## Remaining Backlog
- P2: Jitsi screenshot fix (captureLargeVideoScreenshot API)
- P2: Verify Resend domain for production email delivery
- P3: Modular refactor of server.py into route files
- P3: Real-time WebSocket notifications / chat
- P3: Student progress PDF reports
