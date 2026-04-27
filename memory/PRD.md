# Kaimera Learning - Product Requirements Document

## Original Problem Statement
EdTech CRM/Management Platform with roles: Admin, Counselor, Teacher, Student. Wallet-based credits, Razorpay integration, Counselor dashboard, Teacher schedule management, class proofs with screenshots, complaint system, Video integration (Jitsi), Demo Booking & Tracking workflow, Email Notifications, Global Financial Controls, Conditional Student UI Lockdown.

## Architecture
- **Frontend**: React + Shadcn/UI + Tailwind CSS
- **Backend**: FastAPI (modular routes)
- **Database**: MongoDB Atlas (`mongodb+srv://...@cluster0.oxrrozs.mongodb.net/`) — use local MongoDB if Atlas IP not whitelisted
- **Video**: Jitsi Meet API
- **Auth**: Cookie-based sessions + Google OAuth (manual GIS script, on-demand)
- **Payments**: Razorpay (on-demand script loading, no npm package)
- **Email**: Resend (OTP verification)
- **PDF**: fpdf2 (receipt generation)

## Code Structure
```
/app/backend/
  server.py, database.py
  models/schemas.py
  services/auth.py, helpers.py, rating.py
  tasks/background.py
  routes/admin.py, auth.py, chat.py, classes.py, counsellor.py, demo.py, general.py, payments.py, student.py, teacher.py, attendance.py
/app/frontend/src/
  components/ (ViewProfilePopup.js, ui/)
  pages/ (*Dashboard.js, *Profile.js, Login.js, WalletPage.js, BrowseClasses.js)
  utils/api.js
```

## Completed Features

### Deployment & API Routing (Feb 2026)
- Refactored ALL 26 frontend files to use relative `/api` paths via centralized `utils/api.js`
- Eliminated hardcoded `REACT_APP_BACKEND_URL` from all source files — deployed app now routes API calls to its own domain
- Fixed password_hash leak in `/api/auth/login` and `/api/auth/me` responses

### Assignment Visibility Fix (Feb 2026)
- Fixed "disappearing assignment" bug: after teacher accepts a student, the assignment was invisible on both teacher and student dashboards
- Root cause: Teacher dashboard only showed approved students with payment_status="paid", creating a gap for "approved but awaiting payment" assignments
- Added `awaiting_payment` array to teacher dashboard API and new "Awaiting Student Payment" UI section
- Fixed legacy data: patched assignments missing the payment_status field

### Start Class Button Fix & Learning Plan Max Days (Feb 2026)
- Fixed teacher not seeing "Start Class" button — was restricted to "Today" tab only, now shows for all scheduled classes
- Added `max_days` field to Learning Plans — admin sets max days, counselor assignment auto-locks to that limit
- Backend enforces: rejects assignment if assigned_days > plan's max_days, auto-fills from plan if not provided

### Cancelled Classes, Auto-Refund, Wallet Payment, Proof Fix (Feb 2026)
- Separated cancelled classes into their own tab/section on both Teacher and Student dashboards
- Auto-refund: when teacher cancels ALL classes for an assignment, the Razorpay payment is refunded to student wallet
- Payment choice: students now choose between "Pay from Wallet" or "Pay via Razorpay" instead of going straight to Razorpay
- New endpoint: POST /api/payments/pay-from-wallet (deducts wallet credits, marks assignment paid)

### Per-Day Proof, Reschedule on Cancel, Counsellor Visibility (Feb 2026)
- Proof is now per-day for multi-day classes — teacher submits proof after each session, not in bulk
- Teacher can reschedule cancelled classes (not just student-cancelled sessions) with no reschedule limit
- Reschedule reactivates the class with new date/time and notifies the student
- Counsellor can see who cancelled each class and whether it was rescheduled (with count and new date)

### Refund Loophole Fix, End-Date Shift, Smart Attendance (Feb 2026)
- Fixed refund loophole: when teacher reschedules a cancelled class, the credit refund is reversed (re-charged). Full assignment refunds also reversed.
- Each reschedule extends class end_date by 1 extra day to account for the lost session
- Attendance on non-class day: backend detects no scheduled class and asks teacher "why?" (forgot/rescheduled) + which class it's for. Records off_day_marking, reason, class_id
- Counsellor can view full attendance history per student including off-day markings and reasons (new endpoint)

### Session-Level Cancel & Mandatory Reschedule (Feb 2026)
- Teacher cancel now only cancels TODAY's session, NOT the entire class. Class stays active, end_date shifts +1 day
- needs_reschedule flag blocks starting next session until teacher reschedules
- Reschedule updates timings for all remaining days, clears the block
- Teacher doesn't need to recreate the class — just reschedule the postponed session
- Admin can configure rating deduction per cancellation via Financials > Teacher Cancellation Penalty

### Zoom Integration & Error Notifications (Feb 2026)
- Replaced Jitsi with Zoom Meeting SDK. Backend creates Zoom meetings via Server-to-Server OAuth API
- Frontend VideoClass.js uses embedded Zoom Component View with SDK signature authentication
- Screenshot button (teacher-only) captures screen showing both teacher and student via Screen Capture API
- Fallback: if embedded Zoom fails, opens Zoom join URL in new tab
- Global error handlers: DB errors return 503, unhandled exceptions return 500 with type info
- Login error: shows "Invalid email or password" instead of body stream errors
- All error toasts now show human-readable messages based on HTTP status codes

