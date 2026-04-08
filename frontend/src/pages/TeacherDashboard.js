import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { toast } from 'sonner';
import { GraduationCap, LogOut, Plus, Calendar, Users, AlertCircle, ShieldCheck, Upload, MessageSquare } from 'lucide-react';
import { format, parseISO } from 'date-fns';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const TeacherDashboard = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [classes, setClasses] = useState([]);
  const [pendingAssignments, setPendingAssignments] = useState([]);
  const [approvedStudents, setApprovedStudents] = useState([]);
  const [proofs, setProofs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showProofDialog, setShowProofDialog] = useState(false);
  const [selectedClassForProof, setSelectedClassForProof] = useState(null);
  const [formData, setFormData] = useState({
    title: '', subject: '', class_type: '1:1', date: '', start_time: '', end_time: '',
    max_students: '', assigned_student_id: '', duration_days: '1', is_demo: false
  });
  const [proofData, setProofData] = useState({
    feedback_text: '', student_performance: 'good', topics_covered: '', screenshot_base64: null
  });

  useEffect(() => { fetchDashboardData(); }, []);

  const fetchDashboardData = async () => {
    try {
      const [userRes, dashboardRes, proofsRes] = await Promise.all([
        fetch(`${API}/auth/me`, { credentials: 'include' }),
        fetch(`${API}/teacher/dashboard`, { credentials: 'include' }),
        fetch(`${API}/teacher/my-proofs`, { credentials: 'include' })
      ]);
      if (!userRes.ok || !dashboardRes.ok) throw new Error('Failed to fetch data');
      setUser(await userRes.json());
      const dashboardData = await dashboardRes.json();
      setClasses(dashboardData.classes);
      setPendingAssignments(dashboardData.pending_assignments || []);
      setApprovedStudents(dashboardData.approved_students || []);
      if (proofsRes.ok) setProofs(await proofsRes.json());
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
      toast.success('Class created successfully!');
      setShowCreateDialog(false);
      setFormData({ title: '', subject: '', class_type: '1:1', date: '', start_time: '', end_time: '', max_students: '', assigned_student_id: '', duration_days: '1', is_demo: false });
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
    if (!window.confirm('Are you sure you want to delete this class?')) return;
    try {
      const response = await fetch(`${API}/classes/delete/${classId}`, { method: 'DELETE', credentials: 'include' });
      if (!response.ok) throw new Error((await response.json()).detail);
      toast.success('Class deleted successfully');
      fetchDashboardData();
    } catch (error) { toast.error(error.message); }
  };

  const handleSubmitProof = async () => {
    if (!proofData.feedback_text || !proofData.topics_covered) {
      toast.error('Please fill in all required fields');
      return;
    }
    try {
      const response = await fetch(`${API}/teacher/submit-proof`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
        body: JSON.stringify({ class_id: selectedClassForProof.class_id, ...proofData })
      });
      if (!response.ok) throw new Error((await response.json()).detail);
      toast.success('Proof submitted for verification!');
      setShowProofDialog(false);
      setSelectedClassForProof(null);
      setProofData({ feedback_text: '', student_performance: 'good', topics_covered: '', screenshot_base64: null });
      fetchDashboardData();
    } catch (error) { toast.error(error.message); }
  };

  const handleScreenshotUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) { toast.error('File too large (max 2MB)'); return; }
    const reader = new FileReader();
    reader.onload = () => setProofData({ ...proofData, screenshot_base64: reader.result });
    reader.readAsDataURL(file);
  };

  const handleLogout = async () => {
    try { await fetch(`${API}/auth/logout`, { method: 'POST', credentials: 'include' }); navigate('/login'); } catch {}
  };

  const getProofStatus = (classId) => proofs.find(p => p.class_id === classId);

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="w-16 h-16 border-4 border-sky-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
    </div>
  );

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
              <div>
                <h1 className="text-2xl font-bold text-slate-900">Teacher Dashboard</h1>
                <p className="text-sm text-slate-600">Wallet: {user?.credits || 0} credits</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right">
                <p className="text-sm text-slate-600">Welcome,</p>
                <p className="font-semibold text-slate-900">{user?.name}</p>
              </div>
              <Button onClick={handleLogout} variant="outline" className="rounded-full" data-testid="logout-button">
                <LogOut className="w-4 h-4 mr-2" /> Logout
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Pending Assignments */}
        {pendingAssignments.length > 0 && (
          <div className="mb-8">
            <h2 className="text-xl font-bold text-slate-900 mb-4">Pending Student Assignments</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {pendingAssignments.map(a => (
                <div key={a.assignment_id} className="bg-amber-50 rounded-2xl border-2 border-amber-200 p-5">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="font-bold text-slate-900">{a.student_name}</h3>
                      <p className="text-sm text-slate-600">{a.student_email}</p>
                    </div>
                    <span className="bg-amber-200 text-amber-900 px-3 py-1 rounded-full text-xs font-semibold">PENDING</span>
                  </div>
                  <div className="flex gap-2">
                    <Button onClick={() => handleApproveAssignment(a.assignment_id, true)} className="flex-1 bg-emerald-500 hover:bg-emerald-600 text-white rounded-full">Approve</Button>
                    <Button onClick={() => handleApproveAssignment(a.assignment_id, false)} variant="outline" className="flex-1 rounded-full">Reject</Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Approved Students */}
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

        {/* Action Buttons */}
        <div className="flex flex-wrap gap-3 mb-8">
          <Button onClick={() => setShowCreateDialog(true)} className="bg-sky-500 hover:bg-sky-600 text-white rounded-full px-6 py-3 font-bold" data-testid="create-class-button">
            <Plus className="w-5 h-5 mr-2" /> Create New Class
          </Button>
          <Button onClick={() => navigate('/teacher-classes')} variant="outline" className="rounded-full px-6 py-3 font-bold">
            View All Classes
          </Button>
          <Button onClick={() => navigate('/complaints')} variant="outline" className="rounded-full px-6 py-3 font-bold">
            <MessageSquare className="w-4 h-4 mr-2" /> Complaints
          </Button>
        </div>

        {/* Recent Classes */}
        <h2 className="text-xl font-bold text-slate-900 mb-4">Recent Classes</h2>
        {classes.length === 0 ? (
          <div className="bg-white rounded-3xl p-12 border-2 border-slate-100 text-center">
            <p className="text-slate-600">No classes created yet. Create your first class!</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {classes.slice(0, 6).map(cls => {
              const proof = getProofStatus(cls.class_id);
              return (
                <div key={cls.class_id} className="bg-white rounded-3xl border-2 border-slate-200 shadow-[4px_4px_0px_0px_rgba(226,232,240,1)] p-6" data-testid={`class-card-${cls.class_id}`}>
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex gap-2">
                      <span className="bg-amber-100 text-amber-800 px-3 py-1 rounded-full text-xs font-semibold">{cls.subject}</span>
                      {cls.is_demo && <span className="bg-violet-100 text-violet-800 px-3 py-1 rounded-full text-xs font-semibold">DEMO</span>}
                    </div>
                    <span className="bg-emerald-100 text-emerald-800 px-3 py-1 rounded-full text-xs font-semibold">{cls.status}</span>
                  </div>
                  <h3 className="text-xl font-bold text-slate-900 mb-4">{cls.title}</h3>
                  <div className="space-y-2 mb-4">
                    <div className="flex items-center gap-2 text-slate-600">
                      <Calendar className="w-4 h-4" />
                      <span className="text-sm">{format(parseISO(cls.date), 'MMM dd, yyyy')}</span>
                    </div>
                    <div className="flex items-center gap-2 text-slate-600">
                      <Users className="w-4 h-4" />
                      <span className="text-sm">{cls.enrolled_students.length} / {cls.max_students} students</span>
                    </div>
                  </div>

                  {/* Proof Status */}
                  {proof ? (
                    <div className={`rounded-lg p-2 mb-3 text-center text-sm font-semibold ${
                      proof.status === 'pending' ? 'bg-amber-50 text-amber-800' :
                      proof.status === 'verified' ? 'bg-emerald-50 text-emerald-800' :
                      'bg-red-50 text-red-800'
                    }`}>
                      <ShieldCheck className="w-4 h-4 inline mr-1" /> Proof: {proof.status}
                    </div>
                  ) : null}

                  <div className="space-y-2">
                    {cls.status === 'scheduled' && (
                      <>
                        <Button onClick={() => navigate(`/class/${cls.class_id}`)} className="w-full bg-emerald-500 hover:bg-emerald-600 text-white rounded-full font-bold" data-testid={`start-class-button-${cls.class_id}`}>
                          Start Class
                        </Button>
                        <Button onClick={() => handleDeleteClass(cls.class_id)} variant="outline" className="w-full border-2 border-red-200 hover:bg-red-50 text-red-600 rounded-full font-bold" data-testid={`delete-class-button-${cls.class_id}`}>
                          Delete Class
                        </Button>
                      </>
                    )}
                    {!proof && (
                      <Button onClick={() => { setSelectedClassForProof(cls); setShowProofDialog(true); }} variant="outline" className="w-full border-2 border-sky-200 text-sky-600 rounded-full font-bold" data-testid={`submit-proof-button-${cls.class_id}`}>
                        <Upload className="w-4 h-4 mr-2" /> Submit Proof
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Create Class Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="sm:max-w-2xl rounded-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold text-slate-900">Create New Class</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreateClass} className="space-y-4 mt-4">
            {/* Demo Toggle */}
            <div className="flex items-center gap-3 bg-violet-50 rounded-xl p-4 border-2 border-violet-200">
              <input type="checkbox" id="is_demo" checked={formData.is_demo} onChange={e => setFormData({ ...formData, is_demo: e.target.checked })}
                className="w-5 h-5 text-violet-600 rounded" data-testid="demo-toggle" />
              <label htmlFor="is_demo" className="font-semibold text-violet-800">This is a Demo Session</label>
              <span className="text-xs text-violet-600 ml-auto">Uses demo pricing</span>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Title</Label>
                <Input value={formData.title} onChange={e => setFormData({ ...formData, title: e.target.value })} className="rounded-xl" required data-testid="class-title-input" />
              </div>
              <div>
                <Label>Subject</Label>
                <Input value={formData.subject} onChange={e => setFormData({ ...formData, subject: e.target.value })} className="rounded-xl" required data-testid="class-subject-input" />
              </div>
              <div>
                <Label>Type</Label>
                <select value={formData.class_type} onChange={e => setFormData({ ...formData, class_type: e.target.value })} className="w-full rounded-xl border-2 border-slate-200 px-3 py-2" data-testid="class-type-select">
                  <option value="1:1">1:1</option>
                  <option value="group">Group</option>
                </select>
              </div>
              <div>
                <Label>Date</Label>
                <Input type="date" value={formData.date} onChange={e => setFormData({ ...formData, date: e.target.value })} className="rounded-xl" required data-testid="class-date-input" />
              </div>
              <div>
                <Label>Start Time</Label>
                <Input type="time" value={formData.start_time} onChange={e => setFormData({ ...formData, start_time: e.target.value })} className="rounded-xl" required data-testid="class-start-time-input" />
              </div>
              <div>
                <Label>End Time</Label>
                <Input type="time" value={formData.end_time} onChange={e => setFormData({ ...formData, end_time: e.target.value })} className="rounded-xl" required data-testid="class-end-time-input" />
              </div>
              <div>
                <Label>For Student</Label>
                <select value={formData.assigned_student_id} onChange={e => setFormData({ ...formData, assigned_student_id: e.target.value })} className="w-full rounded-xl border-2 border-slate-200 px-3 py-2" required data-testid="student-select">
                  <option value="">Select student...</option>
                  {approvedStudents.map(a => <option key={a.student_id} value={a.student_id}>{a.student_name}</option>)}
                </select>
              </div>
              <div>
                <Label>Duration (Days)</Label>
                <Input type="number" min="1" value={formData.duration_days} onChange={e => setFormData({ ...formData, duration_days: e.target.value })} className="rounded-xl" required data-testid="class-duration-input" />
              </div>
              <div>
                <Label>Max Students</Label>
                <Input type="number" value={formData.max_students} onChange={e => setFormData({ ...formData, max_students: e.target.value })} className="rounded-xl" required data-testid="class-max-students-input" />
              </div>
            </div>
            <Button type="submit" className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-full py-6 font-bold" data-testid="submit-create-class-button">
              Create {formData.is_demo ? 'Demo Session' : 'Class'}
            </Button>
          </form>
        </DialogContent>
      </Dialog>

      {/* Submit Proof Dialog */}
      <Dialog open={showProofDialog} onOpenChange={setShowProofDialog}>
        <DialogContent className="sm:max-w-lg rounded-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold text-slate-900">Submit Class Proof</DialogTitle>
          </DialogHeader>
          {selectedClassForProof && (
            <div className="space-y-4 mt-4">
              <div className="bg-slate-50 rounded-xl p-3">
                <p className="font-semibold text-slate-900">{selectedClassForProof.title}</p>
                <p className="text-sm text-slate-600">{selectedClassForProof.subject} | {selectedClassForProof.date}</p>
              </div>
              <div>
                <Label>Student Performance *</Label>
                <select value={proofData.student_performance} onChange={e => setProofData({ ...proofData, student_performance: e.target.value })}
                  className="w-full rounded-xl border-2 border-slate-200 px-3 py-2" data-testid="performance-select">
                  <option value="excellent">Excellent</option>
                  <option value="good">Good</option>
                  <option value="average">Average</option>
                  <option value="needs_improvement">Needs Improvement</option>
                </select>
              </div>
              <div>
                <Label>Topics Covered *</Label>
                <textarea value={proofData.topics_covered} onChange={e => setProofData({ ...proofData, topics_covered: e.target.value })}
                  className="w-full rounded-xl border-2 border-slate-200 px-3 py-2" rows={3} placeholder="List topics covered..."
                  data-testid="topics-covered-input" />
              </div>
              <div>
                <Label>Feedback *</Label>
                <textarea value={proofData.feedback_text} onChange={e => setProofData({ ...proofData, feedback_text: e.target.value })}
                  className="w-full rounded-xl border-2 border-slate-200 px-3 py-2" rows={3} placeholder="Your feedback about the session..."
                  data-testid="feedback-text-input" />
              </div>
              <div>
                <Label>Screenshot (optional, max 2MB)</Label>
                <input type="file" accept="image/*" onChange={handleScreenshotUpload} className="w-full rounded-xl border-2 border-slate-200 px-3 py-2 text-sm" data-testid="screenshot-upload" />
                {proofData.screenshot_base64 && <p className="text-xs text-emerald-600 mt-1">Screenshot attached</p>}
              </div>
              <Button onClick={handleSubmitProof} className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-full py-6 font-bold" data-testid="submit-proof-confirm-button">
                <Upload className="w-5 h-5 mr-2" /> Submit Proof for Verification
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default TeacherDashboard;
