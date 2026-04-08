# Kaimera Learning - EdTech CRM Platform PRD

## Original Problem Statement
Complete EdTech CRM/Management Platform with 4 roles: Admin, Counsellor, Teacher, Student.
Flow: Counsellor assigns Student -> Teacher approves -> Teacher creates class -> Video (Jitsi) -> Proofs -> Admin approves & credits teacher.

## Tech Stack
- Frontend: React + Shadcn/UI + Tailwind CSS
- Backend: FastAPI (Python)
- Database: MongoDB (Motor async driver)
- Auth: Session-based + Emergent Google OAuth
- Payments: Stripe (test key, webhook handling)
- Video: Jitsi Meet (free, CDN-loaded)
- Email: Resend API (transactional emails)

## Implemented Features

### Core CRM (DONE)
- 4-role system with session auth + Google OAuth
- Admin: create teachers/counsellors/students (with location/grade), set global pricing, approve teachers, adjust credits
- Counsellor: assign students (using admin's global pricing), view profiles, verify proofs, manage complaints
- Teacher: approve students, create classes, weekly view, submit proofs
- Student: view classes, cancel sessions, edit profile (state/city/country/grade), file complaints

### Teacher ID System (DONE)
- Auto-generated teacher codes (KL-T0001 format)
- Searchable by name/ID in Counsellor + Admin dashboards

### Student Location & Grade (DONE)
- Students have state, city, country, grade fields
- Filterable by location/grade across dashboards

### Admin Global Pricing (DONE)
- Per demo + per class amounts set globally by admin
- Counsellor cannot override pricing during assignment

### Proof Workflow Pipeline (DONE)
- Teacher submits -> Counsellor verifies -> Admin reviews (date-filterable) -> Auto-credits teacher wallet

### Wallet & Credit System (DONE)
- Dedicated /wallet page for teachers (bank details) and students
- Transaction history, pending earnings display

### Class Filtration (DONE)
- Filter by type (demo/regular), status, search keyword
- Student filter by grade, city, state

### Badge System (DONE)
- Admin assigns badges to teachers/counsellors

### Renewal Detection (DONE)
- 80% completion threshold alerts
- Clickable → schedule meeting with student

### Teacher Feedback (DONE)
- Performance feedback to students (in-app notification + email)

### Demo Booking Flow (DONE)
- Public /book-demo form, live sheet, auto-class creation, post-demo feedback, demo limits

### Video Integration - Jitsi Meet (DONE)
- Teacher starts class -> Jitsi room auto-created, student joins when started

### Learning Kit System (DONE - Apr 8, 2026)
- Admin uploads PDF/doc materials by grade level
- Students see only their grade's materials
- Teachers see all materials with grade filter
- Download functionality for both roles
- Admin can delete kits

### Teacher Content Planning Calendar (DONE - Apr 8, 2026)
- Monthly calendar view with content planning entries
- Color-coded entries by subject/topic
- Add/delete entries by clicking on calendar days
- Month navigation (prev/next)

### Nag Screens (DONE - Apr 8, 2026)
- Prominent banner on student dashboard for unassigned students
- "Start your regular classes" with demo count tracking
- Automatically hidden when student has active teacher assignment

### Email Notifications (DONE - Apr 8, 2026)
- Resend integration for transactional emails
- Demo acceptance email (with class details, credentials if new student)
- Teacher feedback email (with rating and feedback content)
- Note: Resend free tier requires domain verification for external recipients

### Other Completed Features
- Cancel class day (max 3, day extension)
- Complaints system with role-based visibility
- Notification system with bell icon
- Stripe payment webhook handling

## Key API Endpoints
- Auth: /api/auth/register, login, session, me, logout
- Demo: /api/demo/request, live-sheet, accept, assign, feedback
- Search: /api/search/teachers, /api/filter/classes, /api/filter/students
- Wallet: /api/wallet/summary
- Proof Pipeline: teacher/submit-proof -> counsellor/verify-proof -> admin/approved-proofs -> admin/approve-proof
- Badges: /api/admin/assign-badge, remove-badge
- Renewal: /api/renewal/check, schedule-meeting, my-meetings
- Learning Kit: /api/admin/learning-kit/upload, /api/learning-kit, /api/learning-kit/download/{id}, /api/learning-kit/grades
- Calendar: /api/teacher/calendar (GET, POST, DELETE)
- Nag: /api/student/nag-check
- Feedback: /api/teacher/feedback-to-student

## DB Collections
users, user_sessions, class_sessions, student_teacher_assignments, transactions, payment_transactions,
complaints, class_proofs, feedback, notifications, system_pricing,
demo_requests, demo_extras, demo_feedback, history_logs,
teacher_student_feedback, renewal_meetings, counters,
learning_kits, teacher_calendar

## Remaining Backlog
- P2: Jitsi screenshot fix (use captureLargeVideoScreenshot API)
- P2: Verify Resend domain for production email delivery
- P3: Complete migration of server.py into modular route files
- P3: Real-time notifications (WebSocket push)
- P3: Student progress reports (PDF generation)
