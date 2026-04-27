import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';
import { GraduationCap, LogOut, Plus, Calendar, Users, AlertCircle, ShieldCheck, Upload, MessageSquare, Bell, Play, ChevronDown, ChevronUp, Zap, CreditCard, BookOpen, CalendarDays, Search, User, Star, AlertTriangle, XCircle, CheckCircle, Clock, Camera, CalendarCheck } from 'lucide-react';
import { getApiError, API } from '../utils/api';
import { ViewProfilePopup } from '../components/ViewProfilePopup';

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
  const [showAttendanceReasonDialog, setShowAttendanceReasonDialog] = useState(false);
  const [attendanceReasonData, setAttendanceReasonData] = useState(null);
  const [unmarkedAttendance, setUnmarkedAttendance] = useState([]);
  const [todayClassesForAttendance, setTodayClassesForAttendance] = useState({});
  const [expandedStudent, setExpandedStudent] = useState(null);
  const [studentDetail, setStudentDetail] = useState({}); // {studentId, date, status, availableClasses}

  const openProfile = (userId, role) => { setViewProfileUserId(userId); setViewProfileRole(role); setViewProfileOpen(true); };

  // Create class form
  const [classForm, setClassForm] = useState({
    title: '', subject: '', class_type: '1:1', date: '', start_time: '', end_time: '', max_students: 1, assigned_student_id: '', duration_days: 1, is_demo: false
  });

  useEffect(() => { fetchUser(); fetchDashboardData(); fetchNotifications(); fetchUnmarkedAttendance(); }, []);

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

  const fetchUnmarkedAttendance = async () => {
    try {
      const res = await fetch(`${API}/attendance/unmarked`, { credentials: 'include' });
      if (res.ok) setUnmarkedAttendance(await res.json());
    } catch {}
  };

  const fetchTodayClasses = async (studentId) => {
    try {
      const res = await fetch(`${API}/attendance/class-today/${studentId}`, { credentials: 'include' });
      if (res.ok) {
        const classes = await res.json();
        setTodayClassesForAttendance(prev => ({ ...prev, [studentId]: classes }));
      }
    } catch {}
  };

  const toggleStudentExpand = async (studentId) => {
    if (expandedStudent === studentId) { setExpandedStudent(null); return; }
    setExpandedStudent(studentId);
    if (!studentDetail[studentId]) {
      try {
        const res = await fetch(`${API}/teacher/student-detail/${studentId}`, { credentials: 'include' });
        if (res.ok) {
          const data = await res.json();
          setStudentDetail(prev => ({ ...prev, [studentId]: data }));
        }
      } catch {}
    }
    fetchTodayClasses(studentId);
  };

  const markAttendance = async (studentId, date, status, reason, classId) => {
    try {
      const payload = { student_id: studentId, date, status };
      if (reason) payload.reason = reason;
      if (classId) payload.class_id = classId;
      const res = await fetch(`${API}/attendance/mark`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error(await getApiError(res));
      const data = await res.json();
      if (data.needs_class_selection) {
        setAttendanceReasonData({ studentId, date, status, availableClasses: data.available_classes || [], step: 'select_class' });
        setShowAttendanceReasonDialog(true);
        return;
      }
      toast.success(data.message || `Attendance marked as ${status}`);
      setShowAttendanceReasonDialog(false);
      setAttendanceReasonData(null);
      // Refresh today's classes for this student to show already marked
      fetchTodayClasses(studentId);
      fetchUnmarkedAttendance();
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
    if (!window.confirm("Cancel today's session? You must reschedule before the next session can start.")) return;
    setCancellingClassId(classId);
    try {
      const res = await fetch(`${API}/teacher/cancel-class/${classId}`, { method: 'POST', credentials: 'include' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to cancel session');
      toast.success(data.message);
      if (data.needs_reschedule) {
        // Auto-open reschedule dialog
        const cls = [...(dashboardData?.todays_sessions || []), ...(dashboardData?.upcoming_classes || [])].find(c => c.class_id === classId);
        if (cls) { setRescheduleTarget(cls); setShowRescheduleDialog(true); }
      }
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
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        class_id: proofClass.class_id,
        ...proofForm
      })
    });

    if (!res.ok) throw new Error(await getApiError(res));

    toast.success('Proof submitted!');

    // ✅ CLOSE + RESET
    setShowProofDialog(false);
    setProofClass(null);
    setProofForm({
      feedback_text: '',
      student_performance: 'good',
      topics_covered: '',
      screenshot_base64: ''
    });

    // ✅ THIS IS THE IMPORTANT LINE
    await fetchDashboardData();

  } catch (err) {
    toast.error(err.message);
  }
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
  const cancelledClasses = dashboardData?.cancelled_classes || [];

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

        {cancellations > 0 && <div className="bg-amber-50 border border-amber-200 rounded-lg p-1.5 mb-2 text-xs text-amber-800 font-semibold">Cancelled {cancellations} session(s)</div>}
        {cls.needs_reschedule && (
          <div className="bg-red-50 rounded-lg p-2 text-center text-xs text-red-700 font-semibold border border-red-200 mb-2">
            <AlertCircle className="w-3 h-3 inline mr-1" /> Must reschedule before next session
          </div>
        )}
        {cls.cancelled_today && !cls.needs_reschedule && (
          <div className="bg-red-50 rounded-lg p-2 text-center text-xs text-red-700 font-semibold border border-red-200 mb-2">
            <AlertCircle className="w-3 h-3 inline mr-1" /> Session cancelled
          </div>
        )}
        {(cls.cancelled_today || cls.needs_reschedule) && (
          <Button onClick={() => { setRescheduleTarget(cls); setShowRescheduleDialog(true); }} className="w-full bg-amber-500 hover:bg-amber-600 text-white rounded-full text-xs h-7 mb-2" data-testid={`reschedule-${cls.class_id}`}>
            <CalendarDays className="w-3 h-3 mr-1" /> Reschedule Session
          </Button>
        )}

        <div className="space-y-1.5">
          {(() => {
            // Time-based Start Class button logic
            const now = new Date();
            const istOffset = 5.5 * 60 * 60 * 1000;
            const nowIST = new Date(now.getTime() + istOffset);
            const currentMin = nowIST.getUTCHours() * 60 + nowIST.getUTCMinutes();
            const startParts = (cls.start_time || '').split(':');
            const endParts = (cls.end_time || '').split(':');
            const startMin = parseInt(startParts[0] || 0) * 60 + parseInt(startParts[1] || 0);
            const endMin = parseInt(endParts[0] || 0) * 60 + parseInt(endParts[1] || 0);
            const canStart = currentMin >= startMin - 5 && currentMin <= endMin;
            const classTimeEnded = currentMin > endMin;
            const isToday = section === 'today';

            return (
              <>
                {/* Start Class - only within time window */}
                {cls.status === 'scheduled' && !cls.cancelled_today && !cls.needs_reschedule && isToday && (
                  canStart ? (
                    <Button onClick={() => navigate(`/class/${cls.class_id}`)} className="w-full bg-emerald-500 hover:bg-emerald-600 text-white rounded-full font-bold text-sm h-8" data-testid={`start-class-${cls.class_id}`}>
                      <Play className="w-3 h-3 mr-1" /> Start Class
                    </Button>
                  ) : classTimeEnded ? (
                    <div className="bg-red-50 rounded-lg p-2 text-center text-xs text-red-700 font-semibold border border-red-200">
                      Class time ended — auto-cancelled
                    </div>
                  ) : (
                    <Button disabled className="w-full bg-slate-200 text-slate-400 rounded-full font-bold text-sm h-8 cursor-not-allowed" data-testid={`start-class-disabled-${cls.class_id}`}>
                      <Play className="w-3 h-3 mr-1" /> Starts at {cls.start_time}
                    </Button>
                  )
                )}
                {/* For upcoming, show faded button */}
                {cls.status === 'scheduled' && !cls.cancelled_today && !cls.needs_reschedule && !isToday && (
                  <Button disabled className="w-full bg-slate-200 text-slate-400 rounded-full font-bold text-sm h-8 cursor-not-allowed">
                    <Play className="w-3 h-3 mr-1" /> Starts {cls.date} at {cls.start_time}
                  </Button>
                )}
                {/* Rejoin live */}
                {isLive && !cls.cancelled_today && (
                  <Button onClick={() => navigate(`/class/${cls.class_id}`)} className="w-full bg-emerald-500 hover:bg-emerald-600 text-white rounded-full font-bold text-sm h-8 animate-pulse" data-testid={`rejoin-class-${cls.class_id}`}>
                    <Play className="w-3 h-3 mr-1" /> Rejoin Live
                  </Button>
                )}
                {/* Proof button: after class time ends OR class completed */}
                {(section === 'conducted' || (isToday && (cls.status === 'completed' || classTimeEnded))) && cls.status !== 'cancelled' && !cls.proof_submitted && (
                  <Button onClick={() => { setProofClass(cls); setShowProofDialog(true); }} variant="outline" className="w-full rounded-full text-xs h-7" data-testid={`submit-proof-${cls.class_id}`}><Upload className="w-3 h-3 mr-1" /> Submit Today's Proof</Button>
                )}
                {(section === 'conducted' || section === 'today') && cls.proof_submitted && (
                  <div className="bg-emerald-50 border border-emerald-200 rounded-full px-3 py-1 text-center text-xs text-emerald-700 font-medium" data-testid={`proof-submitted-${cls.class_id}`}>
                    <CheckCircle className="w-3 h-3 inline mr-1" />Today's Proof Submitted
                    {cls.total_proofs > 0 && cls.duration_days > 1 && <span className="ml-1">({cls.total_proofs}/{cls.duration_days} days)</span>}
                  </div>
                )}
                {/* Cancel button: only if class NOT started and time hasn't ended */}
                {isToday && cls.status === 'scheduled' && !cls.cancelled_today && !cls.needs_reschedule && !isLive && !classTimeEnded && (
                  <Button onClick={() => handleTeacherCancelClass(cls.class_id)} disabled={cancellingClassId === cls.class_id} variant="outline" className="w-full rounded-full text-xs h-7 border-red-200 text-red-600 hover:bg-red-50 disabled:opacity-40 disabled:cursor-not-allowed" data-testid={`teacher-cancel-${cls.class_id}`}><XCircle className="w-3 h-3 mr-1" /> {cancellingClassId === cls.class_id ? 'Cancelling...' : "Cancel Today's Session"}</Button>
                )}
              </>
            );
          })()}
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

        {/* Awaiting Payment - students accepted but haven't paid yet */}
        {dashboardData?.awaiting_payment?.length > 0 && (
          <div className="mb-8" data-testid="awaiting-payment-section">
            <h2 className="text-lg font-bold text-orange-700 mb-3 flex items-center gap-2"><Clock className="w-5 h-5 text-orange-500" /> Awaiting Student Payment ({dashboardData.awaiting_payment.length})</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {dashboardData.awaiting_payment.map(a => (
                <div key={a.assignment_id} className="bg-orange-50 rounded-2xl border-2 border-orange-200 p-5" data-testid={`awaiting-payment-${a.assignment_id}`}>
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-bold text-slate-900">{a.student_name}</h3>
                      <p className="text-sm text-slate-600">{a.student_email}</p>
                      {a.learning_plan_name && <p className="text-xs text-sky-700 mt-1">Plan: {a.learning_plan_name}</p>}
                      {a.counselor_name && <p className="text-xs text-slate-400 mt-0.5">Assigned by: {a.counselor_name}</p>}
                    </div>
                    <span className="bg-orange-200 text-orange-800 px-3 py-1 rounded-full text-xs font-bold whitespace-nowrap">Payment Pending</span>
                  </div>
                  <p className="text-xs text-slate-500 mt-3">You accepted this student. Waiting for them to complete payment before you can schedule a class.</p>
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
            <TabsTrigger value="cancelled" data-testid="tab-cancelled">Cancelled ({cancelledClasses.length})</TabsTrigger>
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

          <TabsContent value="cancelled">
            {cancelledClasses.length === 0 ? (
              <div className="bg-white rounded-3xl p-8 border-2 border-slate-100 text-center"><p className="text-slate-500">No cancelled classes</p></div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {cancelledClasses.map(cls => (
                  <div key={cls.class_id} className="bg-red-50 rounded-2xl border-2 border-red-200 p-4" data-testid={`cancelled-class-${cls.class_id}`}>
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <h3 className="font-bold text-slate-900 text-sm">{cls.title}</h3>
                        <p className="text-xs text-slate-600">{cls.subject} | {cls.class_type}</p>
                        <p className="text-xs text-slate-500">{cls.date} {cls.start_time}-{cls.end_time}</p>
                      </div>
                      <div className="flex flex-col items-end gap-1">
                        <span className="bg-red-200 text-red-800 px-2 py-0.5 rounded-full text-[10px] font-bold">CANCELLED</span>
                        {cls.rescheduled && <span className="bg-amber-200 text-amber-800 px-2 py-0.5 rounded-full text-[10px] font-bold">RESCHEDULED</span>}
                      </div>
                    </div>
                    <p className="text-xs text-red-600 mb-2">Cancelled by: {cls.cancelled_by || 'teacher'}</p>
                    {cls.can_reschedule && !cls.rescheduled && (
                      <Button onClick={() => { setRescheduleTarget(cls); setShowRescheduleDialog(true); }}
                        className="w-full bg-amber-500 hover:bg-amber-600 text-white rounded-full text-xs h-8" data-testid={`reschedule-cancelled-${cls.class_id}`}>
                        <CalendarDays className="w-3 h-3 mr-1" /> Reschedule This Class
                      </Button>
                    )}
                    {cls.rescheduled && (
                      <div className="bg-amber-50 border border-amber-200 rounded-lg p-2 mt-1">
                        <p className="text-xs text-amber-800 font-semibold">Rescheduled to: {cls.rescheduled_date} {cls.rescheduled_start_time}-{cls.rescheduled_end_time}</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>

        {/* My Students — expandable per-student cards */}
        {dashboardData?.approved_students?.length > 0 && (
          <div className="mb-8">
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2 mb-3"><Users className="w-5 h-5 text-sky-500" /> My Students ({dashboardData.approved_students.length})</h2>
            <div className="space-y-2">
              {dashboardData.approved_students.map(s => {
                const isExpanded = expandedStudent === s.student_id;
                const detail = studentDetail[s.student_id];
                const unmarkedForStudent = unmarkedAttendance.filter(u => u.student_id === s.student_id);
                const todayClasses = todayClassesForAttendance[s.student_id] || [];
                return (
                  <div key={s.assignment_id} className="bg-white rounded-xl border border-slate-200 overflow-hidden" data-testid={`student-card-${s.student_id}`}>
                    <button onClick={() => toggleStudentExpand(s.student_id)} className="w-full p-3 flex items-center justify-between hover:bg-slate-50 transition-colors text-left">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-full bg-sky-100 flex items-center justify-center text-sky-700 font-bold text-sm">{s.student_name?.charAt(0)}</div>
                        <div>
                          <p className="font-semibold text-slate-900 text-sm">{s.student_name}</p>
                          <p className="text-xs text-slate-500">{s.student_email}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {unmarkedForStudent.length > 0 && <span className="bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full text-[10px] font-bold">{unmarkedForStudent.length} unmarked</span>}
                        {s.learning_plan_name && <span className="text-[10px] text-sky-700 bg-sky-50 px-2 py-0.5 rounded-full">{s.learning_plan_name}</span>}
                        <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                      </div>
                    </button>
                    {isExpanded && (
                      <div className="border-t border-slate-100 p-3 bg-slate-50 space-y-3">
                        {unmarkedForStudent.length > 0 && (
                          <div className="bg-amber-50 border border-amber-200 rounded-lg p-2 text-xs text-amber-800">
                            <AlertCircle className="w-3 h-3 inline mr-1" /><strong>{unmarkedForStudent.length} unmarked day(s)</strong>
                            <div className="mt-1 space-y-1">
                              {unmarkedForStudent.slice(0, 5).map(u => (
                                <div key={`${u.class_id}-${u.date}`} className="flex items-center gap-1.5">
                                  <span className="text-[10px] text-slate-600">{u.date} — {u.class_title}</span>
                                  <Button onClick={() => markAttendance(u.student_id, u.date, 'present', 'forgot_to_mark', u.class_id)} size="sm" variant="outline" className="rounded-full h-5 px-2 text-[10px]"><CheckCircle className="w-2.5 h-2.5 text-emerald-500 mr-0.5" /> P</Button>
                                  <Button onClick={() => markAttendance(u.student_id, u.date, 'absent', 'forgot_to_mark', u.class_id)} size="sm" variant="outline" className="rounded-full h-5 px-2 text-[10px]"><XCircle className="w-2.5 h-2.5 text-red-500 mr-0.5" /> A</Button>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                        {todayClasses.length > 0 && (
                          <div>
                            <p className="text-xs font-bold text-slate-700 mb-1">Today's Attendance</p>
                            {todayClasses.map(cls => (
                              <div key={cls.class_id} className="flex items-center gap-2 mb-1">
                                <span className="text-xs text-slate-600">{cls.title}</span>
                                {cls.already_marked ? (
                                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${cls.marked_status === 'present' ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>{cls.marked_status}</span>
                                ) : (
                                  <div className="flex gap-1">
                                    <Button onClick={() => markAttendance(s.student_id, new Date().toISOString().split('T')[0], 'present', null, cls.class_id)} variant="outline" className="rounded-full text-[10px] h-6 px-2"><CheckCircle className="w-3 h-3 text-emerald-500 mr-0.5" /> Present</Button>
                                    <Button onClick={() => markAttendance(s.student_id, new Date().toISOString().split('T')[0], 'absent', null, cls.class_id)} variant="outline" className="rounded-full text-[10px] h-6 px-2"><XCircle className="w-3 h-3 text-red-500 mr-0.5" /> Absent</Button>
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                        {detail?.classes?.length > 0 && (
                          <div>
                            <p className="text-xs font-bold text-slate-700 mb-1">Classes ({detail.classes.length})</p>
                            <div className="space-y-1">
                              {detail.classes.map(c => (
                                <div key={c.class_id} className="flex items-center justify-between bg-white rounded-lg px-2 py-1.5 text-xs">
                                  <span className="font-medium">{c.title} <span className="text-slate-400">{c.date} | {c.sessions_conducted || 0}/{c.duration_days}d</span></span>
                                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${c.status === 'completed' ? 'bg-emerald-100 text-emerald-700' : c.status === 'scheduled' ? 'bg-sky-100 text-sky-700' : 'bg-slate-100 text-slate-700'}`}>{c.status}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                        {detail?.attendance?.length > 0 && (
                          <div>
                            <p className="text-xs font-bold text-slate-700 mb-1">Attendance ({detail.attendance.length})</p>
                            <div className="max-h-32 overflow-y-auto space-y-0.5">
                              {detail.attendance.map((a, i) => (
                                <div key={i} className="flex items-center justify-between bg-white rounded px-2 py-1 text-[10px]">
                                  <span>{a.date} {a.class_title && <span className="text-sky-700 ml-1">{a.class_title}</span>}</span>
                                  <span className={`px-1.5 py-0.5 rounded font-bold ${a.status === 'present' ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>{a.status}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                        <Button onClick={() => { setFeedbackTarget({ student_id: s.student_id }); setShowFeedbackDialog(true); }} variant="outline" className="rounded-full text-xs h-7 px-3"><MessageSquare className="w-3 h-3 mr-1" /> Feedback</Button>
                      </div>
                    )}
                  </div>
                );
              })}
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
                {(dashboardData?.approved_students || [])
                  .filter(s => s.payment_status === 'paid')   // ✅ IMPORTANT
                  .map(s => <option key={s.student_id} value={s.student_id}>{s.student_name} {s.assigned_days ? `(${s.assigned_days} days assigned)` : ''}</option>)}
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

      {/* Attendance Class Selection Dialog - when no class on this date */}
      <Dialog open={showAttendanceReasonDialog} onOpenChange={setShowAttendanceReasonDialog}>
        <DialogContent className="sm:max-w-md rounded-3xl">
          <DialogHeader><DialogTitle className="text-xl font-bold flex items-center gap-2"><AlertCircle className="w-5 h-5 text-amber-500" /> Select Class for Attendance</DialogTitle></DialogHeader>
          {attendanceReasonData && (
            <div className="space-y-4 mt-4">
              <p className="text-sm text-slate-600">No class scheduled on {attendanceReasonData.date}. Select which class this attendance is for:</p>
              <div className="space-y-2">
                <Button onClick={() => setAttendanceReasonData({ ...attendanceReasonData, reason: 'forgot_to_mark' })} variant={attendanceReasonData.reason === 'forgot_to_mark' ? 'default' : 'outline'} className="w-full rounded-xl py-3 text-left justify-start" data-testid="reason-forgot">
                  <Clock className="w-4 h-4 mr-2 text-amber-500" /> Forgot to mark earlier
                </Button>
                <Button onClick={() => setAttendanceReasonData({ ...attendanceReasonData, reason: 'rescheduled_class' })} variant={attendanceReasonData.reason === 'rescheduled_class' ? 'default' : 'outline'} className="w-full rounded-xl py-3 text-left justify-start" data-testid="reason-rescheduled">
                  <CalendarDays className="w-4 h-4 mr-2 text-sky-500" /> Rescheduled class
                </Button>
              </div>
              {attendanceReasonData.reason && (
                <div className="space-y-2 mt-3">
                  <p className="text-sm font-semibold text-slate-700">Select the class:</p>
                  {(attendanceReasonData.availableClasses || []).map(cls => (
                    <Button key={cls.class_id} onClick={() => {
                      markAttendance(attendanceReasonData.studentId, attendanceReasonData.date, attendanceReasonData.status, attendanceReasonData.reason, cls.class_id);
                    }} variant="outline" className="w-full rounded-xl py-3 text-left justify-start" data-testid={`select-class-${cls.class_id}`}>
                      {cls.title} ({cls.date} - {cls.end_date})
                    </Button>
                  ))}
                  {(attendanceReasonData.availableClasses || []).length === 0 && (
                    <p className="text-sm text-red-500">No active classes found for this student.</p>
                  )}
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

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
                  <th className="text-left p-2 text-xs text-slate-500">Class</th>
                  <th className="text-center p-2 text-xs text-slate-500">Status</th>
                  <th className="text-left p-2 text-xs text-slate-500">Notes</th>
                </tr>
              </thead>
              <tbody>
                {attendanceRecords.map((r, i) => (
                  <tr key={i} className={`border-b border-slate-100 ${r.off_day_marking ? 'bg-amber-50' : ''}`}>
                    <td className="p-2 text-xs">{r.date}</td>
                    <td className="p-2 text-xs font-semibold">{r.student_name}</td>
                    <td className="p-2 text-xs text-sky-700">{r.class_title || '-'}</td>
                    <td className="p-2 text-center">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${r.status === 'present' ? 'bg-emerald-100 text-emerald-700' : r.status === 'absent' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}`}>{r.status}</span>
                    </td>
                    <td className="p-2 text-xs text-slate-500">
                      {r.off_day_marking && <span className="text-amber-600 font-semibold">Off-day</span>}
                      {r.reason === 'forgot_to_mark' && <span> (Forgot)</span>}
                      {r.reason === 'rescheduled_class' && <span> (Rescheduled)</span>}
                    </td>
                  </tr>
                ))}
                {attendanceRecords.length === 0 && (
                  <tr><td colSpan="5" className="text-center p-8 text-slate-400">No attendance records yet</td></tr>
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
