# Kaimera Learning - EdTech CRM Platform PRD

## Original Problem Statement
Complete EdTech CRM/Management Platform with 4 roles: Admin, Counsellor, Teacher, Student.
Admin creates student accounts manually. Counsellor assigns students to teachers. Teacher approves, creates classes with live video (Jitsi Meet). Classes show on weekly view. Teacher can start/end class, take screenshots. Student joins only when teacher starts.

**New Demo Workflow**: Public demo booking form -> Live sheet for teachers/counsellors -> Teacher accepts (auto-creates class) -> Student notified -> Post-demo feedback -> Counsellor assigns regular teacher.

## Tech Stack
- Frontend: React + Shadcn/UI + Tailwind CSS
- Backend: FastAPI (Python)
- Database: MongoDB (Motor async driver)
- Auth: Session-based + Emergent Google OAuth
- Payments: Stripe (test key, webhook handling)
- Video: Jitsi Meet (free, CDN-loaded)

## Core Workflow
1. Admin creates student account -> shares credentials
2. Counsellor assigns student to teacher with custom price
3. Teacher approves assignment
4. Teacher creates class -> auto-enrollment + credit deduction
5. Teacher starts class -> Jitsi room opens, student gets notification
6. Student joins live class -> video room
7. Teacher takes screenshots during class -> saved to device
8. Teacher ends class -> status resets (or completes if last day)
9. Student can cancel class day (max 3, then dismissed)
10. Teacher submits proof -> Counsellor verifies -> Teacher earns credits

## Demo Booking Flow (NEW)
1. New person/student visits /book-demo -> Fills form (Name, Email, Phone*, Age, Institute, Date, Time, Message)
2. Demo appears on "Live Sheet" (/demo-live-sheet) for all teachers & counsellors
3. Teacher accepts demo OR counsellor assigns to teacher
4. Auto-creates: student account (if new), demo class session, notifications
5. Demo conducted via Jitsi Meet
6. Student submits post-demo feedback (rating, text, preferred teacher)
7. Counsellor sees feedback -> assigns student to regular teacher
8. Max 3 demos per email. Admin can grant exactly 1 extra.

## Implemented Features

### Core CRM (DONE)
- 4-role system, session auth + Google OAuth
- Admin: create teachers/counsellors/students, set pricing, approve teachers, adjust credits
- Counsellor: assign students, view profiles, verify proofs, manage complaints
- Teacher: approve students, create classes (1:1/group, demo/regular), weekly class view
- Student: view classes, cancel sessions, edit profile, file complaints

### Video Integration - Jitsi Meet (DONE)
- Teacher starts class -> Jitsi Meet room auto-created per class
- Student sees "Join Live Class Now" button (only when teacher has started)
- Screenshot capture: screen capture API + html2canvas fallback
- Teacher ends class -> room closes, status resets

### Demo Booking & Tracking (DONE - Apr 8, 2026)
- Public /book-demo page with creative UI (split layout, form with all fields)
- /demo-live-sheet: Teachers see Accept button, Counsellors see Assign dropdown
- Teacher accept: auto-creates class + student account, sends notification
- Counsellor assign: picks teacher, auto-creates class
- /history page: Search logs, view student/teacher profiles with full history
- /demo-feedback page: Student rates demo, selects preferred teacher
- Demo limits: max 3 per email, admin grant-extra endpoint
- Navigation links added to all 4 dashboards + login page

### Teacher Dashboard Week View (DONE)
- Main screen: "This Week's Classes" - only shows classes overlapping current week
- Collapsible "Other Classes" panel
- Start Class button navigates to video room

### Teacher Schedule Calendar (DONE)
- Calendar shows date ranges for multi-day classes
- Status labels: BOOKED, LIVE, DONE, OFF
- Color-coded

### Class Cancellation System (DONE)
- Student cancels day -> extends class by 1 day, teacher notified
- Max 3 cancellations -> class dismissed

### Complaint Visibility (DONE)
- Student complaints auto-link to assigned teacher
- Teachers see ONLY their students' complaints
- Counsellors see ALL complaints

### Notification System (DONE)
- Teacher bell with unread count
- Triggers: class cancellations, dismissals, complaints, class started, demo accepted/assigned

### Stripe Payment (DONE)
- Checkout session with credit packages
- Webhook handler: verifies payment -> credits user account

## API Endpoints
### Auth: /api/auth/register, /api/auth/login, /api/auth/session, /api/auth/me, /api/auth/logout
### Student: /api/student/dashboard, /api/student/update-profile, /api/classes/browse, /api/classes/cancel-day/{id}
### Teacher: /api/teacher/dashboard, /api/teacher/approve-assignment, /api/teacher/submit-proof, /api/teacher/my-proofs, /api/teacher/student-complaints
### Classes: /api/classes/create, /api/classes/start/{id}, /api/classes/end/{id}, /api/classes/status/{id}, /api/classes/delete/{id}
### Counsellor: /api/counsellor/dashboard, /api/counsellor/student-profile/{id}, /api/counsellor/pending-proofs, /api/counsellor/all-proofs, /api/counsellor/verify-proof, /api/counsellor/expired-classes
### Admin: /api/admin/create-student, /api/admin/create-teacher, /api/admin/create-counsellor, /api/admin/set-pricing, /api/admin/approve-teacher, /api/admin/adjust-credits, /api/admin/complaints, /api/admin/resolve-complaint, /api/admin/grant-demo-extra
### Demo: /api/demo/request (PUBLIC), /api/demo/live-sheet, /api/demo/accept/{id}, /api/demo/assign, /api/demo/my-demos, /api/demo/all, /api/demo/feedback, /api/demo/feedback-pending
### History: /api/history/search, /api/history/student/{id}, /api/history/teacher/{id}, /api/history/users
### Notifications: /api/notifications/my, /api/notifications/mark-read/{id}, /api/notifications/mark-all-read
### Payments: /api/payments/checkout, /api/webhook/stripe

## DB Collections
- users, user_sessions, class_sessions, student_teacher_assignments, transactions, payment_transactions
- complaints, class_proofs, feedback, notifications, system_pricing
- demo_requests, demo_extras, demo_feedback, history_logs (NEW)

## Remaining Backlog
- P1: Nag screens/popups for unassigned students ("Start your regular classes")
- P2: Email notifications for demo acceptance (currently in-app only)
- P2: Jitsi screenshot fix (use captureLargeVideoScreenshot API)
- P3: Complete migration of server.py into modular route files
- P3: Real-time notifications (WebSocket push instead of polling)
