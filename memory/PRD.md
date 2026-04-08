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

## Implemented Features

### Core CRM (DONE)
- 4-role system with session auth + Google OAuth
- Admin: create teachers/counsellors/students (with location/grade), set global pricing, approve teachers, adjust credits
- Counsellor: assign students (using admin's global pricing), view profiles, verify proofs, manage complaints
- Teacher: approve students, create classes, weekly view, submit proofs
- Student: view classes, cancel sessions, edit profile (state/city/country/grade), file complaints

### Teacher ID System (DONE - Apr 8, 2026)
- Auto-generated teacher codes on registration (KL-T0001 format)
- Searchable by name, ID, or email in Counsellor + Admin dashboards
- Teachers shown in searchable list format (not cards)

### Student Location & Grade (DONE - Apr 8, 2026)
- Students have state, city, country, grade (class level) fields
- Filterable by teachers via API
- Visible in counsellor/admin student cards

### Admin Global Pricing (DONE - Apr 8, 2026)
- Per demo + per class amounts set globally by admin
- Counsellor CANNOT override pricing during assignment
- System pricing auto-applied to all assignments

### Proof Workflow Pipeline (DONE - Apr 8, 2026)
- Teacher submits proof -> Counsellor verifies -> Auto-forwards to Admin
- Admin sees clickable proof cards with full class/student/teacher details
- Proofs filterable by date range
- Admin approves -> Amount auto-credited to teacher wallet
- Admin can reject with notes

### Wallet & Credit System (DONE - Apr 8, 2026)
- Dedicated /wallet page for teachers and students
- Teacher bank details (account name, number, bank, IFSC) in profile
- Transaction history with credit/debit display
- Pending earnings shown for teachers (proofs awaiting admin approval)
- Auto-credit on admin proof approval

### Class Filtration (DONE - Apr 8, 2026)
- Filter by: type (demo/regular), status (scheduled/in_progress/completed), search keyword
- Available in Admin + Counsellor dashboards
- Student filter by grade, city, state, country

### Badge System (DONE - Apr 8, 2026)
- Admin assigns badges to teachers/counsellors
- Badges displayed on profile cards and search results
- Badge management tab in Admin dashboard

### Renewal Detection (DONE - Apr 8, 2026)
- 80% completion threshold detection
- Alerts to counsellor, student, teacher
- Clickable renewal -> schedule meeting with student
- Meeting reflected on student dashboard

### Teacher Feedback to Student (DONE - Apr 8, 2026)
- Performance rating + feedback text
- In-app notification to student

### Demo Booking Flow (DONE - Apr 8, 2026)
- Public /book-demo form
- Live sheet for teachers/counsellors
- Auto-creates class + student account on acceptance
- Post-demo feedback with preferred teacher selection
- Max 3 demos per email, admin can grant 1 extra

### Video Integration - Jitsi Meet (DONE)
- Teacher starts class -> Jitsi room auto-created
- Student joins when teacher starts
- Screenshot capture functionality

### Other Completed Features
- Cancel class day (max 3, day extension)
- Complaints system with role-based visibility
- Notification system with bell icon
- Stripe payment webhook handling

## API Endpoints
### Auth: /api/auth/register, /api/auth/login, /api/auth/session, /api/auth/me, /api/auth/logout
### Demo: /api/demo/request, /api/demo/live-sheet, /api/demo/accept/{id}, /api/demo/assign, /api/demo/feedback
### Search: /api/search/teachers?q=, /api/filter/classes, /api/filter/students
### Wallet: /api/wallet/summary
### Proof Pipeline: /api/teacher/submit-proof -> /api/counsellor/verify-proof -> /api/admin/approved-proofs -> /api/admin/approve-proof
### Badges: /api/admin/assign-badge, /api/admin/remove-badge
### Renewal: /api/renewal/check, /api/renewal/schedule-meeting, /api/renewal/my-meetings
### Teacher: /api/teacher/feedback-to-student, /api/teacher/update-profile (bank_details)
### History: /api/history/search, /api/history/student/{id}, /api/history/teacher/{id}, /api/history/users

## DB Collections
- users, user_sessions, class_sessions, student_teacher_assignments, transactions, payment_transactions
- complaints, class_proofs, feedback, notifications, system_pricing
- demo_requests, demo_extras, demo_feedback, history_logs
- teacher_student_feedback, renewal_meetings, counters (new)

## Remaining Backlog
- P1: Learning Kit system (admin uploads by grade, students/teachers download PDFs)
- P1: Teacher content planning calendar
- P2: Nag screens/popups for unassigned students
- P2: Email notifications (for demo acceptance, teacher feedback)
- P2: Jitsi screenshot fix (use captureLargeVideoScreenshot API)
- P2: Advanced admin dashboard (manage all features from one place)
- P3: Complete migration of server.py into modular route files
- P3: Real-time notifications (WebSocket push)
