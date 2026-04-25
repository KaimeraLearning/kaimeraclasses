# Kaimera Learning - Product Requirements Document

## Original Problem Statement
EdTech CRM/Management Platform with roles: Admin, Counselor, Teacher, Student. Wallet-based credits, Razorpay integration, Counselor dashboard, Teacher schedule management, class proofs with screenshots, complaint system, Video integration (Jitsi), Demo Booking & Tracking workflow, Email Notifications, Global Financial Controls, Conditional Student UI Lockdown.

## Architecture
- **Frontend**: React + Shadcn/UI + Tailwind CSS
- **Backend**: FastAPI (modular routes)
- **Database**: MongoDB Atlas (`mongodb+srv://...@cluster0.oxrrozs.mongodb.net/`)
- **Video**: Jitsi Meet API
- **Auth**: Cookie-based sessions + Google OAuth (user's own Client ID)
- **Payments**: Razorpay (live keys)
- **Email**: Resend (OTP verification)

## Code Structure
```
/app/backend/
  server.py, database.py
  models/schemas.py (includes LearningPlan, AssignStudentToTeacher with learning_plan_id)
  services/auth.py, helpers.py, rating.py
  tasks/background.py
  routes/admin.py, auth.py, chat.py, classes.py, counsellor.py, demo.py, general.py, payments.py, student.py, teacher.py, attendance.py
/app/frontend/src/
  components/ (ViewProfilePopup.js, ui/)
  pages/ (*Dashboard.js, *Profile.js, Login.js)
  utils/api.js
```

## Spelling Convention
- Internal: `counsellor` (DB, API paths, filenames)
- User-facing: `Counselor`

## Completed Features (as of Feb 2026)
### Phase 1 - Environment & Auth
- MongoDB Atlas connection (user's own cluster)
- Google OAuth with user's Client ID (popup-based)
- @gmail.com only validation for manual user creation
- OTP verification for manually created users (sends email via Resend)
- Account verification flow at login for unverified users
- Self-registration with OTP email verification

### Phase 2 - Learning Plans
- Admin CRUD for Learning Plans (name, price, details/syllabus)
- Learning Plan tab in Admin Dashboard
- Counselor must select a Learning Plan when assigning student to teacher

### Phase 3 - Razorpay Payments
- Replaced Stripe with Razorpay (live keys)
- Payment flow: Counselor assigns → Teacher approves → Student sees "Unpaid" → Student pays via Razorpay → "Paid"
- Teacher only sees students with payment_status = "paid"
- Student dashboard shows "Payment Required" with Pay Now button
- Admin "Razorpay Payments" sub-tab with filters (student name, date range)
- Automated receipt generation
- Webhook handler for payment.captured events

### Phase 4 - Attendance
- Teacher marks daily attendance (present/absent/late) per student
- Attendance History for teacher and student
- One-click attendance buttons on teacher dashboard
- Attendance dialog with date/student/status table

### Phase 5 - Proof Guardrail
- Teacher can submit proof after class ends (no time restriction)
- Counselor blocked from assigning if previous class proof is pending
- Clear error message: "Cannot assign: Proof of completion for the previous session is still pending from the Teacher."

### Previous Features (carried over)
- Full role-based dashboards (Admin, Teacher, Student, Counselor)
- Demo-first enrollment workflow
- Jitsi video class integration
- Teacher rating & penalty/suspension system
- Permission-based scoped chat
- Single-device session enforcement
- KLAT/KL-CAT scoring + PDF resume upload
- Class proofs with screenshot upload
- Complaint system, Notification system
- Global dynamic financial controls
- ViewProfilePopup across all dashboards
- Auto-refresh on tab focus for all dashboards

## Backlog
### P2
- Verify Resend domain for production email
- Google OAuth origin whitelisting for production domain

### P3
- Real-time WebSocket notifications/chat
- Student progress PDF reports
