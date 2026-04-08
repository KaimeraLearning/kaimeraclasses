import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { toast } from 'sonner';
import { ArrowLeft, Plus, MessageSquare, CheckCircle } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ComplaintsPage = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [myComplaints, setMyComplaints] = useState([]);
  const [studentComplaints, setStudentComplaints] = useState([]);
  const [allComplaints, setAllComplaints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showResolveDialog, setShowResolveDialog] = useState(false);
  const [selectedComplaint, setSelectedComplaint] = useState(null);
  const [subject, setSubject] = useState('');
  const [description, setDescription] = useState('');
  const [resolution, setResolution] = useState('');

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const userRes = await fetch(`${API}/auth/me`, { credentials: 'include' });
      if (!userRes.ok) throw new Error('Not authenticated');
      const userData = await userRes.json();
      setUser(userData);

      // Fetch based on role
      if (userData.role === 'admin') {
        const res = await fetch(`${API}/admin/complaints`, { credentials: 'include' });
        if (res.ok) setAllComplaints(await res.json());
      } else if (userData.role === 'teacher') {
        const [myRes, studentRes] = await Promise.all([
          fetch(`${API}/complaints/my`, { credentials: 'include' }),
          fetch(`${API}/teacher/student-complaints`, { credentials: 'include' })
        ]);
        if (myRes.ok) setMyComplaints(await myRes.json());
        if (studentRes.ok) setStudentComplaints(await studentRes.json());
      } else if (userData.role === 'counsellor') {
        const [myRes, allRes] = await Promise.all([
          fetch(`${API}/complaints/my`, { credentials: 'include' }),
          fetch(`${API}/admin/complaints`, { credentials: 'include' })
        ]);
        if (myRes.ok) setMyComplaints(await myRes.json());
        if (allRes.ok) setAllComplaints(await allRes.json());
      } else {
        const myRes = await fetch(`${API}/complaints/my`, { credentials: 'include' });
        if (myRes.ok) setMyComplaints(await myRes.json());
      }
      setLoading(false);
    } catch (error) {
      toast.error('Failed to load complaints');
      setLoading(false);
    }
  };

  const handleCreateComplaint = async () => {
    if (!subject.trim() || !description.trim()) { toast.error('Fill all fields'); return; }
    try {
      const response = await fetch(`${API}/complaints/create`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
        body: JSON.stringify({ subject, description })
      });
      if (!response.ok) throw new Error((await response.json()).detail);
      toast.success('Complaint submitted!');
      setShowCreateDialog(false);
      setSubject('');
      setDescription('');
      fetchData();
    } catch (error) { toast.error(error.message); }
  };

  const handleResolve = async (status) => {
    try {
      const response = await fetch(`${API}/admin/resolve-complaint`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
        body: JSON.stringify({ complaint_id: selectedComplaint.complaint_id, resolution, status })
      });
      if (!response.ok) throw new Error((await response.json()).detail);
      toast.success(`Complaint ${status}`);
      setShowResolveDialog(false);
      setSelectedComplaint(null);
      setResolution('');
      fetchData();
    } catch (error) { toast.error(error.message); }
  };

  const getDashboardRoute = () => {
    if (!user) return '/login';
    return { student: '/student-dashboard', teacher: '/teacher-dashboard', counsellor: '/counsellor-dashboard', admin: '/admin-dashboard' }[user.role] || '/login';
  };

  const renderComplaintCard = (c, canResolve = false) => (
    <div key={c.complaint_id} className="bg-white rounded-2xl border-2 border-slate-200 p-6 hover:shadow-md transition-all" data-testid={`complaint-card-${c.complaint_id}`}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <h3 className="font-bold text-lg text-slate-900">{c.subject}</h3>
          <p className="text-sm text-slate-500">By: {c.raised_by_name} ({c.raised_by_role})</p>
        </div>
        <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
          c.status === 'open' ? 'bg-amber-100 text-amber-800' :
          c.status === 'resolved' ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-800'
        }`}>{c.status.toUpperCase()}</span>
      </div>
      <p className="text-slate-600 mb-3">{c.description}</p>
      {c.resolution && (
        <div className="bg-emerald-50 rounded-xl p-3 border border-emerald-200 mb-3">
          <p className="text-sm text-emerald-800"><strong>Resolution:</strong> {c.resolution}</p>
        </div>
      )}
      <div className="flex items-center justify-between">
        <p className="text-xs text-slate-400">{new Date(c.created_at).toLocaleDateString()}</p>
        {canResolve && c.status === 'open' && (
          <Button onClick={() => { setSelectedComplaint(c); setShowResolveDialog(true); }}
            className="bg-emerald-500 hover:bg-emerald-600 text-white rounded-full text-sm"
            data-testid={`resolve-complaint-${c.complaint_id}`}>
            <CheckCircle className="w-4 h-4 mr-1" /> Resolve
          </Button>
        )}
      </div>
    </div>
  );

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="w-16 h-16 border-4 border-sky-500 border-t-transparent rounded-full animate-spin"></div>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-white/80 border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button onClick={() => navigate(getDashboardRoute())} variant="outline" className="rounded-full">
                <ArrowLeft className="w-4 h-4 mr-2" /> Back
              </Button>
              <h1 className="text-2xl font-bold text-slate-900">Complaints</h1>
            </div>
            {user?.role !== 'admin' && (
              <Button onClick={() => setShowCreateDialog(true)} className="bg-sky-500 hover:bg-sky-600 text-white rounded-full" data-testid="create-complaint-button">
                <Plus className="w-4 h-4 mr-2" /> New Complaint
              </Button>
            )}
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Admin view - all complaints */}
        {user?.role === 'admin' && (
          <div>
            <h2 className="text-xl font-bold text-slate-900 mb-4">All Complaints ({allComplaints.length})</h2>
            {allComplaints.length === 0 ? (
              <div className="bg-white rounded-3xl p-12 border-2 border-slate-100 text-center">
                <MessageSquare className="w-16 h-16 text-slate-300 mx-auto mb-4" />
                <p className="text-slate-600">No complaints received</p>
              </div>
            ) : (
              <div className="space-y-4">
                {allComplaints.map(c => renderComplaintCard(c, true))}
              </div>
            )}
          </div>
        )}

        {/* Teacher view - student complaints about them + their own */}
        {user?.role === 'teacher' && (
          <div className="space-y-8">
            {studentComplaints.length > 0 && (
              <div>
                <h2 className="text-xl font-bold text-red-700 mb-4">Student Complaints About You ({studentComplaints.length})</h2>
                <div className="space-y-4">
                  {studentComplaints.map(c => renderComplaintCard(c))}
                </div>
              </div>
            )}
            <div>
              <h2 className="text-xl font-bold text-slate-900 mb-4">My Complaints ({myComplaints.length})</h2>
              {myComplaints.length === 0 ? (
                <div className="bg-white rounded-3xl p-8 border-2 border-slate-100 text-center">
                  <p className="text-slate-600">No complaints submitted</p>
                </div>
              ) : (
                <div className="space-y-4">{myComplaints.map(c => renderComplaintCard(c))}</div>
              )}
            </div>
          </div>
        )}

        {/* Student / Counsellor view - their own complaints */}
        {user?.role === 'student' && (
          <div>
            <h2 className="text-xl font-bold text-slate-900 mb-4">My Complaints ({myComplaints.length})</h2>
            {myComplaints.length === 0 ? (
              <div className="bg-white rounded-3xl p-12 border-2 border-slate-100 text-center">
                <MessageSquare className="w-16 h-16 text-slate-300 mx-auto mb-4" />
                <p className="text-slate-600">No complaints submitted yet</p>
              </div>
            ) : (
              <div className="space-y-4">{myComplaints.map(c => renderComplaintCard(c))}</div>
            )}
          </div>
        )}

        {/* Counsellor view - all complaints + their own */}
        {user?.role === 'counsellor' && (
          <div className="space-y-8">
            <div>
              <h2 className="text-xl font-bold text-slate-900 mb-4">All Student & Teacher Complaints ({allComplaints.length})</h2>
              {allComplaints.length === 0 ? (
                <div className="bg-white rounded-3xl p-8 border-2 border-slate-100 text-center">
                  <p className="text-slate-600">No complaints received</p>
                </div>
              ) : (
                <div className="space-y-4">{allComplaints.map(c => renderComplaintCard(c))}</div>
              )}
            </div>
            {myComplaints.length > 0 && (
              <div>
                <h2 className="text-xl font-bold text-slate-900 mb-4">My Complaints ({myComplaints.length})</h2>
                <div className="space-y-4">{myComplaints.map(c => renderComplaintCard(c))}</div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Create Complaint Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="sm:max-w-md rounded-3xl">
          <DialogHeader><DialogTitle className="text-2xl font-bold text-slate-900">New Complaint</DialogTitle></DialogHeader>
          <div className="space-y-4 mt-4">
            <div><Label>Subject</Label><Input value={subject} onChange={e => setSubject(e.target.value)} className="rounded-xl" placeholder="Brief summary..." data-testid="complaint-subject-input" /></div>
            <div><Label>Description</Label><textarea value={description} onChange={e => setDescription(e.target.value)} className="w-full rounded-xl border-2 border-slate-200 px-3 py-2" rows={4} placeholder="Describe your issue..." data-testid="complaint-description-input" /></div>
            <Button onClick={handleCreateComplaint} className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-full py-6 font-bold" data-testid="submit-complaint-button">Submit Complaint</Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Resolve Complaint Dialog (Admin) */}
      <Dialog open={showResolveDialog} onOpenChange={setShowResolveDialog}>
        <DialogContent className="sm:max-w-md rounded-3xl">
          <DialogHeader><DialogTitle className="text-2xl font-bold text-slate-900">Resolve Complaint</DialogTitle></DialogHeader>
          {selectedComplaint && (
            <div className="space-y-4 mt-4">
              <div className="bg-slate-50 rounded-xl p-4">
                <p className="font-semibold text-slate-900">{selectedComplaint.subject}</p>
                <p className="text-sm text-slate-600 mt-1">{selectedComplaint.description}</p>
              </div>
              <div><Label>Resolution</Label><textarea value={resolution} onChange={e => setResolution(e.target.value)} className="w-full rounded-xl border-2 border-slate-200 px-3 py-2" rows={3} placeholder="Describe the resolution..." data-testid="resolution-input" /></div>
              <div className="flex gap-3">
                <Button onClick={() => handleResolve('resolved')} className="flex-1 bg-emerald-500 hover:bg-emerald-600 text-white rounded-full py-5 font-bold" data-testid="mark-resolved-button">Mark Resolved</Button>
                <Button onClick={() => handleResolve('closed')} variant="outline" className="flex-1 rounded-full py-5 font-bold" data-testid="mark-closed-button">Close</Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ComplaintsPage;
