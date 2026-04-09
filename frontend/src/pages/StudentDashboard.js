import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { toast } from 'sonner';
import { GraduationCap, LogOut, Calendar, CreditCard, BookOpen, Play, MessageSquare, Bell, AlertCircle, Lock, Star, Clock, User, XCircle } from 'lucide-react';

const BACKEND = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND}/api`;

const StudentDashboard = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [classes, setClasses] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [enrollment, setEnrollment] = useState(null);
  const [demoFeedbacks, setDemoFeedbacks] = useState([]);
  const [showNotifDialog, setShowNotifDialog] = useState(false);
  const [showProfileDialog, setShowProfileDialog] = useState(false);
  const [showFeedbackDialog, setShowFeedbackDialog] = useState(false);
  const [profileForm, setProfileForm] = useState({});

  useEffect(() => { fetchData(); }, []);

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
      if (dashRes.ok) { const d = await dashRes.json(); setClasses(d.my_classes || []); }
      if (notifRes.ok) setNotifications(await notifRes.json());
      if (enrollRes.ok) setEnrollment(await enrollRes.json());
      if (feedbackRes.ok) setDemoFeedbacks(await feedbackRes.json());
    } catch { toast.error('Failed to load dashboard'); }
    setLoading(false);
  };

  const handleLogout = async () => { await fetch(`${API}/auth/logout`, { method: 'POST', credentials: 'include' }); navigate('/login'); };
  const handleMarkAllRead = async () => { await fetch(`${API}/notifications/mark-all-read`, { method: 'POST', credentials: 'include' }); fetchData(); };
  const unreadCount = notifications.filter(n => !n.read).length;

  const handleUpdateProfile = async () => {
    try {
      const res = await fetch(`${API}/student/update-profile`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(profileForm)
      });
      if (!res.ok) throw new Error((await res.json()).detail);
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
      if (!res.ok) throw new Error((await res.json()).detail);
      toast.success("Session cancelled. Teacher will reschedule.");
      fetchData();
    } catch (err) { toast.error(err.message); }
  };

  if (loading) return <div className="min-h-screen flex items-center justify-center bg-slate-50"><div className="w-16 h-16 border-4 border-sky-500 border-t-transparent rounded-full animate-spin" /></div>;

  const isEnrolled = enrollment?.is_enrolled;
  const demoCompleted = enrollment?.demo_completed;
  const hasTeacher = enrollment?.has_approved_teacher;

  // ─── LOCKED VIEW (not enrolled) ───
  if (!isEnrolled) {
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
                  : "Your demo is complete! A counsellor will assign you to a teacher soon."}
            </p>
            <div className="flex gap-3 justify-center">
              {!demoCompleted && (
                <Button onClick={() => navigate('/book-demo')} className="bg-amber-400 hover:bg-amber-500 text-slate-900 rounded-full px-8 py-6 font-bold text-lg" data-testid="book-demo-button">Book a Free Demo</Button>
              )}
              <Button onClick={() => setShowProfileDialog(true)} variant="outline" className="rounded-full px-6 py-6" data-testid="edit-profile-button"><User className="w-4 h-4 mr-2" /> My Profile</Button>
              <Button onClick={() => navigate('/wallet')} variant="outline" className="rounded-full px-6 py-6" data-testid="wallet-button"><CreditCard className="w-4 h-4 mr-2" /> Wallet</Button>
            </div>
          </div>

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
          <Button onClick={() => setShowFeedbackDialog(true)} variant="outline" className="rounded-full" data-testid="feedback-button"><Star className="w-4 h-4 mr-2" /> Demo Feedback</Button>
        </div>

        {/* Active Classes */}
        <h2 className="text-xl font-bold text-slate-900 mb-4 flex items-center gap-2"><Calendar className="w-5 h-5 text-sky-500" /> My Classes ({classes.length})</h2>
        {classes.length === 0 ? (
          <div className="bg-white rounded-3xl p-12 border-2 border-slate-100 text-center">
            <p className="text-slate-500">No active classes. Your teacher will create classes for you.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {classes.map(cls => {
              const isLive = cls.status === 'in_progress';
              const isCancelledToday = cls.cancelled_today;
              const isRescheduled = cls.rescheduled;
              return (
                <div key={cls.class_id} className={`bg-white rounded-2xl border-2 p-5 ${isLive ? 'border-emerald-400 ring-2 ring-emerald-200' : 'border-slate-200'}`} data-testid={`class-card-${cls.class_id}`}>
                  <div className="flex gap-2 flex-wrap mb-2">
                    <span className="bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full text-xs font-semibold">{cls.subject}</span>
                    {cls.is_demo && <span className="bg-violet-100 text-violet-800 px-2 py-0.5 rounded-full text-xs font-semibold">DEMO</span>}
                    {isLive && <span className="bg-emerald-500 text-white px-2 py-0.5 rounded-full text-xs font-semibold animate-pulse">LIVE</span>}
                    {isCancelledToday && <span className="bg-red-100 text-red-800 px-2 py-0.5 rounded-full text-xs font-semibold">Session Cancelled</span>}
                    {isRescheduled && <span className="bg-sky-100 text-sky-800 px-2 py-0.5 rounded-full text-xs font-semibold">Rescheduled</span>}
                  </div>
                  <h3 className="text-base font-bold text-slate-900 mb-1">{cls.title}</h3>
                  <div className="text-xs text-slate-600 space-y-0.5 mb-3">
                    <p className="flex items-center gap-1"><Calendar className="w-3 h-3" /> {cls.date} - {cls.end_date || cls.date}</p>
                    <p className="flex items-center gap-1"><Clock className="w-3 h-3" /> {cls.start_time} - {cls.end_time}</p>
                    {cls.rescheduled_date && <p className="text-sky-600 font-semibold">Rescheduled: {cls.rescheduled_date} {cls.rescheduled_start_time}-{cls.rescheduled_end_time}</p>}
                  </div>
                  {cls.cancellation_count > 0 && (
                    <p className="text-xs text-amber-700 bg-amber-50 rounded-lg p-1.5 mb-2">Cancelled {cls.cancellation_count}/{cls.max_cancellations || 3} sessions</p>
                  )}
                  <div className="space-y-1.5">
                    {isLive && !isCancelledToday && (
                      <Button onClick={() => navigate(`/class/${cls.class_id}`)} className="w-full bg-emerald-500 hover:bg-emerald-600 text-white rounded-full font-bold animate-pulse" data-testid={`join-live-${cls.class_id}`}>
                        <Play className="w-4 h-4 mr-2" /> Join Live Class
                      </Button>
                    )}
                    {isCancelledToday && (
                      <div className="bg-red-50 rounded-xl p-3 text-center text-sm text-red-700 font-medium">
                        <AlertCircle className="w-4 h-4 inline mr-1" /> Waiting for teacher to reschedule
                      </div>
                    )}
                    {!isLive && !isCancelledToday && cls.status === 'scheduled' && (
                      <Button onClick={() => handleCancelSession(cls.class_id)} variant="outline" className="w-full rounded-full border-red-200 text-red-600 text-xs" data-testid={`cancel-session-${cls.class_id}`}>
                        <XCircle className="w-3 h-3 mr-1" /> Cancel Today's Session
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Demo Feedback Dialog */}
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
            <div className="grid grid-cols-2 gap-3">
              <div><Label>Phone</Label><Input value={profileForm.phone} onChange={e => setProfileForm({...profileForm, phone: e.target.value})} className="rounded-xl" data-testid="profile-phone" /></div>
              <div><Label>Grade</Label>
                <select value={profileForm.grade} onChange={e => setProfileForm({...profileForm, grade: e.target.value})} className="w-full rounded-xl border-2 border-slate-200 px-3 py-2 bg-white h-10 text-sm" data-testid="profile-grade">
                  <option value="">Select...</option>
                  {['1','2','3','4','5','6','7','8','9','10','11','12','UG','PG','Other'].map(g => <option key={g} value={g}>{g === 'UG' || g === 'PG' || g === 'Other' ? g : `Class ${g}`}</option>)}
                </select>
              </div>
              <div><Label>State</Label><Input value={profileForm.state} onChange={e => setProfileForm({...profileForm, state: e.target.value})} className="rounded-xl" data-testid="profile-state" /></div>
              <div><Label>City</Label><Input value={profileForm.city} onChange={e => setProfileForm({...profileForm, city: e.target.value})} className="rounded-xl" data-testid="profile-city" /></div>
              <div><Label>Country</Label><Input value={profileForm.country} onChange={e => setProfileForm({...profileForm, country: e.target.value})} className="rounded-xl" data-testid="profile-country" /></div>
              <div><Label>Institute</Label><Input value={profileForm.institute} onChange={e => setProfileForm({...profileForm, institute: e.target.value})} className="rounded-xl" data-testid="profile-institute" /></div>
            </div>
            <div><Label>Goal</Label><Input value={profileForm.goal} onChange={e => setProfileForm({...profileForm, goal: e.target.value})} className="rounded-xl" data-testid="profile-goal" /></div>
            <div><Label>Preferred Time</Label>
              <Input type="datetime-local" value={profileForm.preferred_time_slot?.split(' to ')[0] || ''} onChange={e => setProfileForm({...profileForm, preferred_time_slot: e.target.value})} className="rounded-xl" data-testid="profile-time" />
            </div>
            <Button onClick={handleUpdateProfile} className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-full py-6 font-bold" data-testid="save-profile-button">Save Profile</Button>
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