### Per-Class Per-Day Attendance System (Feb 2026)
- Attendance is now tied to specific classes (class_id + date), not just student + date
- Once marked for a class on a date, cannot be changed (409 Conflict)
- Auto-detects which class covers today's date; if no class, asks teacher to select one
- GET /attendance/unmarked shows past days with missing attendance per class
- GET /attendance/class-today/{student_id} shows today's classes with already_marked flag
- Frontend shows unmarked past-day warnings, per-class Present/Absent buttons that disable after marking
- Attendance history shows class title + date + status + notes

### Counsellor Attendance View & Mid-Class Transfer (Feb 2026)
- Counsellor/Admin can view student attendance history filtered by class (dropdown selector)
- GET /counsellor/student-attendance/{id} returns {records, classes} for dropdown
- New POST /counsellor/transfer-student: transfers student mid-class to another teacher
- Transfer: old classes marked 'transferred', new assignment created with remaining days, old teacher rating deducted
- Notifications sent to old teacher, new teacher, and student on transfer

### Completion Rating Boost (Feb 2026)
- When teacher completes all assigned classes AND all proofs are approved by admin, rating is boosted
- Admin-configurable `completion_rating_boost` (default 0.1) in Financials settings
- Boost accumulates with each successful completion but total rating CANNOT exceed 5.0
- Rating formula: avg_feedback + (completions * boost) - (cancellations * deduction) - (transfers * deduction) - (bad_feedbacks * 0.3)

### Time-Based Class Controls & Admin-Only Delete (Feb 2026)
- Start Class button only active 5 min before class start_time, faded/disabled before that
- After end_time passes: Start Class disappears, class auto-cancelled, Submit Proof appears
- Cancel Today's Session only visible before class starts (not after live or after time ends)
- Delete class: admin-only (teachers cannot delete classes anymore)
- Proof submission auto-captures meeting duration (calculated from last_started_at to submit time)
- Meeting duration shown to counsellor in proof review (teacher cannot modify it)

### Session-Based Completion & Admin/Counsellor Class Detail View (Feb 2026)
- Classes track sessions_conducted separately — only successful completions count toward the total
- If student has 3-day class, exactly 3 sessions must be conducted (cancels/reschedules don't count)
- End date keeps extending until all sessions are done
- Auto-cancel records in session_history with reason "Teacher did not start before end time"
- Admin/Counsellor: GET /admin/teacher-classes/{id} — clickable list of all teacher's classes with summary stats
- Admin/Counsellor: GET /admin/class-detail/{id} — full timeline: session history, attendance, proofs, meeting duration
- Classes are expandable (not cluttered) — click to see full detail with color-coded timeline

### Dashboard Organization, Finish Flow & Class Guards (Feb 2026)
- Teacher dashboard: Students as expandable cards — click to see per-student attendance, classes, history
- Per-student attendance: each student has their own attendance isolated (not one combined table)
- "Mark Finish": Counsellor marks student as finished → removed from teacher & counsellor dashboards, only admin retains records
- Class creation guard: teacher can only create class for PAID students without active/scheduled classes
- Admin delete class: notifies teacher when admin deletes their class
- Teacher student detail endpoint: GET /teacher/student-detail/{id} returns per-student classes, attendance, has_active_class flag

### Demo Limits, OTP Fix, Calendar, Wallet (Feb 2026)
- Demo reassignment capped at 3 attempts — after 3 demos without conversion, student disappears from reassignment area
- Students who paid for class assignment disappear from demo reassignment (demo successful)
- After all classes finished, student can book demo again for new classes
- OTP fix: Resend API key was not loading (same lazy-load issue as Zoom) — now loads at runtime
- Teacher schedule calendar: includes completed classes, excludes finished/cancelled
- Recharge button hidden on teacher wallet (teachers earn, not recharge)

### Auth & Environment
- MongoDB Atlas connection (configurable via .env)
- Google OAuth (on-demand GIS script, no iframe pre-loading)
- @gmail.com only validation for manual user creation
- OTP verification for manually created users
- Self-registration with OTP email verification
- Removed @react-oauth/google and react-razorpay npm packages (fixes postMessage error)

### Learning Plans
- Admin CRUD for Learning Plans (name, price, details/syllabus)
- Counselor must select Learning Plan when assigning student

### Razorpay Payments
- Credit recharge: INR 2,000 / 5,000 / 10,000
- Assignment payment flow: Counselor assigns → Teacher accepts → Student sees "Unpaid" → Pay via Razorpay → "Paid"
- Teacher can only start class if student payment verified
- PDF receipt generation (fpdf2) with download from Wallet page
- Admin Razorpay Payments tab with filters
- Webhook handler for payment.captured

### Attendance
- Teacher marks daily attendance (present/absent/late)
- Attendance History for teacher and student

### Proof Guardrail
- Teacher can submit proof after class ends
- Counselor blocked from assigning if previous proof pending

### Previous Features
- Full role-based dashboards, Demo-first workflow, Jitsi video, Teacher rating/suspension, Scoped chat, Single-device sessions, KLAT/KL-CAT scoring, PDF resume upload, Class proofs, Complaint system, Notifications, Financial controls, ViewProfilePopup, Auto-refresh on tab focus

## Backlog
### P2
- Verify Resend domain for production email
- Google OAuth origin whitelisting for production domain
### P3
- Real-time WebSocket notifications/chat
- Student progress PDF reports
