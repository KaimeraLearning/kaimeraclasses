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

## Architecture (Updated Apr 8, 2026)

### Admin Dashboard = "Operations Center"
Three main sections with sub-tabs:
1. **User Management**
   - Identity Creator: Single form with role dropdown (Student/Teacher/Counsellor), dynamic fields
   - Staff & Student Directory: Searchable data table with inline Block/Delete/Credits actions
   - Credentials & Access: Password reset + Badge management
2. **Financials**
   - Transaction Ledger: Daily revenue view (default), detail view, role filter, date range, search
   - Proofs & Approvals: Pending proof review with Approve/Reject
3. **Reports**
   - Counsellor Tracking: Stats + daily activity bar chart (Recharts)
   - Class Overview: Searchable/filterable class table
   - Complaints: List with status

### Auth Flow
- **Self-signup students**: Email -> OTP verification -> Name/Password -> Account created
- **Admin-created accounts**: Admin creates via Identity Creator -> Direct login (no OTP)
- **Blocked accounts**: Get 403 on login, sessions invalidated

## Implemented Features

### Operations Center Refactoring (DONE - Apr 8, 2026)
- Unified Identity Creator with role dropdown + dynamic form fields
- Searchable staff/student data table with Name/Role/ID/Email/Credits/Status columns
- Drill-down drawer for user profiles (assignments, classes, wallet history)
- Inline admin controls: Block/Suspend, Delete, Reset Password, Adjust Credits
- Company Daily Revenue ledger (default view) with date/credits/deductions/net
- Role toggle filter (All/Student/Teacher/Counsellor)
- Date range picker + global search for transactions
- Detail transaction view with user enrichment
- Counsellor tracking bar chart (Recharts)

### OTP Email Verification (DONE - Apr 8, 2026)
- 3-step registration: Email -> OTP (6-digit, 10-min expiry) -> Profile details
- OTP stored in MongoDB `otp_codes` collection
- Resend API sends styled OTP email
- Admin-created accounts bypass OTP entirely

### Login Page Redesign (DONE - Apr 8, 2026)
- Split layout: branded left panel + auth right panel
- Login/Register tabs
- Google OAuth + email login
- "Book a Free Demo" CTA

### Previous Features (All DONE)
- Teacher Dashboard: Classes of the Day + grouped-by-student view
- Wallet system with correct green/red coloring
- Badge templates with create/delete/assign
- Counsellor rejected student reassignment
- History search (assignments + demos + logs)
- Demo Booking Flow + Live Sheet
- Video Integration (Jitsi Meet)
- Learning Kit System (grade-based PDFs)
- Email Notifications (Resend)
- Teacher Calendar / Schedule Planner
- Nag Screens for unassigned students
- Proof Pipeline: Teacher -> Counsellor -> Admin -> Wallet credit
- Complaints system, Notifications, Stripe webhooks

## Key API Endpoints
- Auth: /api/auth/register, login, send-otp, verify-otp, session, me, logout
- Admin: /api/admin/create-user (unified), block-user, delete-user, reset-password
- Admin: /api/admin/all-users, user-detail/{id}, approve-teacher
- Admin: /api/admin/transactions (supports ?view=daily, ?role=, ?date_from=, ?date_to=, ?search=)
- Admin: /api/admin/counsellor-tracking, counsellor-daily-stats/{id}
- Admin: /api/admin/badge-template(s), assign-badge
- Admin: /api/admin/approved-proofs, approve-proof, adjust-credits
- Demo: /api/demo/request, live-sheet, accept, assign, feedback
- Search: /api/search/teachers, history/search, filter/classes, filter/students
- Wallet: /api/wallet/summary
- Classes: /api/classes/create, /api/teacher/grouped-classes
- Learning Kit, Calendar, Notifications, Complaints endpoints

## DB Collections
users, user_sessions, otp_codes, class_sessions, student_teacher_assignments, transactions,
payment_transactions, complaints, class_proofs, feedback, notifications, system_pricing,
demo_requests, demo_extras, demo_feedback, history_logs, teacher_student_feedback,
renewal_meetings, counters, learning_kits, teacher_calendar, badge_templates

## Remaining Backlog
- P2: Jitsi screenshot fix (captureLargeVideoScreenshot API)
- P2: Verify Resend domain for production email delivery
- P3: Modular refactor of server.py into route files
- P3: Real-time WebSocket notifications
- P3: Student progress PDF reports
