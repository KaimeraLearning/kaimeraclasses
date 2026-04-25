import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';
import { GraduationCap, LogOut, Plus, Calendar, Users, AlertCircle, ShieldCheck, Upload, MessageSquare, Bell, Play, ChevronDown, ChevronUp, Zap, CreditCard, BookOpen, CalendarDays, Search, User, Star, AlertTriangle, XCircle, CheckCircle, Clock, Camera, CalendarCheck } from 'lucide-react';
import { getApiError } from '../utils/api';
import { ViewProfilePopup } from '../components/ViewProfilePopup';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const TeacherDashboard = () => {
  const navigate = useNavigate();
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);
  const [groupedData, setGroupedData] = useState({ today: [], grouped_by_student: {} });
  const [showCreateClass, setShowCreateClass] = useState(false);
  const [showProofDialog, setShowProofDialog] = useState(false);
  const [proofClass, setProofClass] = useState(null);
  const [proofForm, setProofForm] = useState({ feedback_text: '', student_performance: 'good', topics_covered: '', screenshot_base64: '' });
  const [showFeedbackDialog, setShowFeedbackDialog] = useState(false);
  const [feedbackTarget, setFeedbackTarget] = useState(null);
  const [feedbackForm, setFeedbackForm] = useState({ feedback_text: '', performance_rating: 'good' });
  const [showRescheduleDialog, setShowRescheduleDialog] = useState(false);
  const [rescheduleTarget, setRescheduleTarget] = useState(null);
  const [rescheduleForm, setRescheduleForm] = useState({ new_date: '', new_start_time: '', new_end_time: '' });
  const [pendingDemoFeedback, setPendingDemoFeedback] = useState([]);
  const [showDemoFeedbackDialog, setShowDemoFeedbackDialog] = useState(false);
  const [demoFeedbackTarget, setDemoFeedbackTarget] = useState(null);
  const [demoFeedbackForm, setDemoFeedbackForm] = useState({ feedback_text: '', performance_rating: 'good', recommended_frequency: '' });
  const [classTab, setClassTab] = useState('today');
  const [showNotifDialog, setShowNotifDialog] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [showRatingDialog, setShowRatingDialog] = useState(false);
  const [ratingData, setRatingData] = useState(null);
  const [viewProfileOpen, setViewProfileOpen] = useState(false);
  const [viewProfileUserId, setViewProfileUserId] = useState(null);
  const [viewProfileRole, setViewProfileRole] = useState(null);
  const [attendanceRecords, setAttendanceRecords] = useState([]);
  const [showAttendanceDialog, setShowAttendanceDialog] = useState(false);

  const openProfile = (userId, role) => { setViewProfileUserId(userId); setViewProfileRole(role); setViewProfileOpen(true); };

  // Create class form
  const [classForm, setClassForm] = useState({
    title: '', subject: '', class_type: '1:1', date: '', start_time: '', end_time: '', max_students: 1, assigned_student_id: '', duration_days: 1, is_demo: false
  });

  useEffect(() => { fetchUser(); fetchDashboardData(); fetchNotifications(); }, []);

  // Auto-refresh on tab focus
  useEffect(() => {
    const handleVisibility = () => { if (document.visibilityState === 'visible') { fetchDashboardData(); fetchNotifications(); } };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => document.removeEventListener('visibilitychange', handleVisibility);
  }, []);

  const fetchUser = async () => {
    try {
      const res = await fetch(`${API}/auth/me`, { credentials: 'include' });
      if (!res.ok) { navigate('/login'); return; }
      setUser(await res.json());
    } catch { navigate('/login'); }
  };

  const fetchDashboardData = async () => {
    try {
      const [dashRes, groupedRes] = await Promise.all([
        fetch(`${API}/teacher/dashboard`, { credentials: 'include' }),
        fetch(`${API}/teacher/grouped-classes`, { credentials: 'include' })
      ]);
      if (dashRes.ok) {
        const data = await dashRes.json();
        setDashboardData(data);
      }
      if (groupedRes.ok) setGroupedData(await groupedRes.json());
      try {
        const demoFbRes = await fetch(`${API}/teacher/pending-demo-feedback`, { credentials: 'include' });
        if (demoFbRes.ok) setPendingDemoFeedback(await demoFbRes.json());
      } catch {}
      setLoading(false);
    } catch { setLoading(false); }
  };

  const fetchNotifications = async () => {
    try {
      const res = await fetch(`${API}/notifications`, { credentials: 'include' });
      if (res.ok) { const data = await res.json(); setNotifications(data); setUnreadCount(data.filter(n => !n.read).length); }
    } catch {}
  };

  const fetchRating = async () => {
    try {
      const res = await fetch(`${API}/teacher/my-rating`, { credentials: 'include' });
      if (res.ok) setRatingData(await res.json());
    } catch {}
  };

  const fetchAttendance = async () => {
    try {
      const res = await fetch(`${API}/attendance/teacher`, { credentials: 'include' });
      if (res.ok) { setAttendanceRecords(await res.json()); setShowAttendanceDialog(true); }
    } catch {}
  };

  const markAttendance = async (studentId, date, status) => {
    try {
      const res = await fetch(`${API}/attendance/mark`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ student_id: studentId, date, status })
      });
      if (!res.ok) throw new Error(await getApiError(res));
      toast.success(`Attendance marked as ${status}`);
      fetchAttendance();
    } catch (err) { toast.error(err.message); }
  };

  const handleCreateClass = async () => {
    if (!classForm.title || !classForm.date || !classForm.start_time || !classForm.end_time || !classForm.assigned_student_id) {
      toast.error('Please fill all required fields'); return;
    }
    try {
      const res = await fetch(`${API}/classes/create`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
        body: JSON.stringify(classForm)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      toast.success('Class created!');
      setShowCreateClass(false);
      setClassForm({ title: '', subject: '', class_type: '1:1', date: '', start_time: '', end_time: '', max_students: 1, assigned_student_id: '', duration_days: 1, is_demo: false });
      fetchDashboardData();
    } catch (err) { toast.error(err.message); }
  };

  const handleDeleteClass = async (classId) => {
    if (!window.confirm('Delete this class?')) return;
    try {
      const res = await fetch(`${API}/classes/delete/${classId}`, { method: 'DELETE', credentials: 'include' });
      if (!res.ok) throw new Error(await getApiError(res));
      toast.success('Class deleted'); fetchDashboardData();
    } catch (err) { toast.error(err.message); }
  };

  const [cancellingClassId, setCancellingClassId] = useState(null);
  const handleTeacherCancelClass = async (classId) => {
    if (!window.confirm('Cancel this class? This will impact your rating and refund the student.')) return;
    setCancellingClassId(classId);
    try {
      const res = await fetch(`${API}/teacher/cancel-class/${classId}`, { method: 'POST', credentials: 'include' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to cancel class');
      toast.success(data.message);
      fetchDashboardData();
    } catch (err) { toast.error(err.message); }
    setCancellingClassId(null);
  };

  const handleApproveAssignment = async (assignmentId, approved) => {
    try {
      const res = await fetch(`${API}/teacher/approve-assignment`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
        body: JSON.stringify({ assignment_id: assignmentId, approved })
      });
      if (!res.ok) throw new Error(await getApiError(res));
      toast.success(approved ? 'Student approved!' : 'Student rejected');
      fetchDashboardData();
    } catch (err) { toast.error(err.message); }
  };

  const handleSubmitProof = async () => {
    try {
      const res = await fetch(`${API}/teacher/submit-proof`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
        body: JSON.stringify({ class_id: proofClass.class_id, ...proofForm })
      });
      if (!res.ok) throw new Error(await getApiError(res));
      toast.success('Proof submitted!');
      setShowProofDialog(false); setProofClass(null);
      setProofForm({ feedback_text: '', student_performance: 'good', topics_covered: '', screenshot_base64: '' });
    } catch (err) { toast.error(err.message); }
  };

  const handleSendFeedback = async () => {
    if (!feedbackForm.feedback_text) { toast.error('Please enter feedback'); return; }
    try {
      const res = await fetch(`${API}/teacher/feedback-to-student`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
        body: JSON.stringify({ student_id: feedbackTarget.student_id, ...feedbackForm })
      });
      if (!res.ok) throw new Error(await getApiError(res));
      toast.success('Feedback sent!');
      setShowFeedbackDialog(false); setFeedbackTarget(null);
      setFeedbackForm({ feedback_text: '', performance_rating: 'good' });
    } catch (err) { toast.error(err.message); }
  };

  const handleReschedule = async () => {
    if (!rescheduleForm.new_date || !rescheduleForm.new_start_time || !rescheduleForm.new_end_time) {
      toast.error('All reschedule fields required'); return;
    }
    try {
      const res = await fetch(`${API}/teacher/reschedule-class/${rescheduleTarget.class_id}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
        body: JSON.stringify(rescheduleForm)
      });
      if (!res.ok) throw new Error(await getApiError(res));
      toast.success('Session rescheduled!');
      setShowRescheduleDialog(false); setRescheduleTarget(null);
      setRescheduleForm({ new_date: '', new_start_time: '', new_end_time: '' });
      fetchDashboardData();
    } catch (err) { toast.error(err.message); }
  };

  const handleSubmitDemoFeedback = async () => {
    if (!demoFeedbackForm.feedback_text) { toast.error('Please enter demo feedback'); return; }
    try {
      const res = await fetch(`${API}/teacher/submit-demo-feedback`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
        body: JSON.stringify({ demo_id: demoFeedbackTarget.demo_id, student_id: demoFeedbackTarget.student_id || demoFeedbackTarget.student_user_id, ...demoFeedbackForm })
      });
      if (!res.ok) throw new Error(await getApiError(res));
      toast.success('Demo feedback submitted!');
      setShowDemoFeedbackDialog(false); setDemoFeedbackTarget(null);
      setDemoFeedbackForm({ feedback_text: '', performance_rating: 'good', recommended_frequency: '' });
      fetchDashboardData();
    } catch (err) { toast.error(err.message); }
  };

  const handleMarkAllRead = async () => {
    try {
      await fetch(`${API}/notifications/mark-all-read`, { method: 'POST', credentials: 'include' });
      fetchNotifications();
    } catch {}
  };

  const handleLogout = async () => {
    await fetch(`${API}/auth/logout`, { method: 'POST', credentials: 'include' });
    navigate('/login');
  };

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="w-16 h-16 border-4 border-sky-500 border-t-transparent rounded-full animate-spin" />
    </div>
  );

  // SUSPENSION SCREEN
  if (dashboardData?.is_suspended) {
    return (
      <div className="min-h-screen bg-red-50 flex items-center justify-center p-8">
        <div className="bg-white rounded-3xl shadow-xl p-10 max-w-lg text-center border-2 border-red-300" data-testid="suspended-screen">
          <AlertTriangle className="w-20 h-20 text-red-500 mx-auto mb-4" />
          <h1 className="text-3xl font-bold text-red-800 mb-2">Account Suspended</h1>
          <p className="text-red-600 mb-4">Your account has been suspended due to excessive class cancellations.</p>
          <div className="bg-red-100 rounded-xl p-4 mb-6">
            <p className="text-sm text-red-700">Suspended until: <strong>{dashboardData.suspended_until ? new Date(dashboardData.suspended_until).toLocaleDateString() : 'N/A'}</strong></p>
            <p className="text-sm text-red-700 mt-1">Current Rating: <strong>{dashboardData.star_rating}/5</strong></p>
          </div>
          <p className="text-xs text-slate-500">During suspension, you cannot create classes or accept new students. Contact admin for assistance.</p>
          <Button onClick={handleLogout} variant="outline" className="mt-6 rounded-full" data-testid="logout-suspended"><LogOut className="w-4 h-4 mr-2" /> Logout</Button>
        </div>
      </div>
    );
  }

  const todaySessions = dashboardData?.todays_sessions || [];
  const upcomingClasses = dashboardData?.upcoming_classes || [];
  const conductedClasses = dashboardData?.conducted_classes || [];

  const renderClassCard = (cls, section) => {
    const isLive = cls.status === 'in_progress';
    const cancellations = cls.cancellation_count || 0;

    return (
      <div key={cls.class_id} className={`bg-white rounded-2xl border-2 p-4 ${isLive ? 'border-emerald-400 shadow-lg shadow-emerald-50' : cls.cancelled_today ? 'border-red-300' : 'border-slate-200'}`} data-testid={`class-card-${cls.class_id}`}>
        <div className="flex items-start justify-between mb-2">
          <div>
            <h3 className="font-bold text-slate-900 text-sm">{cls.title}</h3>
            <p className="text-xs text-slate-600">{cls.subject} | {cls.class_type}</p>
            <p className="text-xs text-slate-500">{cls.date} {cls.start_time}-{cls.end_time} ({cls.duration_days}d)</p>
          </div>
          <div className="flex flex-col items-end gap-1">
            {isLive && <span className="bg-emerald-500 text-white px-2 py-0.5 rounded-full text-[10px] font-bold animate-pulse">LIVE</span>}
            {cls.is_demo && <span className="bg-violet-100 text-violet-700 px-2 py-0.5 rounded-full text-[10px] font-semibold">DEMO</span>}
            {cls.status === 'completed' && <span className="bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full text-[10px] font-semibold">DONE</span>}
          </div>
        </div>

        {cancellations > 0 && <div className="bg-amber-50 border border-amber-200 rounded-lg p-1.5 mb-2 text-xs text-amber-800 font-semibold">Cancelled {cancellations}/{cls.max_cancellations || 3} sessions</div>}
        {cls.cancelled_today && (
          <div className="bg-red-50 rounded-lg p-2 text-center text-xs text-red-700 font-semibold border border-red-200 mb-2">
            <AlertCircle className="w-3 h-3 inline mr-1" /> Session cancelled by student
          </div>
        )}
        {cls.cancelled_today && (
          <Button onClick={() => { setRescheduleTarget(cls); setShowRescheduleDialog(true); }} className="w-full bg-amber-500 hover:bg-amber-600 text-white rounded-full text-xs h-7 mb-2" data-testid={`reschedule-${cls.class_id}`}>
            <CalendarDays className="w-3 h-3 mr-1" /> Reschedule Session
          </Button>
        )}

        <div className="space-y-1.5">
          {section === 'today' && cls.status === 'scheduled' && !cls.cancelled_today && (
            <Button onClick={() => navigate(`/class/${cls.class_id}`)} className="w-full bg-emerald-500 hover:bg-emerald-600 text-white rounded-full font-bold text-sm h-8" data-testid={`start-class-${cls.class_id}`}>
              <Play className="w-3 h-3 mr-1" /> Start Class
            </Button>
          )}
          {isLive && !cls.cancelled_today && (
            <Button onClick={() => navigate(`/class/${cls.class_id}`)} className="w-full bg-emerald-500 hover:bg-emerald-600 text-white rounded-full font-bold text-sm h-8 animate-pulse" data-testid={`rejoin-class-${cls.class_id}`}>
              <Play className="w-3 h-3 mr-1" /> Rejoin Live
            </Button>
          )}
          {section === 'conducted' && cls.status !== 'cancelled' && !cls.proof_submitted && (
            <Button onClick={() => { setProofClass(cls); setShowProofDialog(true); }} variant="outline" className="w-full rounded-full text-xs h-7" data-testid={`submit-proof-${cls.class_id}`}><Upload className="w-3 h-3 mr-1" /> Submit Proof</Button>
          )}
          {section === 'conducted' && cls.proof_submitted && (
            <div className="bg-emerald-50 border border-emerald-200 rounded-full px-3 py-1 text-center text-xs text-emerald-700 font-medium" data-testid={`proof-submitted-${cls.class_id}`}><CheckCircle className="w-3 h-3 inline mr-1" />Proof Submitted</div>
          )}
          {section !== 'conducted' && cls.status !== 'completed' && cls.status !== 'cancelled' && (
            <div className="flex gap-1.5">
              <Button onClick={() => handleTeacherCancelClass(cls.class_id)} disabled={cancellingClassId === cls.class_id} variant="outline" className="flex-1 rounded-full text-xs h-7 border-red-200 text-red-600 hover:bg-red-50 disabled:opacity-40 disabled:cursor-not-allowed" data-testid={`teacher-cancel-${cls.class_id}`}><XCircle className="w-3 h-3 mr-1" /> {cancellingClassId === cls.class_id ? 'Cancelling...' : 'Cancel'}</Button>
            </div>
          )}
          {section === 'today' && (
            <Button onClick={() => handleDeleteClass(cls.class_id)} variant="outline" className="w-full border border-red-200 hover:bg-red-50 text-red-600 rounded-full text-xs h-7" data-testid={`delete-class-${cls.class_id}`}>Delete</Button>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-white/80 border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <GraduationCap className="w-8 h-8 text-sky-500" />
              <div>
                <h1 className="text-xl font-bold text-slate-900">{user?.name}</h1>
                <p className="text-xs text-slate-500 font-mono" data-testid="teacher-id-display">ID: {user?.teacher_code || user?.user_id}</p>
              </div>
              {/* Star Rating Badge */}
              <button onClick={() => { fetchRating(); setShowRatingDialog(true); }} className="flex items-center gap-1 bg-amber-50 border border-amber-200 rounded-full px-3 py-1 hover:bg-amber-100 transition-colors" data-testid="rating-badge">
                <Star className="w-4 h-4 text-amber-500 fill-amber-500" />
                <span className="text-sm font-bold text-amber-700">{dashboardData?.star_rating?.toFixed(1) || '5.0'}</span>
              </button>
            </div>
            <div className="flex items-center gap-2">
              <Button onClick={() => setShowNotifDialog(true)} variant="outline" className="rounded-full relative" data-testid="notif-button">
                <Bell className="w-4 h-4" />
                {unreadCount > 0 && <span className="absolute -top-1 -right-1 bg-red-500 text-white text-[10px] w-5 h-5 rounded-full flex items-center justify-center font-bold">{unreadCount}</span>}
              </Button>
              <Button onClick={() => navigate('/chat')} variant="outline" className="rounded-full" data-testid="chat-button"><MessageSquare className="w-4 h-4" /></Button>
              <Button onClick={handleLogout} variant="outline" className="rounded-full" data-testid="logout-button"><LogOut className="w-4 h-4" /></Button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Quick Actions */}
        <div className="flex flex-wrap gap-3 mb-8">
          <Button onClick={() => setShowCreateClass(true)} className="bg-sky-500 hover:bg-sky-600 text-white rounded-full" data-testid="create-class-button"><Plus className="w-4 h-4 mr-2" /> Create Class</Button>
          <Button onClick={() => navigate('/demo-live-sheet')} variant="outline" className="rounded-full bg-emerald-50 border-emerald-200 text-emerald-700 hover:bg-emerald-100" data-testid="demo-live-sheet-button"><Play className="w-4 h-4 mr-2" /> Demo Live Sheet</Button>
          <Button onClick={() => navigate('/teacher-calendar')} variant="outline" className="rounded-full" data-testid="calendar-button"><Calendar className="w-4 h-4 mr-2" /> Schedule Planner</Button>
          <Button onClick={() => navigate('/wallet')} variant="outline" className="rounded-full"><CreditCard className="w-4 h-4 mr-2" /> Wallet</Button>
          <Button onClick={() => navigate('/learning-kits')} variant="outline" className="rounded-full"><BookOpen className="w-4 h-4 mr-2" /> Learning Kit</Button>
          <Button onClick={() => navigate('/complaints')} variant="outline" className="rounded-full"><ShieldCheck className="w-4 h-4 mr-2" /> Complaints</Button>
          <Button onClick={() => navigate('/teacher-profile')} variant="outline" className="rounded-full" data-testid="my-profile-button"><User className="w-4 h-4 mr-2" /> My Profile</Button>
        </div>

        {/* Pending Demo Feedback */}
        {pendingDemoFeedback.length > 0 && (
          <div className="mb-8 bg-violet-50 rounded-3xl border-2 border-violet-300 p-6" data-testid="pending-demo-feedback-alert">
            <h2 className="text-lg font-bold text-violet-800 mb-2 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-violet-600" /> Demo Feedback Required ({pendingDemoFeedback.length})
            </h2>
            <p className="text-sm text-violet-600 mb-4">You must submit feedback for completed demos.</p>
            <div className="space-y-2">
              {pendingDemoFeedback.map(demo => (
                <div key={demo.demo_id} className="bg-white rounded-xl p-3 border border-violet-200 flex items-center justify-between">
                  <div>
                    <p className="font-semibold text-slate-900 text-sm">{demo.student_name || demo.name || 'Student'}</p>
                    <p className="text-xs text-slate-500">{demo.subject || 'Demo'} - {demo.preferred_date}</p>
                  </div>
                  <Button onClick={() => { setDemoFeedbackTarget(demo); setShowDemoFeedbackDialog(true); }}
                    className="bg-violet-500 hover:bg-violet-600 text-white rounded-full text-xs px-4" data-testid={`submit-demo-fb-${demo.demo_id}`}>
                    Submit Feedback
                  </Button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Pending Assignments */}
        {dashboardData?.pending_assignments?.length > 0 && (
          <div className="mb-8">
            <h2 className="text-lg font-bold text-slate-900 mb-3">Pending Student Assignments</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {dashboardData.pending_assignments.map(a => (
                <div key={a.assignment_id} className="bg-amber-50 rounded-2xl border-2 border-amber-200 p-5" data-testid={`assignment-${a.assignment_id}`}>
                  <h3 className="font-bold text-slate-900">{a.student_name}</h3>
                  <p className="text-sm text-slate-600">{a.student_email}</p>
                  <div className="flex gap-2 mt-3">
                    <Button onClick={() => handleApproveAssignment(a.assignment_id, true)} className="flex-1 bg-emerald-500 hover:bg-emerald-600 text-white rounded-full" data-testid={`approve-${a.assignment_id}`}><CheckCircle className="w-4 h-4 mr-1" /> Accept</Button>
                    <Button onClick={() => handleApproveAssignment(a.assignment_id, false)} variant="outline" className="flex-1 rounded-full border-red-200 text-red-600" data-testid={`reject-${a.assignment_id}`}><XCircle className="w-4 h-4 mr-1" /> Reject</Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Class Sections - Tabbed */}
        <Tabs value={classTab} onValueChange={setClassTab} className="mb-8">
          <TabsList data-testid="class-tabs">
            <TabsTrigger value="today" data-testid="tab-today">Today's Sessions ({todaySessions.length})</TabsTrigger>
            <TabsTrigger value="upcoming" data-testid="tab-upcoming">Upcoming ({upcomingClasses.length})</TabsTrigger>
            <TabsTrigger value="conducted" data-testid="tab-conducted">Conducted ({conductedClasses.length})</TabsTrigger>
          </TabsList>

          <TabsContent value="today">
            {todaySessions.length === 0 ? (
              <div className="bg-white rounded-3xl p-8 border-2 border-slate-100 text-center"><p className="text-slate-500">No sessions scheduled for today</p></div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {todaySessions.map(cls => renderClassCard(cls, 'today'))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="upcoming">
            {upcomingClasses.length === 0 ? (
              <div className="bg-white rounded-3xl p-8 border-2 border-slate-100 text-center"><p className="text-slate-500">No upcoming classes</p></div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {upcomingClasses.map(cls => renderClassCard(cls, 'upcoming'))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="conducted">
            {conductedClasses.length === 0 ? (
              <div className="bg-white rounded-3xl p-8 border-2 border-slate-100 text-center"><p className="text-slate-500">No conducted classes yet</p></div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {conductedClasses.map(cls => renderClassCard(cls, 'conducted'))}
              </div>
            )}
          </TabsContent>
        </Tabs>

        {/* My Students */}
        {dashboardData?.approved_students?.length > 0 && (
          <div className="mb-8">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2"><Users className="w-5 h-5 text-sky-500" /> My Students</h2>
              <Button variant="outline" onClick={fetchAttendance} className="rounded-full text-xs" data-testid="view-attendance-btn"><CalendarCheck className="w-3.5 h-3.5 mr-1" /> Attendance History</Button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {dashboardData.approved_students.map(s => (
                <div key={s.assignment_id} className="bg-white rounded-xl border border-slate-200 p-3">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <p className="font-semibold text-slate-900 text-sm">{s.student_name}</p>
                        <p className="text-xs text-slate-500">{s.student_email}</p>
                        {s.counselor_name && (
                          <p className="text-xs text-slate-400 mt-0.5">Assigned by: <button onClick={() => openProfile(s.counselor_id, 'counsellor')} className="text-violet-600 hover:underline font-semibold cursor-pointer" data-testid={`view-counselor-${s.counselor_id}`}>{s.counselor_name}</button></p>
                        )}
                      </div>
                    </div>
                    <div className="flex gap-1.5 flex-wrap">
                      <Button onClick={() => markAttendance(s.student_id, new Date().toISOString().split('T')[0], 'present')} variant="outline" className="rounded-full text-xs h-7 px-2" data-testid={`mark-present-${s.student_id}`} title="Mark Present Today">
                        <CheckCircle className="w-3 h-3 text-emerald-500 mr-1" /> Present
                      </Button>
                      <Button onClick={() => markAttendance(s.student_id, new Date().toISOString().split('T')[0], 'absent')} variant="outline" className="rounded-full text-xs h-7 px-2" data-testid={`mark-absent-${s.student_id}`} title="Mark Absent Today">
                        <XCircle className="w-3 h-3 text-red-500 mr-1" /> Absent
                      </Button>
                      <Button onClick={() => { setFeedbackTarget({ student_id: s.student_id }); setShowFeedbackDialog(true); }} variant="outline" className="rounded-full text-xs h-7 px-2"><MessageSquare className="w-3 h-3 mr-1" /> Feedback</Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Create Class Dialog */}
      <Dialog open={showCreateClass} onOpenChange={setShowCreateClass}>
        <DialogContent className="sm:max-w-lg rounded-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle className="text-2xl font-bold text-slate-900">Create Class Session</DialogTitle></DialogHeader>
          <div className="space-y-4 mt-4">
            <div><Label>Title</Label><Input value={classForm.title} onChange={e => setClassForm({...classForm, title: e.target.value})} placeholder="Class title" className="rounded-xl" data-testid="class-title-input" /></div>
            <div className="grid grid-cols-2 gap-3">
              <div><Label>Subject</Label><Input value={classForm.subject} onChange={e => setClassForm({...classForm, subject: e.target.value})} className="rounded-xl" /></div>
              <div><Label>Type</Label>
                <select value={classForm.class_type} onChange={e => setClassForm({...classForm, class_type: e.target.value})} className="w-full rounded-xl border-2 border-slate-200 px-3 py-2 text-sm h-10">
                  <option value="1:1">1:1</option><option value="group">Group</option>
                </select>
              </div>
            </div>
            <div><Label>Student</Label>
              <select value={classForm.assigned_student_id} onChange={e => {
                const sid = e.target.value;
                const student = (dashboardData?.approved_students || []).find(s => s.student_id === sid);
                const days = student?.assigned_days || classForm.duration_days;
                setClassForm({...classForm, assigned_student_id: sid, duration_days: days});
              }}
                className="w-full rounded-xl border-2 border-slate-200 px-3 py-2 text-sm" data-testid="class-student-select">
                <option value="">Select student...</option>
                {(dashboardData?.approved_students || []).map(s => <option key={s.student_id} value={s.student_id}>{s.student_name} {s.assigned_days ? `(${s.assigned_days} days assigned)` : ''}</option>)}
              </select>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div><Label>Date</Label><Input type="date" value={classForm.date} onChange={e => setClassForm({...classForm, date: e.target.value})} className="rounded-xl" data-testid="class-date-input" /></div>
              <div><Label>Start</Label><Input type="time" value={classForm.start_time} onChange={e => setClassForm({...classForm, start_time: e.target.value})} className="rounded-xl" /></div>
              <div><Label>End</Label><Input type="time" value={classForm.end_time} onChange={e => setClassForm({...classForm, end_time: e.target.value})} className="rounded-xl" /></div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Duration (Days)</Label>
                {(() => {
                  const student = (dashboardData?.approved_students || []).find(s => s.student_id === classForm.assigned_student_id);
                  const locked = student?.assigned_days > 0;
                  return (
                    <>
                      <Input type="number" min="1" value={classForm.duration_days}
                        onChange={e => { if (!locked) setClassForm({...classForm, duration_days: parseInt(e.target.value) || 1}); }}
                        readOnly={locked} className={`rounded-xl ${locked ? 'bg-slate-100 cursor-not-allowed' : ''}`} data-testid="class-days-input" />
                      {locked && <p className="text-[10px] text-amber-600 mt-0.5">Set by counselor</p>}
                    </>
                  );
                })()}
              </div>
              <div className="flex items-end">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked={classForm.is_demo} onChange={e => setClassForm({...classForm, is_demo: e.target.checked})} className="rounded" />
                  <span className="text-sm font-medium text-slate-700">Demo Session</span>
                </label>
              </div>
            </div>
            <Button onClick={handleCreateClass} className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-full py-6 font-bold" data-testid="submit-create-class">Create Class</Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Proof Dialog */}
      <Dialog open={showProofDialog} onOpenChange={setShowProofDialog}>
        <DialogContent className="sm:max-w-md rounded-3xl">
          <DialogHeader><DialogTitle>Submit Class Proof</DialogTitle></DialogHeader>
          <div className="space-y-3 mt-4">
            <div><Label>Topics Covered</Label><Input value={proofForm.topics_covered} onChange={e => setProofForm({...proofForm, topics_covered: e.target.value})} className="rounded-xl" data-testid="proof-topics" /></div>
            <div><Label>Student Performance</Label>
              <select value={proofForm.student_performance} onChange={e => setProofForm({...proofForm, student_performance: e.target.value})} className="w-full rounded-xl border-2 border-slate-200 px-3 py-2 text-sm" data-testid="proof-performance">
                <option value="excellent">Excellent</option><option value="good">Good</option><option value="average">Average</option><option value="needs_improvement">Needs Improvement</option>
              </select>
            </div>
            <div><Label>Feedback</Label><textarea value={proofForm.feedback_text} onChange={e => setProofForm({...proofForm, feedback_text: e.target.value})} className="w-full rounded-xl border-2 border-slate-200 px-3 py-2 text-sm" rows={3} data-testid="proof-feedback" /></div>
            <div>
              <Label>Screenshot (required)</Label>
              <div className="mt-1">
                {proofForm.screenshot_base64 ? (
                  <div className="relative">
                    <img src={proofForm.screenshot_base64} alt="Proof screenshot" className="w-full rounded-xl border-2 border-emerald-200 max-h-48 object-contain bg-slate-50" />
                    <button onClick={() => setProofForm({...proofForm, screenshot_base64: ''})} className="absolute top-2 right-2 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs hover:bg-red-600">X</button>
                  </div>
                ) : (
                  <label className="flex flex-col items-center justify-center w-full h-28 border-2 border-dashed border-slate-300 rounded-xl cursor-pointer hover:border-sky-400 hover:bg-sky-50 transition-colors" data-testid="proof-screenshot-upload">
                    <Camera className="w-8 h-8 text-slate-400 mb-1" />
                    <span className="text-sm text-slate-500">Click to upload screenshot</span>
                    <input type="file" accept="image/*" className="hidden" onChange={e => {
                      const file = e.target.files[0];
                      if (file) {
                        if (file.size > 5 * 1024 * 1024) { toast.error('Image must be under 5MB'); return; }
                        const reader = new FileReader();
                        reader.onload = () => setProofForm(prev => ({...prev, screenshot_base64: reader.result}));
                        reader.readAsDataURL(file);
                      }
                    }} />
                  </label>
                )}
              </div>
            </div>
            <Button onClick={handleSubmitProof} disabled={!proofForm.screenshot_base64} className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-full py-6 font-bold disabled:opacity-50" data-testid="submit-proof-btn">Submit Proof</Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Feedback Dialog */}
      <Dialog open={showFeedbackDialog} onOpenChange={setShowFeedbackDialog}>
        <DialogContent className="sm:max-w-md rounded-3xl">
          <DialogHeader><DialogTitle>Send Feedback to Student</DialogTitle></DialogHeader>
          <div className="space-y-3 mt-4">
            <div><Label>Rating</Label>
              <select value={feedbackForm.performance_rating} onChange={e => setFeedbackForm({...feedbackForm, performance_rating: e.target.value})} className="w-full rounded-xl border-2 border-slate-200 px-3 py-2 text-sm">
                <option value="excellent">Excellent</option><option value="good">Good</option><option value="average">Average</option><option value="needs_improvement">Needs Improvement</option>
              </select>
            </div>
            <div><Label>Feedback</Label><textarea value={feedbackForm.feedback_text} onChange={e => setFeedbackForm({...feedbackForm, feedback_text: e.target.value})} className="w-full rounded-xl border-2 border-slate-200 px-3 py-2 text-sm" rows={3} placeholder="Your feedback..." /></div>
            <Button onClick={handleSendFeedback} className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-full py-6 font-bold">Send Feedback</Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Reschedule Dialog */}
      <Dialog open={showRescheduleDialog} onOpenChange={setShowRescheduleDialog}>
        <DialogContent className="sm:max-w-md rounded-3xl">
          <DialogHeader><DialogTitle>Reschedule Session</DialogTitle></DialogHeader>
          {rescheduleTarget && (
            <div className="space-y-4 mt-4">
              <div className="bg-amber-50 rounded-xl p-3 border border-amber-200">
                <p className="font-semibold text-slate-900">{rescheduleTarget.title}</p>
              </div>
              <div><Label>New Date</Label><Input type="date" value={rescheduleForm.new_date} onChange={e => setRescheduleForm({...rescheduleForm, new_date: e.target.value})} className="rounded-xl" data-testid="reschedule-date" /></div>
              <div className="grid grid-cols-2 gap-3">
                <div><Label>Start</Label><Input type="time" value={rescheduleForm.new_start_time} onChange={e => setRescheduleForm({...rescheduleForm, new_start_time: e.target.value})} className="rounded-xl" /></div>
                <div><Label>End</Label><Input type="time" value={rescheduleForm.new_end_time} onChange={e => setRescheduleForm({...rescheduleForm, new_end_time: e.target.value})} className="rounded-xl" /></div>
              </div>
              <Button onClick={handleReschedule} className="w-full bg-amber-500 hover:bg-amber-600 text-white rounded-full py-6 font-bold" data-testid="confirm-reschedule-btn">Confirm Reschedule</Button>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Demo Feedback Dialog */}
      <Dialog open={showDemoFeedbackDialog} onOpenChange={setShowDemoFeedbackDialog}>
        <DialogContent className="sm:max-w-md rounded-3xl">
          <DialogHeader><DialogTitle>Demo Feedback (Required)</DialogTitle></DialogHeader>
          {demoFeedbackTarget && (
            <div className="space-y-4 mt-4">
              <div className="bg-violet-50 rounded-xl p-3 border border-violet-200">
                <p className="font-semibold text-slate-900">{demoFeedbackTarget.student_name || 'Student'}</p>
              </div>
              <div><Label>Rating</Label>
                <select value={demoFeedbackForm.performance_rating} onChange={e => setDemoFeedbackForm({...demoFeedbackForm, performance_rating: e.target.value})} className="w-full rounded-xl border-2 border-slate-200 px-3 py-2 text-sm" data-testid="demo-fb-rating">
                  <option value="excellent">Excellent</option><option value="good">Good</option><option value="average">Average</option><option value="needs_improvement">Needs Improvement</option>
                </select>
              </div>
              <div><Label>Recommended Frequency</Label>
                <select value={demoFeedbackForm.recommended_frequency} onChange={e => setDemoFeedbackForm({...demoFeedbackForm, recommended_frequency: e.target.value})} className="w-full rounded-xl border-2 border-slate-200 px-3 py-2 text-sm">
                  <option value="">Select...</option><option value="daily">Daily</option><option value="alternate_days">Alternate Days</option><option value="3_per_week">3 Per Week</option><option value="weekly">Weekly</option>
                </select>
              </div>
              <div><Label>Feedback (Required)</Label><textarea value={demoFeedbackForm.feedback_text} onChange={e => setDemoFeedbackForm({...demoFeedbackForm, feedback_text: e.target.value})} className="w-full rounded-xl border-2 border-slate-200 px-3 py-2 text-sm" rows={4} data-testid="demo-fb-text" /></div>
              <Button onClick={handleSubmitDemoFeedback} className="w-full bg-violet-500 hover:bg-violet-600 text-white rounded-full py-6 font-bold" data-testid="submit-demo-fb-btn">Submit Feedback</Button>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Notifications */}
      <Dialog open={showNotifDialog} onOpenChange={setShowNotifDialog}>
        <DialogContent className="sm:max-w-lg rounded-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <div className="flex items-center justify-between w-full">
              <DialogTitle>Notifications</DialogTitle>
              {unreadCount > 0 && <Button onClick={handleMarkAllRead} variant="outline" className="rounded-full text-xs">Mark all read</Button>}
            </div>
          </DialogHeader>
          <div className="space-y-3 mt-4">
            {notifications.length === 0 ? <p className="text-slate-500 text-center py-8">No notifications</p> : notifications.map(n => (
              <div key={n.notification_id} className={`rounded-xl p-4 border-2 ${n.read ? 'bg-slate-50 border-slate-200' : 'bg-sky-50 border-sky-200'}`}>
                <p className="font-semibold text-slate-900 text-sm">{n.title}</p>
                <p className="text-slate-600 text-sm">{n.message}</p>
                <p className="text-xs text-slate-400 mt-1">{new Date(n.created_at).toLocaleString()}</p>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>

      {/* Rating Dialog */}
      <Dialog open={showRatingDialog} onOpenChange={setShowRatingDialog}>
        <DialogContent className="sm:max-w-md rounded-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle className="flex items-center gap-2"><Star className="w-5 h-5 text-amber-500 fill-amber-500" /> My Rating & History</DialogTitle></DialogHeader>
          {ratingData && (
            <div className="space-y-4 mt-4">
              <div className="bg-amber-50 rounded-2xl p-5 text-center border border-amber-200">
                <p className="text-4xl font-black text-amber-700">{ratingData.star_rating?.toFixed(1)}<span className="text-lg">/5</span></p>
                {ratingData.is_suspended && <p className="text-red-600 font-bold mt-1">SUSPENDED until {new Date(ratingData.suspended_until).toLocaleDateString()}</p>}
              </div>
              <div className="grid grid-cols-2 gap-2 text-center">
                <div className="bg-slate-50 rounded-xl p-2"><p className="text-[10px] text-slate-500">Avg Feedback</p><p className="font-bold">{ratingData.rating_details?.avg_feedback?.toFixed(1) || '-'}</p></div>
                <div className="bg-slate-50 rounded-xl p-2"><p className="text-[10px] text-slate-500">Monthly Cancellations</p><p className="font-bold text-red-600">{ratingData.rating_details?.monthly_cancellations || 0}</p></div>
                <div className="bg-slate-50 rounded-xl p-2"><p className="text-[10px] text-slate-500">Bad Feedbacks</p><p className="font-bold text-red-600">{ratingData.rating_details?.bad_feedbacks || 0}</p></div>
                <div className="bg-slate-50 rounded-xl p-2"><p className="text-[10px] text-slate-500">Penalty</p><p className="font-bold text-red-600">-{ratingData.rating_details?.penalty?.toFixed(1) || 0}</p></div>
              </div>
              {ratingData.recent_events?.length > 0 && (
                <div>
                  <p className="text-sm font-bold text-slate-700 mb-2">Recent Events</p>
                  <div className="space-y-1.5 max-h-48 overflow-y-auto">
                    {ratingData.recent_events.map(e => (
                      <div key={e.event_id} className={`rounded-lg p-2 text-xs ${e.event === 'cancellation' ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700'}`}>
                        <span className="font-bold">{e.event === 'cancellation' ? 'Cancellation' : 'Bad Feedback'}</span>: {e.details}
                        <span className="text-slate-400 ml-2">{new Date(e.created_at).toLocaleDateString()}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      <ViewProfilePopup open={viewProfileOpen} onOpenChange={setViewProfileOpen} userId={viewProfileUserId} userRole={viewProfileRole} />

      {/* Attendance History Dialog */}
      <Dialog open={showAttendanceDialog} onOpenChange={setShowAttendanceDialog}>
        <DialogContent className="sm:max-w-2xl rounded-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle className="flex items-center gap-2"><CalendarCheck className="w-5 h-5 text-sky-500" /> Attendance History</DialogTitle></DialogHeader>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="text-left p-2 text-xs text-slate-500">Date</th>
                  <th className="text-left p-2 text-xs text-slate-500">Student</th>
                  <th className="text-center p-2 text-xs text-slate-500">Status</th>
                </tr>
              </thead>
              <tbody>
                {attendanceRecords.map((r, i) => (
                  <tr key={i} className="border-b border-slate-100">
                    <td className="p-2 text-xs">{r.date}</td>
                    <td className="p-2 text-xs font-semibold">{r.student_name}</td>
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
};

export default TeacherDashboard;
