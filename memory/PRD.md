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
