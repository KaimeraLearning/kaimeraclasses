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

### Admin Dashboard = "Operations Center"
Three main sections with sub-tabs:
1. **User Management**
   - Identity Creator: Single form with role dropdown (Student/Teacher/Counsellor), dynamic fields
   - Staff & Student Directory: Searchable data table with inline Block/Delete/Credits actions
   - Credentials & Access: Password reset + Badge management
2. **Financials**
   - Transaction Ledger: Daily revenue view (default), detail view, role filter, date range, search
   - Proofs & Approvals: Pending proof review with Approve/Reject
   - **System Pricing**: Unified Rates Dashboard - 4 fields: Demo Class Rate (student), Regular Class Fee (student), Demo Session Credit (teacher), Regular Class Pay (teacher)
3. **Reports**
   - Counsellor Tracking: Stats + daily activity bar chart (Recharts)
   - Class Overview: Searchable/filterable class table
   - Complaints: List with status

### Admin Student Profile Override
- Edit Profile button in User Drawer (students only)
- Editable fields: name, email, phone, credits, grade, institute, goal, preferred_time_slot, state, city, country, bio
- Direct save via POST /api/admin/edit-student/{user_id}

### Counsellor Assignment Flow
- Assignment modal now includes: Teacher selection, Class Frequency dropdown, Specific Days input, Demo Performance Notes textarea
- Active Assignments display shows frequency/days/demo notes metadata
- Student Profile drawer shows Demo History with teacher who conducted the demo

### Teacher Dashboard
- Classes of the Day, Grouped-by-Student view
- Reschedule Session UI: Button appears only when student cancels today's session
- Reschedule dialog: New date, start time, end time
- Two-way feedback: Teacher sends performance feedback to student (existing)
- Schedule Planner, Wallet, Learning Kit, Complaints links

### Student Dashboard
- UI Lockdown Mode for unenrolled students
- Demo booking, class attendance, complaints, learning kits

### Auth Flow
- **Self-signup students**: Email -> OTP verification -> Name/Password -> Account created
- **Admin-created accounts**: Admin creates via Identity Creator -> Direct login (no OTP)
- **Blocked accounts**: Get 403 on login, sessions invalidated

## Implemented Features (All DONE)

### Operations & Logic Refactor (DONE - Apr 9, 2026)
- CounsellorDashboard: Assignment modal with class_frequency, specific_days, demo_performance_notes
- CounsellorDashboard: Active assignments display with metadata
- CounsellorDashboard: Student profile shows demo history with teacher info
- TeacherDashboard: Reschedule Session UI (cancelled_today trigger)
- AdminDashboard: System Pricing tab with 4 global rate fields
- AdminDashboard: Student profile edit mode in user drawer
- Backend: Auto-cleanup background tasks, credit deduction engine
- Backend: Global system_pricing collection, admin edit-student endpoint
- StudentDashboard: UI Lockdown mode for unenrolled students

### Operations Center Refactoring (DONE - Apr 8, 2026)
- Unified Identity Creator with role dropdown + dynamic form fields
- Searchable staff/student data table
- Drill-down drawer for user profiles
- Inline admin controls: Block/Suspend, Delete, Reset Password, Adjust Credits
- Company Daily Revenue ledger, Role toggle filter, Date range picker
- Counsellor tracking bar chart (Recharts)

### OTP Email Verification (DONE - Apr 8, 2026)
### Login Page Redesign (DONE - Apr 8, 2026)

### Previous Features (All DONE)
- Teacher Dashboard: Classes of the Day + grouped-by-student view
- Wallet system with correct green/red coloring
- Badge templates with create/delete/assign
- Counsellor rejected student reassignment
- History search, Demo Booking Flow, Video Integration (Jitsi)
- Learning Kit System, Email Notifications (Resend)
- Teacher Calendar/Schedule Planner, Nag Screens
- Proof Pipeline, Complaints, Notifications, Stripe webhooks

## Key API Endpoints
- Auth: /api/auth/register, login, send-otp, verify-otp, session, me, logout
- Admin: /api/admin/create-user, block-user, delete-user, reset-password
- Admin: /api/admin/all-users, user-detail/{id}, approve-teacher
- Admin: /api/admin/set-pricing, get-pricing (4 global rate fields)
- Admin: /api/admin/edit-student/{user_id} (full profile override)
- Admin: /api/admin/transactions, counsellor-tracking, badge-templates
- Demo: /api/demo/request, live-sheet, accept, assign, feedback
- Counsellor: /api/counsellor/student-profile/{id} (now includes demo_history)
- Teacher: /api/teacher/reschedule-class/{class_id}
- Teacher: /api/teacher/feedback-to-student
- Search, Wallet, Classes, Learning Kit, Calendar, Notifications, Complaints

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
