# Kaimera Learning - EdTech CRM Platform PRD

## Original Problem Statement
Complete EdTech CRM/Management Platform with 4 roles: Admin, Counsellor, Teacher, Student.
Admin creates student accounts manually. Counsellor assigns students to teachers. Teacher approves, creates classes with live video (Jitsi Meet). Classes show on weekly view. Teacher can start/end class, take screenshots. Student joins only when teacher starts.

## Tech Stack
- Frontend: React + Shadcn/UI + Tailwind CSS
- Backend: FastAPI (Python)
- Database: MongoDB (Motor async driver)
- Auth: Session-based + Emergent Google OAuth
- Payments: Stripe (test key, webhook handling)
- Video: Jitsi Meet (free, CDN-loaded)

## Core Workflow
1. Admin creates student account → shares credentials
2. Counsellor assigns student to teacher with custom price
3. Teacher approves assignment
4. Teacher creates class → auto-enrollment + credit deduction
5. Teacher starts class → Jitsi room opens, student gets notification
6. Student joins live class → video room
7. Teacher takes screenshots during class → saved to device
8. Teacher ends class → status resets (or completes if last day)
9. Student can cancel class day (max 3, then dismissed)
10. Teacher submits proof → Counsellor verifies → Teacher earns credits

## Implemented Features

### Core CRM (DONE)
- 4-role system, session auth + Google OAuth
- Admin: create teachers/counsellors/students, set pricing, approve teachers, adjust credits
- Counsellor: assign students, view profiles, verify proofs, manage complaints
- Teacher: approve students, create classes (1:1/group, demo/regular), weekly class view
- Student: view classes, cancel sessions, edit profile, file complaints

### Video Integration - Jitsi Meet (DONE)
- Teacher starts class → Jitsi Meet room auto-created per class
- Student sees "Join Live Class Now" button (only when teacher has started)
- Student sees "Waiting for teacher..." screen when class not started
- Screenshot capture: screen capture API + html2canvas fallback → downloads PNG
- Teacher ends class → room closes, status resets
- Live indicator on class cards (LIVE badge + pulse animation)

### Teacher Dashboard Week View (DONE)
- Main screen: "This Week's Classes" - only shows classes overlapping current week
- Collapsible "Other Classes" panel for past/future classes
- Start Class button navigates to video room
- Student complaint section at top

### Teacher Schedule Calendar (DONE)
- Calendar shows date ranges for multi-day classes
- Status labels: BOOKED (scheduled), LIVE (in_progress), DONE (completed), OFF (dismissed)
- Color-coded: sky=booked, emerald=live, slate=done, red=dismissed

### Class Cancellation System (DONE)
- Student cancels day → extends class by 1 day, teacher notified
- Max 3 cancellations → class dismissed
- No Join/Cancel Booking buttons (replaced with Cancel Today's Session)

### Complaint Visibility (DONE)
- Student complaints auto-link to assigned teacher
- Teachers see ONLY their students' complaints
- Counsellors see ALL complaints, Admin can resolve

### Notification System (DONE)
- Teacher bell with unread count
- Triggers: class cancellations, dismissals, complaints, class started (to student)

### Stripe Payment (DONE)
- Checkout session with credit packages
- Webhook handler: verifies payment → credits user account → creates transaction record

### Backend Modular Structure (DONE)
- database.py: DB connection module
- auth_utils.py: Auth utilities and User model
- models/schemas.py: All Pydantic models
- routes/: Router package (ready for full migration)
- server.py: Monolith (still primary, gradual migration path)

## API Endpoints
### Auth: /api/auth/register, /api/auth/login, /api/auth/session, /api/auth/me, /api/auth/logout
### Student: /api/student/dashboard, /api/student/update-profile, /api/classes/browse, /api/classes/cancel-day/{id}
### Teacher: /api/teacher/dashboard, /api/teacher/approve-assignment, /api/teacher/submit-proof, /api/teacher/my-proofs, /api/teacher/student-complaints
### Classes: /api/classes/create, /api/classes/start/{id}, /api/classes/end/{id}, /api/classes/status/{id}, /api/classes/delete/{id}
### Counsellor: /api/counsellor/dashboard, /api/counsellor/student-profile/{id}, /api/counsellor/pending-proofs, /api/counsellor/all-proofs, /api/counsellor/verify-proof, /api/counsellor/expired-classes
### Admin: /api/admin/create-student, /api/admin/create-teacher, /api/admin/create-counsellor, /api/admin/set-pricing, /api/admin/approve-teacher, /api/admin/adjust-credits, /api/admin/complaints, /api/admin/resolve-complaint
### Notifications: /api/notifications/my, /api/notifications/mark-read/{id}, /api/notifications/mark-all-read
### Payments: /api/payments/checkout, /api/webhook/stripe

## Remaining Backlog
- P3: Complete migration of server.py into modular route files
- P3: Real-time notifications (WebSocket push instead of polling)
