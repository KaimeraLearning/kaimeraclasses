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
- Teacher: approve students, create classes, grouped student view, submit proofs
- Student: view classes, cancel sessions, edit profile (state/city/country/grade), file complaints

### Teacher Dashboard UI Overhaul (DONE - Apr 8, 2026)
- "Classes of the Day" section showing today's active classes
- Grouped-by-student view replacing weekly view
- Clickable student groups that expand to show their classes
- Student search filter by name
- Feedback button on each student group
- "Schedule Planner" button (renamed from Content Planner)
- Ended classes separated into history count

### Admin Dashboard Enhancements (DONE - Apr 8, 2026)
- **Credentials Tab**: Password reset for any user by email, global user search with clickable profiles opening full detail dialog
- **Counsellors Tab**: Counsellor tracking showing assignment statistics (total, active, pending, rejected)
- **Badge Templates**: Create/delete badge templates, assign from dropdown or custom name
- User detail dialog showing profile, assignments, classes, transactions

### Wallet UI Color Fix (DONE - Apr 8, 2026)
- Credits show as green "+" (earnings, admin adds, proof approved)
- Debits show as red "-" (payments, deductions)
- Smart type detection for transaction direction

### Teacher ID System (DONE)
- Auto-generated teacher codes (KL-T0001 format)
- Searchable by name/ID in Counsellor + Admin dashboards

### Student Location & Grade (DONE)
- Students have state, city, country, grade fields
- Filterable by location/grade across dashboards

### Admin Global Pricing (DONE)
- Per demo + per class amounts set globally by admin

### Proof Workflow Pipeline (DONE)
- Teacher submits -> Counsellor verifies -> Admin reviews (date-filterable) -> Auto-credits teacher wallet

### Wallet & Credit System (DONE)
- Dedicated /wallet page for teachers (bank details) and students
- Transaction history with correct color-coded amounts

### Badge System (DONE)
- Admin creates badge templates for reuse
- Assigns from dropdown or custom name
- Badge templates manageable (create/delete)

### Demo Booking Flow (DONE)
- Public /book-demo form, live sheet, auto-class creation, post-demo feedback, demo limits

### Video Integration - Jitsi Meet (DONE)
- Teacher starts class -> Jitsi room auto-created, student joins when started

### Learning Kit System (DONE)
- Admin uploads PDF/doc materials by grade level
- Students see only their grade's materials, teachers see all

### Teacher Content Planning Calendar (DONE)
- Monthly calendar view with content planning entries

### Nag Screens (DONE)
- Prominent banner on student dashboard for unassigned students

### Email Notifications (DONE)
- Resend integration for demo acceptance and teacher feedback emails

### Other Completed Features
- Cancel class day (max 3, day extension)
- Complaints system with role-based visibility
- Notification system with bell icon
- Stripe payment webhook handling
- Renewal detection (80% threshold alerts)
- Teacher feedback to students

## Key API Endpoints
- Auth: /api/auth/register, login, session, me, logout
- Demo: /api/demo/request, live-sheet, accept, assign, feedback
- Search: /api/search/teachers, /api/filter/classes, /api/filter/students
- Wallet: /api/wallet/summary
- Proof Pipeline: teacher/submit-proof -> counsellor/verify-proof -> admin/approved-proofs -> admin/approve-proof
- Badges: /api/admin/assign-badge, remove-badge, badge-template(s)
- Credentials: /api/admin/reset-password, all-users, user-detail/{id}
- Counsellor Tracking: /api/admin/counsellor-tracking
- Learning Kit: /api/admin/learning-kit/upload, /api/learning-kit, /api/learning-kit/download/{id}
- Calendar: /api/teacher/calendar (GET, POST, DELETE)
- Grouped Classes: /api/teacher/grouped-classes

## DB Collections
users, user_sessions, class_sessions, student_teacher_assignments, transactions, payment_transactions,
complaints, class_proofs, feedback, notifications, system_pricing,
demo_requests, demo_extras, demo_feedback, history_logs,
teacher_student_feedback, renewal_meetings, counters,
learning_kits, teacher_calendar, badge_templates

## Remaining Backlog
- P2: Jitsi screenshot fix (use captureLargeVideoScreenshot API)
- P2: Verify Resend domain for production email delivery
- P3: Complete migration of server.py into modular route files
- P3: Real-time notifications (WebSocket push)
- P3: Student progress reports (PDF generation)
