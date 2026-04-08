# Kaimera Learning - EdTech CRM Platform PRD

## Original Problem Statement
Complete EdTech CRM/Management Platform with 4 roles: Admin, Counsellor, Teacher, Student.
Flow: Counsellor assigns Student -> Teacher approves -> Teacher creates class -> Video (Jitsi) -> Proofs -> Admin approves & credits teacher.

## Tech Stack
- Frontend: React + Shadcn/UI + Tailwind CSS + Recharts (charts)
- Backend: FastAPI (Python)
- Database: MongoDB (Motor async driver)
- Auth: Session-based + Emergent Google OAuth
- Payments: Stripe (test key, webhook handling)
- Video: Jitsi Meet (free, CDN-loaded)
- Email: Resend API (transactional emails)

## Implemented Features

### Core CRM (DONE)
- 4-role system with session auth + Google OAuth
- Admin: create teachers/counsellors/students, set global pricing, approve teachers, adjust credits
- Counsellor: assign students, view profiles, verify proofs, manage complaints
- Teacher: approve students, create classes, grouped student view, submit proofs
- Student: view classes, cancel sessions, edit profile, file complaints

### Admin Credential Management (DONE - Apr 8, 2026)
- **Create Teacher Login**: Name/email/password form, shows credentials + teacher_code after creation
- **Create Counsellor Login**: Name/email/password form, shows credentials after creation
- **Reset Password**: Admin resets any user's password by email
- **Block/Unblock Users**: Admin can block accounts (blocked users get 403 on login, sessions invalidated)
- **Delete Users**: Permanent deletion with double-confirm (admin accounts protected)
- **User Search**: Search all users by name/email/ID with Block/Delete inline actions
- **User Detail Dialog**: Shows email prominently, assignments, classes, transactions, Block/Delete actions

### Counsellor Tracking with Bar Chart (DONE - Apr 8, 2026)
- Counsellor tracking tab shows assignment statistics per counsellor
- "View Daily Stats" button expands a Recharts bar chart showing:
  - Daily leads/demos handled
  - Daily allotments made
  - Daily sessions/proofs processed
- Backend endpoint `/admin/counsellor-daily-stats/{id}` aggregates data from assignments and history_logs

### Wallet Color Fix (DONE - Apr 8, 2026)
- Transaction amounts now stored with correct sign: positive for credits, negative for debits
- WalletPage uses `amount > 0` for green `+`, negative for red `-`
- admin credit_add = positive, credit_deduct = negative, auto_booking = negative

### History Search Fix (DONE - Apr 8, 2026)
- `/api/history/search` now searches across `history_logs`, `student_teacher_assignments`, and `demo_requests`
- Returns combined results sorted by date

### Counsellor Rejected Student Reassignment (DONE - Apr 8, 2026)
- Rejected assignment cards now show "Reassign to Another Teacher" button
- Opens the assign dialog pre-filled with the student

### Counsellor "All Students" Search (DONE - Apr 8, 2026)
- Added search bar to CounsellorStudents.js
- Filters by name, email, student_code, phone, institute, city

### Teacher Dashboard UI Overhaul (DONE - Apr 8, 2026)
- "Classes of the Day" section, grouped-by-student view, student search, "Schedule Planner"

### Badge Templates (DONE - Apr 8, 2026)
- Create/delete badge templates, assign from dropdown

### Per-Class Student Wallet Deduction (DONE - existing)
- `class_price_student` set by admin in system pricing
- Auto-deducted from student wallet when teacher creates a class for them

### Other Completed Features
- Demo Booking Flow (live sheet, feedback, auto-class creation)
- Video Integration (Jitsi Meet)
- Learning Kit System (grade-based PDFs)
- Email Notifications (Resend)
- Teacher Calendar / Schedule Planner
- Nag Screens for unassigned students
- Auto teacher_code / student_code generation
- Proof Pipeline: Teacher -> Counsellor -> Admin -> Wallet credit
- Cancel class day (max 3, day extension)
- Complaints system
- Notification system with bell icon
- Stripe payment webhook handling
- Renewal detection (80% threshold)

## Key API Endpoints
- Auth: /api/auth/register, login, session, me, logout
- Admin: /api/admin/create-teacher, create-counsellor, create-student
- Admin: /api/admin/block-user, delete-user, reset-password
- Admin: /api/admin/counsellor-tracking, counsellor-daily-stats/{id}
- Admin: /api/admin/all-users, user-detail/{id}
- Admin: /api/admin/badge-template(s), assign-badge
- Demo: /api/demo/request, live-sheet, accept, assign, feedback
- Search: /api/search/teachers, history/search, filter/classes, filter/students
- Wallet: /api/wallet/summary
- Proof Pipeline: teacher/submit-proof -> counsellor/verify-proof -> admin/approve-proof
- Classes: /api/classes/create, /api/teacher/grouped-classes
- Learning Kit: /api/admin/learning-kit/upload, /api/learning-kit
- Calendar: /api/teacher/calendar
- Notifications: /api/notifications/my, mark-all-read

## DB Collections
users, user_sessions, class_sessions, student_teacher_assignments, transactions, payment_transactions,
complaints, class_proofs, feedback, notifications, system_pricing,
demo_requests, demo_extras, demo_feedback, history_logs,
teacher_student_feedback, renewal_meetings, counters,
learning_kits, teacher_calendar, badge_templates

## Remaining Backlog
- P2: Jitsi screenshot fix (use captureLargeVideoScreenshot API)
- P2: Verify Resend domain for production email delivery
- P3: Modular refactor of server.py into route files
- P3: Real-time notifications (WebSocket push)
- P3: Student progress reports (PDF generation)
