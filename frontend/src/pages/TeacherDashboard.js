import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { toast } from 'sonner';
import { GraduationCap, LogOut, Plus, Calendar, Users, AlertCircle, ShieldCheck, Upload, MessageSquare, Bell, Play, ChevronDown, ChevronUp, Zap, CreditCard, BookOpen, CalendarDays } from 'lucide-react';
import { format, parseISO } from 'date-fns';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const TeacherDashboard = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [groupedData, setGroupedData] = useState({ today: [], by_student: [], ended_count: 0 });
  const [pendingAssignments, setPendingAssignments] = useState([]);
  const [approvedStudents, setApprovedStudents] = useState([]);
  const [proofs, setProofs] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [studentComplaints, setStudentComplaints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showProofDialog, setShowProofDialog] = useState(false);
  const [showNotifDialog, setShowNotifDialog] = useState(false);
  const [selectedClassForProof, setSelectedClassForProof] = useState(null);
  const [expandedStudent, setExpandedStudent] = useState(null);
  const [studentSearch, setStudentSearch] = useState('');
  const [showFeedbackDialog, setShowFeedbackDialog] = useState(false);
  const [feedbackTarget, setFeedbackTarget] = useState(null);
  const [feedbackForm, setFeedbackForm] = useState({ feedback_text: '', performance_rating: 'good' });
  const [formData, setFormData] = useState({
    title: '', subject: '', class_type: '1:1', date: '', start_time: '', end_time: '',
    max_students: '1', assigned_student_id: '', duration_days: '1', is_demo: false
  });
  const [proofData, setProofData] = useState({
    feedback_text: '', student_performance: 'good', topics_covered: '', screenshot_base64: null
  });

  useEffect(() => { fetchDashboardData(); }, []);

  const fetchDashboardData = async () => {
    try {
      const [userRes, dashboardRes, proofsRes, notifRes, complaintsRes, groupedRes] = await Promise.all([
        fetch(`${API}/auth/me`, { credentials: 'include' }),
        fetch(`${API}/teacher/dashboard`, { credentials: 'include' }),
        fetch(`${API}/teacher/my-proofs`, { credentials: 'include' }),
        fetch(`${API}/notifications/my`, { credentials: 'include' }),
        fetch(`${API}/teacher/student-complaints`, { credentials: 'include' }),
        fetch(`${API}/teacher/grouped-classes`, { credentials: 'include' })
      ]);
      if (!userRes.ok || !dashboardRes.ok) throw new Error('Failed to fetch data');
      setUser(await userRes.json());
      const dashboardData = await dashboardRes.json();
      setPendingAssignments(dashboardData.pending_assignments || []);
      setApprovedStudents(dashboardData.approved_students || []);
      if (proofsRes.ok) setProofs(await proofsRes.json());
      if (notifRes.ok) setNotifications(await notifRes.json());
      if (complaintsRes.ok) setStudentComplaints(await complaintsRes.json());
      if (groupedRes.ok) setGroupedData(await groupedRes.json());
      setLoading(false);
    } catch (error) {
      toast.error('Failed to load dashboard');
      setLoading(false);
    }
  };

  const handleCreateClass = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch(`${API}/classes/create`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
        body: JSON.stringify({
          ...formData, max_students: parseInt(formData.max_students),
          duration_days: parseInt(formData.duration_days), is_demo: formData.is_demo
        })
      });
      if (!response.ok) throw new Error((await response.json()).detail);
      toast.success('Class created!');
      setShowCreateDialog(false);
      setFormData({ title: '', subject: '', class_type: '1:1', date: '', start_time: '', end_time: '', max_students: '1', assigned_student_id: '', duration_days: '1', is_demo: false });
      fetchDashboardData();
    } catch (error) { toast.error(error.message); }
  };

  const handleApproveAssignment = async (assignmentId, approved) => {
    try {
      const response = await fetch(`${API}/teacher/approve-assignment`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
        body: JSON.stringify({ assignment_id: assignmentId, approved })
      });
      if (!response.ok) throw new Error((await response.json()).detail);
      toast.success(approved ? 'Student approved!' : 'Student rejected');
      fetchDashboardData();
    } catch (error) { toast.error(error.message); }
  };

  const handleDeleteClass = async (classId) => {
    if (!window.confirm('Delete this class?')) return;
    try {
      const response = await fetch(`${API}/classes/delete/${classId}`, { method: 'DELETE', credentials: 'include' });
      if (!response.ok) throw new Error((await response.json()).detail);
      toast.success('Class deleted');
      fetchDashboardData();
    } catch (error) { toast.error(error.message); }
  };

  const handleSubmitProof = async () => {
    if (!proofData.feedback_text || !proofData.topics_covered) { toast.error('Fill all required fields'); return; }
    try {
      const response = await fetch(`${API}/teacher/submit-proof`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
        body: JSON.stringify({ class_id: selectedClassForProof.class_id, ...proofData })
      });
      if (!response.ok) throw new Error((await response.json()).detail);
      toast.success('Proof submitted!');
      setShowProofDialog(false);
      setSelectedClassForProof(null);
      setProofData({ feedback_text: '', student_performance: 'good', topics_covered: '', screenshot_base64: null });
      fetchDashboardData();
    } catch (error) { toast.error(error.message); }
  };

  const handleScreenshotUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) { toast.error('Max 2MB'); return; }
    const reader = new FileReader();
    reader.onload = () => setProofData({ ...proofData, screenshot_base64: reader.result });
    reader.readAsDataURL(file);
  };

  const handleMarkAllRead = async () => {
    await fetch(`${API}/notifications/mark-all-read`, { method: 'POST', credentials: 'include' });
    fetchDashboardData();
  };

  const handleLogout = async () => {
    try { await fetch(`${API}/auth/logout`, { method: 'POST', credentials: 'include' }); navigate('/login'); } catch {}
  };

  const getProofStatus = (classId) => proofs.find(p => p.class_id === classId);
  const unreadCount = notifications.filter(n => !n.read).length;

  const renderClassCard = (cls) => {
    const proof = getProofStatus(cls.class_id);
    const cancellations = cls.cancellation_count || 0;
    const isLive = cls.status === 'in_progress';
    return (
      <div key={cls.class_id} className={`bg-white rounded-3xl border-2 shadow-[4px_4px_0px_0px_rgba(226,232,240,1)] p-6 ${isLive ? 'border-emerald-400 ring-2 ring-emerald-200' : 'border-slate-200'}`} data-testid={`class-card-${cls.class_id}`}>
        <div className="flex items-start justify-between mb-3">
          <div className="flex gap-2 flex-wrap">
            <span className="bg-amber-100 text-amber-800 px-3 py-1 rounded-full text-xs font-semibold">{cls.subject}</span>
            {cls.is_demo && <span className="bg-violet-100 text-violet-800 px-3 py-1 rounded-full text-xs font-semibold">DEMO</span>}
            {isLive && <span className="bg-emerald-500 text-white px-3 py-1 rounded-full text-xs font-semibold animate-pulse">LIVE</span>}
            {cls.status === 'dismissed' && <span className="bg-red-100 text-red-800 px-3 py-1 rounded-full text-xs font-semibold">DISMISSED</span>}
          </div>
        </div>
        <h3 className="text-xl font-bold text-slate-900 mb-2">{cls.title}</h3>
        <div className="space-y-1 mb-3 text-sm text-slate-600">
          <div className="flex items-center gap-2"><Calendar className="w-4 h-4" /><span>{format(parseISO(cls.date), 'MMM dd')} - {cls.end_date ? format(parseISO(cls.end_date), 'MMM dd') : ''}</span></div>
          <div className="flex items-center gap-2"><Users className="w-4 h-4" /><span>{cls.duration_days}d | {cls.start_time}-{cls.end_time}</span></div>
        </div>
        {cancellations > 0 && <div className="bg-amber-50 border border-amber-200 rounded-lg p-2 mb-3 text-xs text-amber-800 font-semibold">Student cancelled {cancellations}/{cls.max_cancellations || 3} sessions</div>}
        {proof && <div className={`rounded-lg p-2 mb-3 text-center text-sm font-semibold ${proof.status === 'pending' ? 'bg-amber-50 text-amber-800' : proof.status === 'verified' ? 'bg-emerald-50 text-emerald-800' : 'bg-red-50 text-red-800'}`}><ShieldCheck className="w-4 h-4 inline mr-1" /> Proof: {proof.status}</div>}
        <div className="space-y-2">
          {cls.status === 'scheduled' && (
            <>
              <Button onClick={() => navigate(`/class/${cls.class_id}`)} className="w-full bg-emerald-500 hover:bg-emerald-600 text-white rounded-full font-bold" data-testid={`start-class-${cls.class_id}`}>
                <Play className="w-4 h-4 mr-2" /> Start Class
              </Button>
              <Button onClick={() => handleDeleteClass(cls.class_id)} variant="outline" className="w-full border-2 border-red-200 hover:bg-red-50 text-red-600 rounded-full" data-testid={`delete-class-${cls.class_id}`}>Delete</Button>
            </>
          )}
          {isLive && (
            <Button onClick={() => navigate(`/class/${cls.class_id}`)} className="w-full bg-emerald-500 hover:bg-emerald-600 text-white rounded-full font-bold animate-pulse" data-testid={`rejoin-class-${cls.class_id}`}>
              <Play className="w-4 h-4 mr-2" /> Rejoin Live Class
            </Button>
          )}
          {!proof && cls.status !== 'dismissed' && (
            <Button onClick={() => { setSelectedClassForProof(cls); setShowProofDialog(true); }} variant="outline" className="w-full border-2 border-sky-200 text-sky-600 rounded-full" data-testid={`submit-proof-${cls.class_id}`}>
              <Upload className="w-4 h-4 mr-2" /> Submit Proof
            </Button>
          )}
        </div>
      </div>
    );
  };

  if (loading) return <div className="min-h-screen flex items-center justify-center bg-slate-50"><div className="w-16 h-16 border-4 border-sky-500 border-t-transparent rounded-full animate-spin"></div></div>;

  if (!user?.is_approved) return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center" data-testid="teacher-pending-approval">
      <div className="bg-white rounded-3xl p-12 border-2 border-amber-200 max-w-md text-center">
        <AlertCircle className="w-16 h-16 text-amber-500 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-slate-900 mb-2">Approval Pending</h2>
        <p className="text-slate-600 mb-6">Your teacher account is awaiting admin approval.</p>
        <Button onClick={handleLogout} className="rounded-full" data-testid="logout-button">Logout</Button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-white/80 border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <GraduationCap className="w-10 h-10 text-sky-500" strokeWidth={2.5} />
              <div><h1 className="text-2xl font-bold text-slate-900">Teacher Dashboard</h1><p className="text-sm text-slate-600">Wallet: {user?.credits || 0} credits</p></div>
            </div>
            <div className="flex items-center gap-4">
              <button onClick={() => setShowNotifDialog(true)} className="relative p-2 rounded-full hover:bg-slate-100" data-testid="notifications-bell">
                <Bell className="w-6 h-6 text-slate-700" />
                {unreadCount > 0 && <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center font-bold">{unreadCount}</span>}
              </button>
              <div className="text-right"><p className="text-sm text-slate-600">Welcome,</p><p className="font-semibold text-slate-900">{user?.name}</p></div>
              <Button onClick={handleLogout} variant="outline" className="rounded-full" data-testid="logout-button"><LogOut className="w-4 h-4 mr-2" /> Logout</Button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Student Complaints */}
        {studentComplaints.length > 0 && (
          <div className="mb-8">
            <h2 className="text-xl font-bold text-red-700 mb-4">Student Complaints ({studentComplaints.length})</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {studentComplaints.map(c => (
                <div key={c.complaint_id} className="bg-red-50 rounded-2xl border-2 border-red-200 p-5">
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="font-bold text-slate-900">{c.subject}</h3>
                    <span className={`px-2 py-1 rounded-full text-xs font-semibold ${c.status === 'open' ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-800'}`}>{c.status}</span>
                  </div>
                  <p className="text-sm text-slate-600 mb-1">{c.description}</p>
                  <p className="text-xs text-slate-500">From: {c.raised_by_name}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Pending Assignments */}
        {pendingAssignments.length > 0 && (
          <div className="mb-8">
            <h2 className="text-xl font-bold text-slate-900 mb-4">Pending Student Assignments</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {pendingAssignments.map(a => (
                <div key={a.assignment_id} className="bg-amber-50 rounded-2xl border-2 border-amber-200 p-5">
                  <div className="flex items-start justify-between mb-3">
                    <div><h3 className="font-bold text-slate-900">{a.student_name}</h3><p className="text-sm text-slate-600">{a.student_email}</p></div>
                    <span className="bg-amber-200 text-amber-900 px-3 py-1 rounded-full text-xs font-semibold">PENDING</span>
                  </div>
                  <div className="flex gap-2">
                    <Button onClick={() => handleApproveAssignment(a.assignment_id, true)} className="flex-1 bg-emerald-500 hover:bg-emerald-600 text-white rounded-full" data-testid={`approve-${a.assignment_id}`}>Approve</Button>
                    <Button onClick={() => handleApproveAssignment(a.assignment_id, false)} variant="outline" className="flex-1 rounded-full" data-testid={`reject-${a.assignment_id}`}>Reject</Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* My Students */}
        {approvedStudents.length > 0 && (
          <div className="mb-8">
            <h2 className="text-xl font-bold text-slate-900 mb-4">My Students</h2>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {approvedStudents.map(a => (
                <div key={a.assignment_id} className="bg-emerald-50 rounded-2xl border-2 border-emerald-200 p-4">
                  <h3 className="font-bold text-slate-900">{a.student_name}</h3>
                  <p className="text-xs text-slate-600">{a.student_email}</p>
                  <p className="text-sm text-emerald-600 mt-2 font-semibold">{a.credit_price}/class</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex flex-wrap gap-3 mb-8">
          <Button onClick={() => setShowCreateDialog(true)} className="bg-sky-500 hover:bg-sky-600 text-white rounded-full px-6 py-3 font-bold" data-testid="create-class-button"><Plus className="w-5 h-5 mr-2" /> Create New Class</Button>
          <Button onClick={() => navigate('/demo-live-sheet')} className="bg-amber-400 hover:bg-amber-500 text-slate-900 rounded-full px-6 py-3 font-bold" data-testid="demo-live-sheet-button"><Zap className="w-4 h-4 mr-2" /> Demo Live Sheet</Button>
          <Button onClick={() => navigate('/wallet')} variant="outline" className="rounded-full px-6 py-3 font-bold" data-testid="wallet-button"><CreditCard className="w-4 h-4 mr-2" /> Wallet</Button>
          <Button onClick={() => navigate('/teacher-calendar')} variant="outline" className="rounded-full px-6 py-3 font-bold" data-testid="calendar-button"><CalendarDays className="w-4 h-4 mr-2" /> Content Planner</Button>
          <Button onClick={() => navigate('/learning-kit')} variant="outline" className="rounded-full px-6 py-3 font-bold" data-testid="learning-kit-button"><BookOpen className="w-4 h-4 mr-2" /> Learning Kit</Button>
          <Button onClick={() => navigate('/teacher-classes')} variant="outline" className="rounded-full px-6 py-3 font-bold">All Classes</Button>
          <Button onClick={() => navigate('/complaints')} variant="outline" className="rounded-full px-6 py-3 font-bold"><MessageSquare className="w-4 h-4 mr-2" /> My Complaints</Button>
        </div>

        {/* This Week's Classes */}
        <h2 className="text-xl font-bold text-slate-900 mb-4">This Week's Classes ({thisWeekClasses.length})</h2>
        {thisWeekClasses.length === 0 ? (
          <div className="bg-white rounded-3xl p-12 border-2 border-slate-100 text-center mb-8">
            <p className="text-slate-600">No classes this week. Create one!</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
            {thisWeekClasses.map(cls => renderClassCard(cls))}
          </div>
        )}

        {/* Other Classes (collapsible) */}
        {otherClasses.length > 0 && (
          <div>
            <button onClick={() => setShowOtherClasses(!showOtherClasses)} className="flex items-center gap-2 text-lg font-bold text-slate-700 mb-4 hover:text-slate-900 transition-colors" data-testid="toggle-other-classes">
              {showOtherClasses ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
              Other Classes ({otherClasses.length})
            </button>
            {showOtherClasses && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {otherClasses.map(cls => renderClassCard(cls))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Create Class Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="sm:max-w-2xl rounded-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle className="text-2xl font-bold text-slate-900">Create New Class</DialogTitle></DialogHeader>
          <form onSubmit={handleCreateClass} className="space-y-4 mt-4">
            <div className="flex items-center gap-3 bg-violet-50 rounded-xl p-4 border-2 border-violet-200">
              <input type="checkbox" id="is_demo" checked={formData.is_demo} onChange={e => setFormData({ ...formData, is_demo: e.target.checked })} className="w-5 h-5 rounded" data-testid="demo-toggle" />
              <label htmlFor="is_demo" className="font-semibold text-violet-800">Demo Session</label>
              <span className="text-xs text-violet-600 ml-auto">Uses demo pricing</span>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div><Label>Title</Label><Input value={formData.title} onChange={e => setFormData({ ...formData, title: e.target.value })} className="rounded-xl" required data-testid="class-title-input" /></div>
              <div><Label>Subject</Label><Input value={formData.subject} onChange={e => setFormData({ ...formData, subject: e.target.value })} className="rounded-xl" required data-testid="class-subject-input" /></div>
              <div><Label>Type</Label><select value={formData.class_type} onChange={e => setFormData({ ...formData, class_type: e.target.value })} className="w-full rounded-xl border-2 border-slate-200 px-3 py-2" data-testid="class-type-select"><option value="1:1">1:1</option><option value="group">Group</option></select></div>
              <div><Label>Date</Label><Input type="date" value={formData.date} onChange={e => setFormData({ ...formData, date: e.target.value })} className="rounded-xl" required data-testid="class-date-input" /></div>
              <div><Label>Start Time</Label><Input type="time" value={formData.start_time} onChange={e => setFormData({ ...formData, start_time: e.target.value })} className="rounded-xl" required data-testid="class-start-time-input" /></div>
              <div><Label>End Time</Label><Input type="time" value={formData.end_time} onChange={e => setFormData({ ...formData, end_time: e.target.value })} className="rounded-xl" required data-testid="class-end-time-input" /></div>
              <div><Label>For Student</Label><select value={formData.assigned_student_id} onChange={e => setFormData({ ...formData, assigned_student_id: e.target.value })} className="w-full rounded-xl border-2 border-slate-200 px-3 py-2" required data-testid="student-select"><option value="">Select student...</option>{approvedStudents.map(a => <option key={a.student_id} value={a.student_id}>{a.student_name}</option>)}</select></div>
              <div><Label>Duration (Days)</Label><Input type="number" min="1" value={formData.duration_days} onChange={e => setFormData({ ...formData, duration_days: e.target.value })} className="rounded-xl" required data-testid="class-duration-input" /></div>
              <div><Label>Max Students</Label><Input type="number" value={formData.max_students} onChange={e => setFormData({ ...formData, max_students: e.target.value })} className="rounded-xl" required data-testid="class-max-students-input" /></div>
            </div>
            <Button type="submit" className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-full py-6 font-bold" data-testid="submit-create-class-button">Create {formData.is_demo ? 'Demo Session' : 'Class'}</Button>
          </form>
        </DialogContent>
      </Dialog>

      {/* Submit Proof Dialog */}
      <Dialog open={showProofDialog} onOpenChange={setShowProofDialog}>
        <DialogContent className="sm:max-w-lg rounded-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle className="text-2xl font-bold text-slate-900">Submit Class Proof</DialogTitle></DialogHeader>
          {selectedClassForProof && (
            <div className="space-y-4 mt-4">
              <div className="bg-slate-50 rounded-xl p-3"><p className="font-semibold text-slate-900">{selectedClassForProof.title}</p><p className="text-sm text-slate-600">{selectedClassForProof.subject} | {selectedClassForProof.date}</p></div>
              <div><Label>Performance *</Label><select value={proofData.student_performance} onChange={e => setProofData({ ...proofData, student_performance: e.target.value })} className="w-full rounded-xl border-2 border-slate-200 px-3 py-2" data-testid="performance-select"><option value="excellent">Excellent</option><option value="good">Good</option><option value="average">Average</option><option value="needs_improvement">Needs Improvement</option></select></div>
              <div><Label>Topics Covered *</Label><textarea value={proofData.topics_covered} onChange={e => setProofData({ ...proofData, topics_covered: e.target.value })} className="w-full rounded-xl border-2 border-slate-200 px-3 py-2" rows={3} data-testid="topics-covered-input" /></div>
              <div><Label>Feedback *</Label><textarea value={proofData.feedback_text} onChange={e => setProofData({ ...proofData, feedback_text: e.target.value })} className="w-full rounded-xl border-2 border-slate-200 px-3 py-2" rows={3} data-testid="feedback-text-input" /></div>
              <div><Label>Screenshot (optional, max 2MB)</Label><input type="file" accept="image/*" onChange={handleScreenshotUpload} className="w-full rounded-xl border-2 border-slate-200 px-3 py-2 text-sm" data-testid="screenshot-upload" />{proofData.screenshot_base64 && <p className="text-xs text-emerald-600 mt-1">Attached</p>}</div>
              <Button onClick={handleSubmitProof} className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-full py-6 font-bold" data-testid="submit-proof-confirm-button"><Upload className="w-5 h-5 mr-2" /> Submit Proof</Button>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Notifications Dialog */}
      <Dialog open={showNotifDialog} onOpenChange={setShowNotifDialog}>
        <DialogContent className="sm:max-w-lg rounded-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <div className="flex items-center justify-between w-full">
              <DialogTitle className="text-2xl font-bold text-slate-900">Notifications</DialogTitle>
              {unreadCount > 0 && <Button onClick={handleMarkAllRead} variant="outline" className="rounded-full text-xs" data-testid="mark-all-read">Mark all read</Button>}
            </div>
          </DialogHeader>
          <div className="space-y-3 mt-4">
            {notifications.length === 0 ? <p className="text-slate-500 text-center py-8">No notifications</p> : notifications.map(n => (
              <div key={n.notification_id} className={`rounded-xl p-4 border-2 ${n.read ? 'bg-slate-50 border-slate-200' : 'bg-sky-50 border-sky-200'}`} data-testid={`notif-${n.notification_id}`}>
                <div className="flex items-start gap-3">
                  {!n.read && <div className="w-2 h-2 rounded-full bg-sky-500 mt-2 flex-shrink-0"></div>}
                  <div className="flex-1"><p className="font-semibold text-slate-900 text-sm">{n.title}</p><p className="text-slate-600 text-sm">{n.message}</p><p className="text-xs text-slate-400 mt-1">{new Date(n.created_at).toLocaleString()}</p></div>
                </div>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default TeacherDashboard;
