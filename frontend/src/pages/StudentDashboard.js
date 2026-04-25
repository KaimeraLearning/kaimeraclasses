import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { toast } from 'sonner';
import { GraduationCap, LogOut, Calendar, CreditCard, BookOpen, Play, MessageSquare, Bell, AlertCircle, Lock, Star, Clock, User, XCircle, IndianRupee, Download, CheckCircle } from 'lucide-react';
import { getApiError } from '../utils/api';
import { ViewProfilePopup } from '../components/ViewProfilePopup';
import { useRazorpay } from 'react-razorpay';

const BACKEND = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND}/api`;

const StudentDashboard = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [classes, setClasses] = useState([]);
  const [liveClasses, setLiveClasses] = useState([]);
  const [upcomingClasses, setUpcomingClasses] = useState([]);
  const [completedClasses, setCompletedClasses] = useState([]);
  const [pendingRating, setPendingRating] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [enrollment, setEnrollment] = useState(null);
  const [demoFeedbacks, setDemoFeedbacks] = useState([]);
  const [showNotifDialog, setShowNotifDialog] = useState(false);
  const [showProfileDialog, setShowProfileDialog] = useState(false);
  const [showFeedbackDialog, setShowFeedbackDialog] = useState(false);
  const [showRatingDialog, setShowRatingDialog] = useState(false);
  const [ratingTarget, setRatingTarget] = useState(null);
  const [ratingForm, setRatingForm] = useState({ rating: 5, comments: '' });
  const [profileForm, setProfileForm] = useState({});
  const [viewProfileOpen, setViewProfileOpen] = useState(false);
  const [viewProfileUserId, setViewProfileUserId] = useState(null);
  const [viewProfileRole, setViewProfileRole] = useState(null);
  const [assignments, setAssignments] = useState([]);
  const [paymentLoading, setPaymentLoading] = useState(false);
  const { Razorpay: RazorpayCheckout } = useRazorpay();
  const [attendanceRecords, setAttendanceRecords] = useState([]);
  const [showAttendanceDialog, setShowAttendanceDialog] = useState(false);

  const openProfile = (userId, role) => { setViewProfileUserId(userId); setViewProfileRole(role); setViewProfileOpen(true); };

  useEffect(() => { fetchData(); }, []);

  // Auto-refresh on tab focus
  useEffect(() => {
    const handleVisibility = () => { if (document.visibilityState === 'visible') fetchData(); };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => document.removeEventListener('visibilitychange', handleVisibility);
  }, []);

  const fetchData = async () => {
    try {
      const [userRes, dashRes, notifRes, enrollRes, feedbackRes] = await Promise.all([
        fetch(`${API}/auth/me`, { credentials: 'include' }),
        fetch(`${API}/student/dashboard`, { credentials: 'include' }),
        fetch(`${API}/notifications/my`, { credentials: 'include' }),
        fetch(`${API}/student/enrollment-status`, { credentials: 'include' }),
        fetch(`${API}/student/demo-feedback-received`, { credentials: 'include' })
      ]);
      if (!userRes.ok) throw new Error();
      const userData = await userRes.json();
      setUser(userData);
      setProfileForm({ state: userData.state || '', city: userData.city || '', country: userData.country || '', grade: userData.grade || '', phone: userData.phone || '', institute: userData.institute || '', goal: userData.goal || '', preferred_time_slot: userData.preferred_time_slot || '' });
      if (dashRes.ok) {
        const d = await dashRes.json();
        setClasses(d.live_classes || []);
        setLiveClasses(d.live_classes || []);
        setUpcomingClasses(d.upcoming_classes || []);
        setCompletedClasses(d.completed_classes || []);
        setPendingRating(d.pending_rating || []);
        setAssignments(d.assignments || []);
      }
      if (notifRes.ok) setNotifications(await notifRes.json());
      if (enrollRes.ok) setEnrollment(await enrollRes.json());
      if (feedbackRes.ok) setDemoFeedbacks(await feedbackRes.json());
    } catch { toast.error('Failed to load dashboard'); }
    setLoading(false);
  };

  const handleLogout = async () => { await fetch(`${API}/auth/logout`, { method: 'POST', credentials: 'include' }); navigate('/login'); };
  const handleMarkAllRead = async () => { await fetch(`${API}/notifications/mark-all-read`, { method: 'POST', credentials: 'include' }); fetchData(); };
  const unreadCount = notifications.filter(n => !n.read).length;

  const fetchAttendance = async () => {
    try {
      const res = await fetch(`${API}/attendance/student`, { credentials: 'include' });
      if (res.ok) { setAttendanceRecords(await res.json()); setShowAttendanceDialog(true); }
    } catch {}
  };

  const handlePayNow = async (assignmentId) => {
    setPaymentLoading(true);
    try {
      const res = await fetch(`${API}/payments/create-order`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ assignment_id: assignmentId })
      });
      if (!res.ok) throw new Error(await getApiError(res));
      const data = await res.json();

      const options = {
        key: data.key_id,
        amount: data.amount,
        currency: data.currency,
        order_id: data.order_id,
        name: 'Kaimera Learning',
        description: 'Learning Plan Payment',
        prefill: { name: data.student_name, email: data.student_email },
        handler: async (response) => {
          try {
            const verifyRes = await fetch(`${API}/payments/verify`, {
              method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                razorpay_order_id: response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature: response.razorpay_signature
              })
            });
            if (!verifyRes.ok) throw new Error(await getApiError(verifyRes));
            toast.success('Payment successful! Your classes will begin soon.');
            fetchData();
          } catch (err) { toast.error('Payment verification failed: ' + err.message); }
        },
        theme: { color: '#0ea5e9' }
      };

      const rzp = new RazorpayCheckout(options);
      rzp.open();
    } catch (err) { toast.error(err.message); }
    finally { setPaymentLoading(false); }
  };

  const handleUpdateProfile = async () => {
    try {
      const res = await fetch(`${API}/student/update-profile`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(profileForm)
      });
      if (!res.ok) throw new Error(await getApiError(res));
      toast.success('Profile updated!');
      setShowProfileDialog(false);
      fetchData();
    } catch (err) { toast.error(err.message); }
  };

  const handleCancelSession = async (classId) => {
    if (!window.confirm("Cancel today's session? Your teacher will reschedule.")) return;
    try {
      const res = await fetch(`${API}/classes/cancel-session/${classId}`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      if (!res.ok) throw new Error(await getApiError(res));
      toast.success("Session cancelled. Teacher will reschedule.");
      fetchData();
    } catch (err) { toast.error(err.message); }
  };

  const handleSubmitRating = async () => {
    if (!ratingForm.comments) { toast.error('Please enter comments'); return; }
    try {
      const res = await fetch(`${API}/student/rate-class`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ class_id: ratingTarget.class_id, rating: ratingForm.rating, comments: ratingForm.comments })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      toast.success('Rating submitted!');
      setShowRatingDialog(false); setRatingTarget(null);
      setRatingForm({ rating: 5, comments: '' });
      fetchData();
    } catch (err) { toast.error(err.message); }
  };

  if (loading) return <div className="min-h-screen flex items-center justify-center bg-slate-50"><div className="w-16 h-16 border-4 border-sky-500 border-t-transparent rounded-full animate-spin" /></div>;

  const isEnrolled = enrollment?.is_enrolled;
  const demoCompleted = enrollment?.demo_completed;
  const hasTeacher = enrollment?.has_approved_teacher;

  // ─── LOCKED VIEW (not enrolled) ───
  if (!isEnrolled) {
    // Demo classes the student can join
    const demoLiveClasses = liveClasses.filter(c => c.is_demo);
    const demoUpcoming = upcomingClasses.filter(c => c.is_demo);
    const hasDemoClasses = demoLiveClasses.length > 0 || demoUpcoming.length > 0;

    return (
      <div className="min-h-screen bg-slate-50">
        <header className="sticky top-0 z-50 backdrop-blur-xl bg-white/80 border-b border-slate-200">
          <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <GraduationCap className="w-9 h-9 text-sky-500" strokeWidth={2.5} />
              <h1 className="text-xl font-bold text-slate-900">Student Dashboard</h1>
            </div>
            <div className="flex items-center gap-3">
              <button onClick={() => setShowNotifDialog(true)} className="relative p-2 rounded-full hover:bg-slate-100" data-testid="notifications-bell">
                <Bell className="w-5 h-5 text-slate-700" />
                {unreadCount > 0 && <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center font-bold">{unreadCount}</span>}
              </button>
              <span className="text-sm font-medium text-slate-700">{user?.name}</span>
              <Button onClick={handleLogout} variant="outline" size="sm" className="rounded-full" data-testid="logout-button"><LogOut className="w-3 h-3" /></Button>
            </div>
          </div>
        </header>

        <div className="max-w-2xl mx-auto px-4 py-12">
          {/* Locked banner */}
          <div className="bg-white rounded-3xl border-2 border-amber-200 p-8 text-center mb-6" data-testid="locked-banner">
            <Lock className="w-16 h-16 text-amber-500 mx-auto mb-4" />
            <h2 className="text-2xl font-bold text-slate-900 mb-2">Welcome, {user?.name}!</h2>
            <p className="text-slate-600 mb-4">
              {!demoCompleted
                ? "You're not enrolled yet. Book a free demo to get started!"
                : hasTeacher
                  ? "Your teacher enrollment is being processed. Hang tight!"
                  : "Your demo is complete! A counselor will assign you to a teacher soon."}
            </p>
            <div className="flex flex-wrap gap-3 justify-center">
              {!demoCompleted && (
                <Button onClick={() => navigate('/book-demo')} className="bg-amber-400 hover:bg-amber-500 text-slate-900 rounded-full px-8 py-6 font-bold text-lg" data-testid="book-demo-button">Book a Free Demo</Button>
              )}
              <Button onClick={() => setShowProfileDialog(true)} variant="outline" className="rounded-full px-6 py-6" data-testid="edit-profile-button"><User className="w-4 h-4 mr-2" /> My Profile</Button>
              <Button onClick={() => navigate('/wallet')} variant="outline" className="rounded-full px-6 py-6" data-testid="wallet-button"><CreditCard className="w-4 h-4 mr-2" /> Wallet</Button>
              <Button onClick={() => navigate('/chat')} variant="outline" className="rounded-full px-6 py-6" data-testid="chat-button"><MessageSquare className="w-4 h-4 mr-2" /> Chat</Button>
              <Button onClick={fetchAttendance} variant="outline" className="rounded-full px-6 py-6" data-testid="attendance-history-btn"><Calendar className="w-4 h-4 mr-2" /> Attendance</Button>
            </div>
          </div>

          {/* DEMO LIVE CLASSES - Join button */}
          {demoLiveClasses.length > 0 && (
            <div className="mb-6">
              <h3 className="text-lg font-bold text-emerald-700 mb-3 flex items-center gap-2"><Play className="w-5 h-5 text-emerald-500" /> Your Demo Class - Live Now</h3>
              {demoLiveClasses.map(cls => (
                <div key={cls.class_id} className="bg-white rounded-2xl border-2 border-emerald-400 p-5 ring-2 ring-emerald-200 mb-3" data-testid={`demo-live-${cls.class_id}`}>
                  <div className="flex gap-2 mb-2">
                    <span className="bg-emerald-500 text-white px-2 py-0.5 rounded-full text-xs font-semibold animate-pulse">LIVE</span>
                    <span className="bg-violet-100 text-violet-800 px-2 py-0.5 rounded-full text-xs">DEMO</span>
                  </div>
                  <h4 className="font-bold text-slate-900 mb-1">{cls.title}</h4>
                  <p className="text-xs text-slate-600 mb-3">{cls.start_time} - {cls.end_time} | Teacher: <button onClick={(e) => { e.stopPropagation(); openProfile(cls.teacher_id, 'teacher'); }} className="text-sky-600 hover:underline font-semibold cursor-pointer">{cls.teacher_name}</button></p>
                  <Button onClick={() => navigate(`/class/${cls.class_id}`)} className="w-full bg-emerald-500 hover:bg-emerald-600 text-white rounded-full font-bold animate-pulse" data-testid={`join-demo-live-${cls.class_id}`}>
                    <Play className="w-4 h-4 mr-2" /> Join Demo Class
                  </Button>
                </div>
              ))}
            </div>
          )}

          {/* DEMO UPCOMING CLASSES */}
          {demoUpcoming.length > 0 && (
            <div className="mb-6">
              <h3 className="text-lg font-bold text-sky-700 mb-3 flex items-center gap-2"><Calendar className="w-5 h-5 text-sky-500" /> Upcoming Demo</h3>
              {demoUpcoming.map(cls => (
                <div key={cls.class_id} className="bg-white rounded-2xl border border-sky-200 p-5 mb-3" data-testid={`demo-upcoming-${cls.class_id}`}>
                  <div className="flex gap-2 mb-2">
                    <span className="bg-sky-100 text-sky-800 px-2 py-0.5 rounded-full text-xs font-semibold">SCHEDULED</span>
                    <span className="bg-violet-100 text-violet-800 px-2 py-0.5 rounded-full text-xs">DEMO</span>
                  </div>
                  <h4 className="font-bold text-slate-900 mb-1">{cls.title}</h4>
                  <p className="text-xs text-slate-600">Date: {cls.date} | {cls.start_time} - {cls.end_time} | Teacher: <button onClick={(e) => { e.stopPropagation(); openProfile(cls.teacher_id, 'teacher'); }} className="text-sky-600 hover:underline font-semibold cursor-pointer">{cls.teacher_name}</button></p>
                </div>
              ))}
            </div>
          )}

          {/* Demo Feedbacks */}
          {demoFeedbacks.length > 0 && (
            <div className="bg-white rounded-3xl border-2 border-sky-100 p-6 mb-6">
              <h3 className="font-bold text-slate-900 mb-3 flex items-center gap-2"><Star className="w-5 h-5 text-amber-500" /> Demo Feedback</h3>
              {demoFeedbacks.map((fb, i) => (
                <div key={i} className="bg-sky-50 rounded-xl p-4 border border-sky-200 mb-2" data-testid={`demo-feedback-${i}`}>
                  <div className="flex justify-between mb-1">
                    <p className="text-sm font-semibold text-slate-900">Teacher: {fb.teacher_name || 'Unknown'}</p>
                    <span className="text-xs text-slate-500">{fb.created_at?.slice(0, 10)}</span>
                  </div>
                  <p className="text-sm text-slate-600">{fb.feedback || fb.feedback_text || fb.notes || 'No detailed feedback'}</p>
                  {fb.rating && <p className="text-xs text-amber-600 mt-1 font-semibold">Rating: {fb.rating}</p>}
                </div>
              ))}
            </div>
          )}

          {/* Notifications */}
          {notifications.filter(n => !n.read).length > 0 && (
            <div className="bg-white rounded-3xl border-2 border-slate-100 p-6">
              <h3 className="font-bold text-slate-900 mb-3">Recent Notifications</h3>
              {notifications.filter(n => !n.read).slice(0, 5).map(n => (
                <div key={n.notification_id} className="bg-sky-50 rounded-xl p-3 border border-sky-200 mb-2">
                  <p className="font-semibold text-slate-900 text-sm">{n.title}</p>
                  <p className="text-sm text-slate-600">{n.message}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Profile & Notification Dialogs */}
        {renderProfileDialog()}
        {renderNotifDialog()}
        <ViewProfilePopup open={viewProfileOpen} onOpenChange={setViewProfileOpen} userId={viewProfileUserId} userRole={viewProfileRole} />
      </div>
    );
  }

  // ─── ENROLLED VIEW (full dashboard) ───
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-white/80 border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <GraduationCap className="w-9 h-9 text-sky-500" strokeWidth={2.5} />
            <div><h1 className="text-xl font-bold text-slate-900">Student Dashboard</h1><p className="text-xs text-slate-500">Credits: {user?.credits || 0}</p></div>
          </div>
          <div className="flex items-center gap-4">
            <button onClick={() => setShowNotifDialog(true)} className="relative p-2 rounded-full hover:bg-slate-100" data-testid="notifications-bell">
              <Bell className="w-5 h-5 text-slate-700" />
              {unreadCount > 0 && <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center font-bold">{unreadCount}</span>}
            </button>
            <span className="text-sm font-medium text-slate-700">{user?.name}</span>
            <span className="text-[10px] font-mono text-slate-400" data-testid="student-id-header">{user?.student_code}</span>
            <Button onClick={handleLogout} variant="outline" size="sm" className="rounded-full" data-testid="logout-button"><LogOut className="w-3 h-3" /></Button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Quick Actions */}
        <div className="flex flex-wrap gap-3 mb-8">
          <Button onClick={() => setShowProfileDialog(true)} variant="outline" className="rounded-full"><User className="w-4 h-4 mr-2" /> Profile</Button>
          <Button onClick={() => navigate('/wallet')} variant="outline" className="rounded-full" data-testid="wallet-button"><CreditCard className="w-4 h-4 mr-2" /> Wallet</Button>
          <Button onClick={() => navigate('/learning-kit')} variant="outline" className="rounded-full" data-testid="learning-kit-button"><BookOpen className="w-4 h-4 mr-2" /> Learning Kit</Button>
          <Button onClick={() => navigate('/complaints')} variant="outline" className="rounded-full" data-testid="complaints-button"><MessageSquare className="w-4 h-4 mr-2" /> Complaints</Button>
          <Button onClick={() => navigate('/chat')} variant="outline" className="rounded-full" data-testid="chat-button"><MessageSquare className="w-4 h-4 mr-2" /> Chat</Button>
          <Button onClick={() => setShowFeedbackDialog(true)} variant="outline" className="rounded-full" data-testid="feedback-button"><Star className="w-4 h-4 mr-2" /> Demo Feedback</Button>
        </div>

        {/* ═══ UNPAID ASSIGNMENTS ═══ */}
        {assignments.filter(a => a.payment_status !== 'paid').length > 0 && (
          <div className="mb-8">
            <h2 className="text-xl font-bold text-orange-700 mb-4 flex items-center gap-2"><IndianRupee className="w-5 h-5 text-orange-500" /> Payment Required ({assignments.filter(a => a.payment_status !== 'paid').length})</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {assignments.filter(a => a.payment_status !== 'paid').map(a => (
                <div key={a.assignment_id} className="bg-white rounded-2xl border-2 border-orange-300 p-5 shadow-sm" data-testid={`unpaid-assignment-${a.assignment_id}`}>
                  <div className="flex gap-2 mb-2">
                    <span className="bg-orange-100 text-orange-800 px-2 py-0.5 rounded-full text-xs font-semibold">UNPAID</span>
                    {a.learning_plan_name && <span className="bg-sky-100 text-sky-800 px-2 py-0.5 rounded-full text-xs">{a.learning_plan_name}</span>}
                  </div>
                  <h3 className="font-bold text-slate-900 mb-1">Assignment with {a.teacher_name}</h3>
                  <p className="text-xs text-slate-600 mb-1">Plan: {a.learning_plan_name || 'Standard'}</p>
                  <p className="text-2xl font-black text-orange-600 mb-3">&#8377;{a.learning_plan_price || a.credit_price}</p>
                  <Button onClick={() => handlePayNow(a.assignment_id)} disabled={paymentLoading}
                    className="w-full bg-orange-500 hover:bg-orange-600 text-white rounded-full font-bold h-12" data-testid={`pay-now-${a.assignment_id}`}>
                    <IndianRupee className="w-4 h-4 mr-2" /> Pay Now
                  </Button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ═══ PAID ASSIGNMENTS ═══ */}
        {assignments.filter(a => a.payment_status === 'paid').length > 0 && (
          <div className="mb-8">
            <h2 className="text-lg font-bold text-emerald-700 mb-3 flex items-center gap-2"><CheckCircle className="w-5 h-5 text-emerald-500" /> Active Enrollments</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {assignments.filter(a => a.payment_status === 'paid').map(a => (
                <div key={a.assignment_id} className="bg-emerald-50 rounded-2xl border border-emerald-200 p-4" data-testid={`paid-assignment-${a.assignment_id}`}>
                  <p className="font-semibold text-slate-900 text-sm">{a.teacher_name}</p>
                  <p className="text-xs text-emerald-700">{a.learning_plan_name || 'Standard Plan'}</p>
                  <p className="text-xs text-slate-500 mt-1">Paid &#8377;{a.learning_plan_price || a.credit_price}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ═══ LIVE CLASSES ═══ */}
        {liveClasses.length > 0 && (
          <div className="mb-8">
            <h2 className="text-xl font-bold text-emerald-700 mb-4 flex items-center gap-2"><Play className="w-5 h-5 text-emerald-500" /> Live Now ({liveClasses.length})</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {liveClasses.map(cls => (
                <div key={cls.class_id} className="bg-white rounded-2xl border-2 border-emerald-400 p-5 ring-2 ring-emerald-200" data-testid={`live-class-${cls.class_id}`}>
                  <div className="flex gap-2 mb-2">
                    <span className="bg-emerald-500 text-white px-2 py-0.5 rounded-full text-xs font-semibold animate-pulse">LIVE</span>
                    <span className="bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full text-xs">{cls.subject}</span>
                  </div>
                  <h3 className="font-bold text-slate-900 mb-1">{cls.title}</h3>
                  <p className="text-xs text-slate-600 mb-3">{cls.start_time} - {cls.end_time} | Teacher: <button onClick={(e) => { e.stopPropagation(); openProfile(cls.teacher_id, 'teacher'); }} className="text-sky-600 hover:underline font-semibold cursor-pointer" data-testid={`view-teacher-${cls.teacher_id}`}>{cls.teacher_name}</button></p>
                  {!cls.cancelled_today ? (
                    <Button onClick={() => navigate(`/class/${cls.class_id}`)} className="w-full bg-emerald-500 hover:bg-emerald-600 text-white rounded-full font-bold animate-pulse" data-testid={`join-live-${cls.class_id}`}>
                      <Play className="w-4 h-4 mr-2" /> Join Live Class
                    </Button>
                  ) : (
                    <div className="bg-red-50 rounded-xl p-3 text-center text-sm text-red-700 font-medium">
                      <AlertCircle className="w-4 h-4 inline mr-1" /> Waiting for teacher to reschedule
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ═══ PENDING RATING (Completed but unrated) ═══ */}
        {pendingRating.length > 0 && (
          <div className="mb-8">
            <h2 className="text-xl font-bold text-amber-700 mb-4 flex items-center gap-2"><Star className="w-5 h-5 text-amber-500" /> Rate Your Classes ({pendingRating.length})</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {pendingRating.map(cls => (
                <div key={cls.class_id} className="bg-amber-50 rounded-2xl border-2 border-amber-200 p-5" data-testid={`pending-rating-${cls.class_id}`}>
                  <h3 className="font-bold text-slate-900 mb-1">{cls.title}</h3>
                  <p className="text-xs text-slate-600 mb-3">{cls.subject} | Teacher: <button onClick={(e) => { e.stopPropagation(); openProfile(cls.teacher_id, 'teacher'); }} className="text-sky-600 hover:underline font-semibold cursor-pointer" data-testid={`view-teacher-rating-${cls.teacher_id}`}>{cls.teacher_name}</button> | {cls.date}</p>
                  <Button onClick={() => { setRatingTarget(cls); setShowRatingDialog(true); }}
                    className="w-full bg-amber-500 hover:bg-amber-600 text-white rounded-full font-bold" data-testid={`rate-class-${cls.class_id}`}>
                    <Star className="w-4 h-4 mr-2" /> Rate & Review
                  </Button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ═══ UPCOMING CLASSES ═══ */}
        <div className="mb-8">
          <h2 className="text-xl font-bold text-slate-900 mb-4 flex items-center gap-2"><Calendar className="w-5 h-5 text-sky-500" /> Upcoming Classes ({upcomingClasses.length})</h2>
          {upcomingClasses.length === 0 ? (
            <div className="bg-white rounded-3xl p-8 border-2 border-slate-100 text-center"><p className="text-slate-500">No upcoming classes</p></div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {upcomingClasses.map(cls => (
                <div key={cls.class_id} className="bg-white rounded-2xl border-2 border-slate-200 p-5" data-testid={`upcoming-class-${cls.class_id}`}>
                  <div className="flex gap-2 flex-wrap mb-2">
                    <span className="bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full text-xs">{cls.subject}</span>
                    {cls.is_demo && <span className="bg-violet-100 text-violet-800 px-2 py-0.5 rounded-full text-xs">DEMO</span>}
                  </div>
                  <h3 className="font-bold text-slate-900 mb-1">{cls.title}</h3>
                  <p className="text-xs text-slate-600 mb-1">{cls.date} | {cls.start_time} - {cls.end_time}</p>
                  <p className="text-xs text-slate-500">Teacher: <button onClick={(e) => { e.stopPropagation(); openProfile(cls.teacher_id, 'teacher'); }} className="text-sky-600 hover:underline font-semibold cursor-pointer" data-testid={`view-teacher-upcoming-${cls.teacher_id}`}>{cls.teacher_name}</button> | {cls.duration_days}d</p>
                  {cls.status === 'scheduled' && !cls.cancelled_today && (
                    <Button onClick={() => handleCancelSession(cls.class_id)} variant="outline" className="w-full mt-3 rounded-full border-red-200 text-red-600 text-xs" data-testid={`cancel-session-${cls.class_id}`}>
                      <XCircle className="w-3 h-3 mr-1" /> Cancel Today's Session
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* ═══ COMPLETED CLASSES ═══ */}
        {completedClasses.length > 0 && (
          <div className="mb-8">
            <h2 className="text-xl font-bold text-slate-700 mb-4 flex items-center gap-2"><Clock className="w-5 h-5 text-slate-400" /> Completed Classes ({completedClasses.length})</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {completedClasses.map(cls => (
                <div key={cls.class_id} className="bg-slate-50 rounded-2xl border border-slate-200 p-4" data-testid={`completed-class-${cls.class_id}`}>
                  <h3 className="font-semibold text-slate-700 text-sm">{cls.title}</h3>
                  <p className="text-xs text-slate-500">{cls.subject} | {cls.date} | Teacher: <button onClick={(e) => { e.stopPropagation(); openProfile(cls.teacher_id, 'teacher'); }} className="text-sky-600 hover:underline font-semibold cursor-pointer" data-testid={`view-teacher-completed-${cls.teacher_id}`}>{cls.teacher_name}</button></p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Rating Dialog */}
      <Dialog open={showRatingDialog} onOpenChange={setShowRatingDialog}>
        <DialogContent className="sm:max-w-md rounded-3xl">
          <DialogHeader><DialogTitle className="text-xl font-bold flex items-center gap-2"><Star className="w-5 h-5 text-amber-500" /> Rate This Class</DialogTitle></DialogHeader>
          {ratingTarget && (
            <div className="space-y-4 mt-4">
              <div className="bg-sky-50 rounded-xl p-3 border border-sky-200">
                <p className="font-semibold text-slate-900">{ratingTarget.title}</p>
                <p className="text-sm text-slate-600">Teacher: {ratingTarget.teacher_name}</p>
              </div>
              <div>
                <Label>Rating</Label>
                <div className="flex gap-2 mt-1">
                  {[1,2,3,4,5].map(s => (
                    <button key={s} onClick={() => setRatingForm({...ratingForm, rating: s})}
                      className={`w-10 h-10 rounded-full text-lg font-bold transition-all ${ratingForm.rating >= s ? 'bg-amber-400 text-white scale-110' : 'bg-slate-100 text-slate-400'}`}
                      data-testid={`star-${s}`}>
                      {s}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <Label>Comments (Required)</Label>
                <textarea value={ratingForm.comments} onChange={e => setRatingForm({...ratingForm, comments: e.target.value})}
                  placeholder="Share your experience..." className="w-full rounded-xl border-2 border-slate-200 px-3 py-2 text-sm" rows={3} data-testid="rating-comments" />
              </div>
              <Button onClick={handleSubmitRating} className="w-full bg-amber-500 hover:bg-amber-600 text-white rounded-full py-6 font-bold" data-testid="submit-rating-btn">Submit Rating</Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
      <Dialog open={showFeedbackDialog} onOpenChange={setShowFeedbackDialog}>
        <DialogContent className="sm:max-w-lg rounded-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader><DialogTitle className="text-xl font-bold">Demo Feedback from Teachers</DialogTitle></DialogHeader>
          <div className="space-y-3 mt-4">
            {demoFeedbacks.length === 0 ? <p className="text-slate-500 text-center py-8">No demo feedback yet</p> : demoFeedbacks.map((fb, i) => (
              <div key={i} className="bg-sky-50 rounded-xl p-4 border border-sky-200" data-testid={`demo-feedback-${i}`}>
                <p className="text-sm font-semibold text-slate-900 mb-1">Teacher: {fb.teacher_name} {fb.teacher_code ? `(${fb.teacher_code})` : ''}</p>
                <p className="text-sm text-slate-600">{fb.feedback || fb.feedback_text || fb.notes || 'No detailed feedback'}</p>
                {fb.rating && <p className="text-xs text-amber-600 mt-1 font-semibold">Rating: {fb.rating}</p>}
                <p className="text-xs text-slate-400 mt-1">{fb.created_at?.slice(0, 10)}</p>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>

      {renderProfileDialog()}
      {renderNotifDialog()}
      <ViewProfilePopup open={viewProfileOpen} onOpenChange={setViewProfileOpen} userId={viewProfileUserId} userRole={viewProfileRole} />

      {/* Attendance Dialog */}
      <Dialog open={showAttendanceDialog} onOpenChange={setShowAttendanceDialog}>
        <DialogContent className="sm:max-w-2xl rounded-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle className="flex items-center gap-2"><Calendar className="w-5 h-5 text-sky-500" /> My Attendance History</DialogTitle></DialogHeader>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="text-left p-2 text-xs text-slate-500">Date</th>
                  <th className="text-left p-2 text-xs text-slate-500">Teacher</th>
                  <th className="text-center p-2 text-xs text-slate-500">Status</th>
                </tr>
              </thead>
              <tbody>
                {attendanceRecords.map((r, i) => (
                  <tr key={i} className="border-b border-slate-100">
                    <td className="p-2 text-xs">{r.date}</td>
                    <td className="p-2 text-xs font-semibold">{r.teacher_name}</td>
                    <td className="p-2 text-center">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${r.status === 'present' ? 'bg-emerald-100 text-emerald-700' : r.status === 'absent' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}`}>{r.status}</span>
                    </td>
                  </tr>
                ))}
                {attendanceRecords.length === 0 && (
                  <tr><td colSpan="3" className="text-center p-8 text-slate-400">No attendance records yet</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );

  // ─── Shared Dialogs ───
  function renderProfileDialog() {
    return (
      <Dialog open={showProfileDialog} onOpenChange={setShowProfileDialog}>
        <DialogContent className="sm:max-w-md rounded-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader><DialogTitle className="text-xl font-bold">My Profile</DialogTitle></DialogHeader>
          <div className="space-y-3 mt-4">
            {/* Read-only Student ID */}
            <div className="bg-slate-50 rounded-xl p-3">
              <Label className="text-xs text-slate-500">Student ID (Read-Only)</Label>
              <p className="font-mono font-bold text-slate-900" data-testid="student-code-readonly">{user?.student_code || '-'}</p>
            </div>
            <div className="bg-slate-50 rounded-xl p-3">
              <Label className="text-xs text-slate-500">Email</Label>
              <p className="text-sm text-slate-900">{user?.email}</p>
            </div>
            {/* Read-only academic fields (only Admin can edit) */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-slate-50 rounded-xl p-3">
                <Label className="text-xs text-slate-500">Grade/Class</Label>
                <p className="text-sm font-semibold text-slate-900">{user?.grade ? `Class ${user.grade}` : 'Not set'}</p>
              </div>
              <div className="bg-slate-50 rounded-xl p-3">
                <Label className="text-xs text-slate-500">Institute</Label>
                <p className="text-sm font-semibold text-slate-900">{user?.institute || 'Not set'}</p>
              </div>
              <div className="bg-slate-50 rounded-xl p-3 col-span-2">
                <Label className="text-xs text-slate-500">Goal</Label>
                <p className="text-sm font-semibold text-slate-900">{user?.goal || 'Not set'}</p>
              </div>
            </div>
            <p className="text-[10px] text-amber-600 bg-amber-50 rounded-lg p-2 font-medium">Academic details (Grade, Institute, Goal) can only be changed by Admin. Contact support if you need changes.</p>
            {/* Editable contact fields */}
            <div className="grid grid-cols-2 gap-3">
              <div><Label>Phone</Label><Input value={profileForm.phone} onChange={e => setProfileForm({...profileForm, phone: e.target.value})} className="rounded-xl" data-testid="profile-phone" /></div>
              <div><Label>Preferred Time</Label>
                <Input type="datetime-local" value={profileForm.preferred_time_slot?.split(' to ')[0] || ''} onChange={e => setProfileForm({...profileForm, preferred_time_slot: e.target.value})} className="rounded-xl" data-testid="profile-time" />
              </div>
              <div><Label>State</Label><Input value={profileForm.state} onChange={e => setProfileForm({...profileForm, state: e.target.value})} className="rounded-xl" data-testid="profile-state" /></div>
              <div><Label>City</Label><Input value={profileForm.city} onChange={e => setProfileForm({...profileForm, city: e.target.value})} className="rounded-xl" data-testid="profile-city" /></div>
              <div className="col-span-2"><Label>Country</Label><Input value={profileForm.country} onChange={e => setProfileForm({...profileForm, country: e.target.value})} className="rounded-xl" data-testid="profile-country" /></div>
            </div>
            <Button onClick={handleUpdateProfile} className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-full py-6 font-bold" data-testid="save-profile-button">Save Contact Info</Button>
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  function renderNotifDialog() {
    return (
      <Dialog open={showNotifDialog} onOpenChange={setShowNotifDialog}>
        <DialogContent className="sm:max-w-lg rounded-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <div className="flex items-center justify-between w-full">
              <DialogTitle className="text-xl font-bold">Notifications</DialogTitle>
              {unreadCount > 0 && <Button onClick={handleMarkAllRead} variant="outline" size="sm" className="rounded-full text-xs" data-testid="mark-all-read">Mark all read</Button>}
            </div>
          </DialogHeader>
          <div className="space-y-2 mt-4">
            {notifications.length === 0 ? <p className="text-slate-500 text-center py-8">No notifications</p> : notifications.map(n => (
              <div key={n.notification_id} className={`rounded-xl p-3 border-2 ${n.read ? 'bg-slate-50 border-slate-200' : 'bg-sky-50 border-sky-200'}`}>
                {!n.read && <div className="w-2 h-2 rounded-full bg-sky-500 float-right" />}
                <p className="font-semibold text-sm text-slate-900">{n.title}</p>
                <p className="text-sm text-slate-600">{n.message}</p>
                <p className="text-xs text-slate-400 mt-1">{new Date(n.created_at).toLocaleString()}</p>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    );
  }
};

export default StudentDashboard;
