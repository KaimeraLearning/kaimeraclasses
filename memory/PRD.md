# Kaimera Learning - EdTech CRM Platform PRD

## Original Problem Statement
Complete EdTech CRM/Management Platform with 4 roles: Admin, Counsellor, Teacher, Student.
Students cannot self-register openly. Admin creates student accounts manually and shares credentials.
Counsellor assigns students to teachers. Teacher approves, creates classes (auto-enrollment).
Complaints visibility is role-scoped: student complaints go to their assigned teacher + counsellor only.

## Tech Stack
- Frontend: React + Shadcn/UI + Tailwind CSS
- Backend: FastAPI (Python)
- Database: MongoDB (Motor async driver)
- Auth: Session-based + Emergent Google OAuth
- Payments: Stripe (test key)

## Core Workflow
1. Admin creates student account (email + password + details) → shares credentials
2. Counsellor assigns student to teacher with custom credit price
3. Teacher approves assignment (24hr window)
4. Teacher creates class for student → auto-enrollment + credit deduction
5. Student attends classes; can cancel a day's session (max 3, then class dismissed)
6. Teacher submits proof after class → Counsellor verifies → Teacher earns wallet credits
7. If class duration expires: rebook within 3 days OR release to counsellor pool

## Implemented Features

### Core CRM (DONE)
- 4-role system: Admin, Counsellor, Teacher, Student
- Session-based auth + Google OAuth
- Admin: create teachers/counsellors/students, set pricing, approve teachers, adjust credits
- Counsellor: assign students, view profiles, verify proofs, manage complaints
- Teacher: approve students, create classes (1:1/group, demo/regular), submit proofs
- Student: view classes, cancel sessions, edit profile, file complaints

### Student Account Creation by Admin (DONE)
- POST /api/admin/create-student endpoint
- Admin fills name, email, password, institute, goal, time slot, phone
- Returns credentials that admin shares with student
- Admin cannot edit existing credentials (by design)

### Class Cancellation System (DONE)
- Student clicks "Cancel Today's Session" → class extends by 1 day
- Cancellation tracker shows X/3 used with progress bar
- After 3 cancellations → class dismissed
- Teacher receives notification on each cancellation
- No Join/Cancel Booking buttons (removed)

### Complaint Visibility (DONE)
- Student complaints auto-link to their assigned teacher
- Teachers see ONLY complaints from their students (not other teachers' students)
- Counsellors see ALL complaints
- Admin sees ALL complaints and can resolve them

### Notification System (DONE)
- Teacher notification bell with unread count
- Notifications for: class cancellations, class dismissals, student complaints
- Mark all read functionality

### Demo Sessions & Class Verification (DONE)
- Demo vs regular class toggle
- Teacher proof submission (feedback, performance, topics, screenshot)
- Counsellor proof verification → teacher earns credits

### Profile & Student Details (DONE)
- Student profile popup for counsellors (institute, goal, time slot, class history)
- Student profile edit (phone, institute, goal, time slot)
- Teacher schedule calendar view

### Auto-Reassignment (DONE)
- Expired classes flagged on counsellor dashboard
- Rebook within 3 days or release student

## API Endpoints
### Auth: /api/auth/register, /api/auth/login, /api/auth/session, /api/auth/me, /api/auth/logout
### Student: /api/student/dashboard, /api/student/update-profile, /api/classes/browse, /api/classes/cancel-day/{id}
### Teacher: /api/teacher/dashboard, /api/teacher/approve-assignment, /api/teacher/submit-proof, /api/teacher/my-proofs, /api/teacher/student-complaints
### Counsellor: /api/counsellor/dashboard, /api/counsellor/student-profile/{id}, /api/counsellor/pending-proofs, /api/counsellor/all-proofs, /api/counsellor/verify-proof, /api/counsellor/expired-classes, /api/counsellor/reassign-student
### Admin: /api/admin/teachers, /api/admin/students, /api/admin/classes, /api/admin/complaints, /api/admin/resolve-complaint, /api/admin/assign-student, /api/admin/create-teacher, /api/admin/create-counsellor, /api/admin/create-student, /api/admin/set-pricing, /api/admin/approve-teacher, /api/admin/adjust-credits
### Notifications: /api/notifications/my, /api/notifications/mark-read/{id}, /api/notifications/mark-all-read
### Complaints: /api/complaints/create, /api/complaints/my

## Remaining Backlog
- P2: Stripe integration robustness (webhooks, real payment flow)
- P3: Video integration for live classes
- P3: Refactor server.py into modular routers
