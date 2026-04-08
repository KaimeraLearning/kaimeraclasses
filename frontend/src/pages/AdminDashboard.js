import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';
import { GraduationCap, LogOut, Check, X, DollarSign, MessageSquare, UserPlus, Copy, Zap, Clock, History, Search, Shield, Award, Filter, BookOpen } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const AdminDashboard = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [teachers, setTeachers] = useState([]);
  const [classes, setClasses] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [complaints, setComplaints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreditsDialog, setShowCreditsDialog] = useState(false);
  const [showCreateStudentDialog, setShowCreateStudentDialog] = useState(false);
  const [showCredsResult, setShowCredsResult] = useState(null);
  const [selectedUser, setSelectedUser] = useState(null);
  const [creditAmount, setCreditAmount] = useState('');
  const [creditAction, setCreditAction] = useState('add');
  const [newStudent, setNewStudent] = useState({
    name: '', email: '', password: '', institute: '', goal: '', preferred_time_slot: '', phone: '', state: '', city: '', country: '', grade: ''
  });
  const [pendingProofs, setPendingProofs] = useState([]);
  const [teacherSearch, setTeacherSearch] = useState('');
  const [teacherSearchResults, setTeacherSearchResults] = useState([]);
  const [classFilter, setClassFilter] = useState({ search: '', is_demo: '', status: '' });
  const [filteredClasses, setFilteredClasses] = useState([]);
  const [badgeTarget, setBadgeTarget] = useState('');
  const [badgeName, setBadgeName] = useState('');
  const [proofDateFrom, setProofDateFrom] = useState('');
  const [proofDateTo, setProofDateTo] = useState('');

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const [userRes, teachersRes, classesRes, transactionsRes, complaintsRes] = await Promise.all([
        fetch(`${API}/auth/me`, { credentials: 'include' }),
        fetch(`${API}/admin/teachers`, { credentials: 'include' }),
        fetch(`${API}/admin/classes`, { credentials: 'include' }),
        fetch(`${API}/admin/transactions`, { credentials: 'include' }),
        fetch(`${API}/admin/complaints`, { credentials: 'include' })
      ]);

      if (!userRes.ok) throw new Error('Failed to fetch data');

      const userData = await userRes.json();
      const teachersData = teachersRes.ok ? await teachersRes.json() : [];
      const classesData = classesRes.ok ? await classesRes.json() : [];
      const transactionsData = transactionsRes.ok ? await transactionsRes.json() : [];
      const complaintsData = complaintsRes.ok ? await complaintsRes.json() : [];

      setUser(userData);
      setTeachers(teachersData);
      setClasses(classesData);
      setTransactions(transactionsData);
      setComplaints(complaintsData);
      setFilteredClasses(classesData);
      // Fetch pending proofs for admin
      const proofsRes = await fetch(`${API}/admin/approved-proofs`, { credentials: 'include' });
      if (proofsRes.ok) setPendingProofs(await proofsRes.json());
      setLoading(false);
    } catch (error) {
      console.error(error);
      toast.error('Failed to load dashboard');
      setLoading(false);
    }
  };

  const handleApproveTeacher = async (teacherId, approved) => {
    try {
      const response = await fetch(`${API}/admin/approve-teacher`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ user_id: teacherId, approved })
      });

      if (!response.ok) throw new Error('Failed to update teacher');

      toast.success(`Teacher ${approved ? 'approved' : 'rejected'}`);
      fetchDashboardData();
    } catch (error) {
      toast.error(error.message);
    }
  };

  const handleAdjustCredits = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch(`${API}/admin/adjust-credits`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          user_id: selectedUser,
          amount: parseFloat(creditAmount),
          action: creditAction
        })
      });

      if (!response.ok) throw new Error('Failed to adjust credits');

      toast.success('Credits adjusted successfully');
      setShowCreditsDialog(false);
      setCreditAmount('');
      setSelectedUser(null);
      fetchDashboardData();
    } catch (error) {
      toast.error(error.message);
    }
  };

  const handleLogout = async () => {
    try {
      await fetch(`${API}/auth/logout`, { method: 'POST', credentials: 'include' });
      navigate('/login');
    } catch (error) { console.error(error); }
  };

  const handleTeacherSearch = async (query) => {
    setTeacherSearch(query);
    try {
      const res = await fetch(`${API}/search/teachers?q=${encodeURIComponent(query)}`, { credentials: 'include' });
      if (res.ok) setTeacherSearchResults(await res.json());
    } catch { /* ignore */ }
  };

  const handleFilterClasses = async () => {
    const params = new URLSearchParams();
    if (classFilter.search) params.set('search', classFilter.search);
    if (classFilter.is_demo) params.set('is_demo', classFilter.is_demo);
    if (classFilter.status) params.set('status', classFilter.status);
    try {
      const res = await fetch(`${API}/filter/classes?${params}`, { credentials: 'include' });
      if (res.ok) setFilteredClasses(await res.json());
    } catch { /* ignore */ }
  };

  const handleApproveProof = async (proofId, approved) => {
    const notes = approved ? '' : (prompt('Reason for rejection:') || '');
    try {
      const res = await fetch(`${API}/admin/approve-proof`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ proof_id: proofId, approved, admin_notes: notes })
      });
      if (!res.ok) throw new Error((await res.json()).detail);
      toast.success(approved ? 'Proof approved & teacher credited!' : 'Proof rejected');
      fetchDashboardData();
    } catch (err) { toast.error(err.message); }
  };

  const handleFilterProofs = async () => {
    const params = new URLSearchParams();
    if (proofDateFrom) params.set('date_from', proofDateFrom);
    if (proofDateTo) params.set('date_to', proofDateTo);
    try {
      const res = await fetch(`${API}/admin/approved-proofs?${params}`, { credentials: 'include' });
      if (res.ok) setPendingProofs(await res.json());
    } catch { /* ignore */ }
  };

  const handleAssignBadge = async () => {
    if (!badgeTarget || !badgeName) { toast.error('Select user and badge name'); return; }
    try {
      const res = await fetch(`${API}/admin/assign-badge`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: badgeTarget, badge_name: badgeName })
      });
      if (!res.ok) throw new Error((await res.json()).detail);
      toast.success('Badge assigned!');
      setBadgeName('');
      fetchDashboardData();
    } catch (err) { toast.error(err.message); }
  };

  const handleCreateStudent = async (e) => {
    e.preventDefault();
    if (!newStudent.name || !newStudent.email || !newStudent.password) {
      toast.error('Name, email and password are required');
      return;
    }
    try {
      const response = await fetch(`${API}/admin/create-student`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(newStudent)
      });
      if (!response.ok) throw new Error((await response.json()).detail);
      const data = await response.json();
      toast.success('Student account created!');
      setShowCredsResult(data.credentials);
      setNewStudent({ name: '', email: '', password: '', institute: '', goal: '', preferred_time_slot: '', phone: '', state: '', city: '', country: '', grade: '' });
      fetchDashboardData();
    } catch (error) { toast.error(error.message); }
  };

  const copyCredentials = () => {
    if (showCredsResult) {
      navigator.clipboard.writeText(`Email: ${showCredsResult.email}\nPassword: ${showCredsResult.password}`);
      toast.success('Credentials copied to clipboard!');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-sky-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-slate-600 font-medium">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-white/80 border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <GraduationCap className="w-10 h-10 text-sky-500" strokeWidth={2.5} />
              <h1 className="text-2xl font-bold text-slate-900">Admin Dashboard</h1>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right">
                <p className="text-sm text-slate-600">Admin</p>
                <p className="font-semibold text-slate-900">{user?.name}</p>
              </div>
              <Button onClick={handleLogout} variant="outline" className="rounded-full" data-testid="logout-button">
                <LogOut className="w-4 h-4 mr-2" />
                Logout
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Quick Actions */}
        <div className="flex flex-wrap gap-3 mb-6">
          <Button onClick={() => navigate('/demo-live-sheet')} className="bg-amber-400 hover:bg-amber-500 text-slate-900 rounded-full font-bold" data-testid="admin-demo-live-sheet">
            <Zap className="w-4 h-4 mr-2" /> Demo Live Sheet
          </Button>
          <Button onClick={() => navigate('/history')} className="bg-violet-500 hover:bg-violet-600 text-white rounded-full font-bold" data-testid="admin-history-link">
            <History className="w-4 h-4 mr-2" /> History & Search
          </Button>
          <Button onClick={() => navigate('/learning-kit')} variant="outline" className="rounded-full font-bold" data-testid="admin-learning-kit-link">
            <BookOpen className="w-4 h-4 mr-2" /> Learning Kit
          </Button>
        </div>

        <Tabs defaultValue="teachers" className="w-full">
          <TabsList className="mb-8 flex-wrap">
            <TabsTrigger value="teachers" data-testid="teachers-tab">Teachers</TabsTrigger>
            <TabsTrigger value="students" data-testid="students-tab">Add Student</TabsTrigger>
            <TabsTrigger value="classes" data-testid="classes-tab">Classes</TabsTrigger>
            <TabsTrigger value="proofs" data-testid="proofs-tab">Proofs ({pendingProofs.length})</TabsTrigger>
            <TabsTrigger value="transactions" data-testid="transactions-tab">Transactions</TabsTrigger>
            <TabsTrigger value="complaints" data-testid="complaints-tab">Complaints ({complaints.length})</TabsTrigger>
            <TabsTrigger value="badges" data-testid="badges-tab">Badges</TabsTrigger>
          </TabsList>

          <TabsContent value="teachers">
            <h2 className="text-2xl font-bold text-slate-900 mb-4">Teachers Management</h2>
            <Input placeholder="Search by name, ID (KL-T...), or email..." value={teacherSearch}
              onChange={e => handleTeacherSearch(e.target.value)}
              className="mb-4 bg-white border-2 border-slate-200 rounded-xl" data-testid="admin-teacher-search" />
            {(teacherSearch ? teacherSearchResults : teachers).length === 0 ? (
              <div className="bg-white rounded-3xl p-8 border-2 border-slate-100 text-center">
                <p className="text-slate-600">No teachers found</p>
              </div>
            ) : (
              <div className="space-y-3">
                {(teacherSearch ? teacherSearchResults : teachers).map(teacher => (
                  <div key={teacher.user_id} className="bg-white rounded-2xl border-2 border-slate-100 p-5 flex items-center justify-between" data-testid={`admin-teacher-${teacher.user_id}`}>
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 bg-gradient-to-br from-amber-400 to-amber-500 rounded-xl flex items-center justify-center text-white font-bold">
                        {teacher.name?.charAt(0)}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-bold text-slate-900">{teacher.name}</h3>
                          <span className="bg-sky-50 text-sky-700 px-2 py-0.5 rounded-full text-xs font-mono">{teacher.teacher_code || '—'}</span>
                          {teacher.badges?.map((b, i) => (
                            <span key={i} className="bg-violet-100 text-violet-700 px-2 py-0.5 rounded-full text-xs">{b}</span>
                          ))}
                        </div>
                        <p className="text-sm text-slate-500">{teacher.email}</p>
                        <p className="text-xs text-emerald-600 font-semibold">Wallet: {teacher.credits} credits</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${teacher.is_approved ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
                        {teacher.is_approved ? 'Approved' : 'Pending'}
                      </span>
                      {!teacher.is_approved && (
                        <>
                          <Button onClick={() => handleApproveTeacher(teacher.user_id, true)} size="sm" className="bg-emerald-500 text-white rounded-full" data-testid={`approve-${teacher.user_id}`}>
                            <Check className="w-4 h-4" />
                          </Button>
                          <Button onClick={() => handleApproveTeacher(teacher.user_id, false)} size="sm" variant="outline" className="rounded-full border-red-200 text-red-600" data-testid={`reject-${teacher.user_id}`}>
                            <X className="w-4 h-4" />
                          </Button>
                        </>
                      )}
                      <Button onClick={() => { setSelectedUser(teacher.user_id); setShowCreditsDialog(true); }} size="sm" variant="outline" className="rounded-full">
                        <DollarSign className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="students">
            <h2 className="text-2xl font-bold text-slate-900 mb-4">Create Student Account</h2>
            <div className="bg-white rounded-3xl border-2 border-slate-200 p-6 max-w-xl">
              {showCredsResult ? (
                <div className="space-y-4">
                  <div className="bg-emerald-50 rounded-xl p-6 border-2 border-emerald-200">
                    <h3 className="text-lg font-bold text-emerald-800 mb-3">Student Account Created!</h3>
                    <p className="text-sm text-slate-700 mb-1">Share these credentials with the student:</p>
                    <div className="bg-white rounded-lg p-4 mt-3 font-mono text-sm">
                      <p><strong>Email:</strong> {showCredsResult.email}</p>
                      <p><strong>Password:</strong> {showCredsResult.password}</p>
                    </div>
                    <div className="flex gap-2 mt-4">
                      <Button onClick={copyCredentials} className="bg-emerald-500 hover:bg-emerald-600 text-white rounded-full" data-testid="copy-credentials-button">
                        <Copy className="w-4 h-4 mr-2" /> Copy Credentials
                      </Button>
                      <Button onClick={() => setShowCredsResult(null)} variant="outline" className="rounded-full">
                        Create Another
                      </Button>
                    </div>
                  </div>
                </div>
              ) : (
                <form onSubmit={handleCreateStudent} className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div><Label>Name *</Label><Input value={newStudent.name} onChange={e => setNewStudent({...newStudent, name: e.target.value})} className="rounded-xl" required data-testid="student-name-input" /></div>
                    <div><Label>Email *</Label><Input type="email" value={newStudent.email} onChange={e => setNewStudent({...newStudent, email: e.target.value})} className="rounded-xl" required data-testid="student-email-input" /></div>
                    <div><Label>Password *</Label><Input value={newStudent.password} onChange={e => setNewStudent({...newStudent, password: e.target.value})} className="rounded-xl" required data-testid="student-password-input" /></div>
                    <div><Label>Phone</Label><Input value={newStudent.phone} onChange={e => setNewStudent({...newStudent, phone: e.target.value})} className="rounded-xl" data-testid="student-phone-input" /></div>
                    <div><Label>Grade/Class</Label>
                      <select value={newStudent.grade} onChange={e => setNewStudent({...newStudent, grade: e.target.value})}
                        className="w-full rounded-xl border-2 border-slate-200 px-3 py-2 bg-white h-10 text-sm" data-testid="student-grade-input">
                        <option value="">Select class...</option>
                        {['1','2','3','4','5','6','7','8','9','10','11','12','UG','PG','Other'].map(g => (
                          <option key={g} value={g}>{g === 'UG' || g === 'PG' || g === 'Other' ? g : `Class ${g}`}</option>
                        ))}
                      </select>
                    </div>
                    <div><Label>Institute</Label><Input value={newStudent.institute} onChange={e => setNewStudent({...newStudent, institute: e.target.value})} className="rounded-xl" data-testid="student-institute-input" /></div>
                    <div><Label>City</Label><Input value={newStudent.city} onChange={e => setNewStudent({...newStudent, city: e.target.value})} className="rounded-xl" placeholder="City" data-testid="student-city-input" /></div>
                    <div><Label>State</Label><Input value={newStudent.state} onChange={e => setNewStudent({...newStudent, state: e.target.value})} className="rounded-xl" placeholder="State" data-testid="student-state-input" /></div>
                    <div><Label>Country</Label><Input value={newStudent.country} onChange={e => setNewStudent({...newStudent, country: e.target.value})} className="rounded-xl" placeholder="Country" data-testid="student-country-input" /></div>
                    <div><Label>Goal</Label><Input value={newStudent.goal} onChange={e => setNewStudent({...newStudent, goal: e.target.value})} className="rounded-xl" data-testid="student-goal-input" /></div>
                    <div className="col-span-2"><Label>Preferred Time Slot</Label><Input value={newStudent.preferred_time_slot} onChange={e => setNewStudent({...newStudent, preferred_time_slot: e.target.value})} className="rounded-xl" placeholder="e.g., Weekdays 5-7 PM" data-testid="student-timeslot-input" /></div>
                  </div>
                  <Button type="submit" className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-full py-6 font-bold" data-testid="create-student-submit">
                    <UserPlus className="w-5 h-5 mr-2" /> Create Student Account
                  </Button>
                </form>
              )}
            </div>
          </TabsContent>

          <TabsContent value="classes">
            <h2 className="text-2xl font-bold text-slate-900 mb-4">All Classes</h2>
            {/* Filters */}
            <div className="bg-white rounded-2xl border-2 border-slate-100 p-4 mb-4 flex flex-wrap gap-3 items-end">
              <div className="flex-1 min-w-[200px]">
                <Label className="text-xs text-slate-500">Search</Label>
                <Input placeholder="Name, ID, subject..." value={classFilter.search}
                  onChange={e => setClassFilter({...classFilter, search: e.target.value})}
                  className="rounded-xl text-sm" data-testid="class-search-input" />
              </div>
              <div>
                <Label className="text-xs text-slate-500">Type</Label>
                <select value={classFilter.is_demo} onChange={e => setClassFilter({...classFilter, is_demo: e.target.value})}
                  className="rounded-xl border-2 border-slate-200 px-3 py-2 text-sm h-10" data-testid="class-type-filter">
                  <option value="">All</option>
                  <option value="true">Demo</option>
                  <option value="false">Regular</option>
                </select>
              </div>
              <div>
                <Label className="text-xs text-slate-500">Status</Label>
                <select value={classFilter.status} onChange={e => setClassFilter({...classFilter, status: e.target.value})}
                  className="rounded-xl border-2 border-slate-200 px-3 py-2 text-sm h-10" data-testid="class-status-filter">
                  <option value="">All</option>
                  <option value="scheduled">Scheduled</option>
                  <option value="in_progress">In Progress</option>
                  <option value="completed">Completed</option>
                </select>
              </div>
              <Button onClick={handleFilterClasses} className="bg-sky-500 hover:bg-sky-600 text-white rounded-xl h-10 px-4" data-testid="apply-class-filter">
                <Filter className="w-4 h-4 mr-1" /> Filter
              </Button>
            </div>
            {filteredClasses.length === 0 ? (
              <div className="bg-white rounded-3xl p-8 border-2 border-slate-100 text-center">
                <p className="text-slate-600">No classes found</p>
              </div>
            ) : (
              <div className="space-y-2">
                {filteredClasses.map(cls => (
                  <div key={cls.class_id} className="bg-white rounded-2xl border border-slate-100 p-4 flex items-center justify-between hover:bg-slate-50 transition-colors" data-testid={`class-row-${cls.class_id}`}>
                    <div className="flex items-center gap-3">
                      <div className={`w-3 h-3 rounded-full ${cls.is_demo ? 'bg-violet-500' : 'bg-sky-500'}`} />
                      <div>
                        <p className="font-semibold text-slate-900 text-sm">{cls.title}</p>
                        <p className="text-xs text-slate-500">Teacher: {cls.teacher_name} | {cls.date} - {cls.end_date || cls.date}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-500">{cls.class_id}</span>
                      {cls.is_demo && <span className="bg-violet-100 text-violet-700 px-2 py-0.5 rounded-full text-xs">Demo</span>}
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        cls.status === 'scheduled' ? 'bg-sky-100 text-sky-700' :
                        cls.status === 'in_progress' ? 'bg-emerald-100 text-emerald-700' :
                        'bg-slate-100 text-slate-600'
                      }`}>{cls.status}</span>
                      <span className="text-xs text-slate-600">{cls.enrolled_students?.length || 0}/{cls.max_students} students</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="transactions">
            <h2 className="text-2xl font-bold text-slate-900 mb-4">All Transactions</h2>
            {transactions.length === 0 ? (
              <div className="bg-white rounded-3xl p-8 border-2 border-slate-100 text-center">
                <p className="text-slate-600">No transactions yet</p>
              </div>
            ) : (
              <div className="bg-white rounded-2xl border-2 border-slate-200 overflow-hidden">
                <table className="w-full">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-slate-900">Type</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-slate-900">Amount</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-slate-900">Description</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-slate-900">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {transactions.map((txn) => (
                      <tr key={txn.transaction_id} className="border-t border-slate-100">
                        <td className="px-4 py-3 text-sm text-slate-900">{txn.type}</td>
                        <td className="px-4 py-3 text-sm text-slate-900">{txn.amount}</td>
                        <td className="px-4 py-3 text-sm text-slate-600">{txn.description}</td>
                        <td className="px-4 py-3 text-sm">
                          <span className="bg-emerald-100 text-emerald-800 px-2 py-1 rounded-full text-xs font-semibold">
                            {txn.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </TabsContent>

          <TabsContent value="complaints">
            <h2 className="text-2xl font-bold text-slate-900 mb-4">Complaints</h2>
            {complaints.length === 0 ? (
              <div className="bg-white rounded-3xl p-8 border-2 border-slate-100 text-center">
                <p className="text-slate-600">No complaints received</p>
              </div>
            ) : (
              <div className="space-y-4">
                {complaints.map(c => (
                  <div key={c.complaint_id} className="bg-white rounded-2xl border-2 border-slate-200 p-6" data-testid={`complaint-${c.complaint_id}`}>
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <h3 className="font-bold text-slate-900">{c.subject}</h3>
                        <p className="text-sm text-slate-500">By: {c.raised_by_name} ({c.raised_by_role})</p>
                      </div>
                      <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                        c.status === 'open' ? 'bg-amber-100 text-amber-800' :
                        c.status === 'resolved' ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-800'
                      }`}>{c.status.toUpperCase()}</span>
                    </div>
                    <p className="text-slate-600 text-sm mb-2">{c.description}</p>
                    {c.resolution && <p className="text-sm text-emerald-700 bg-emerald-50 p-2 rounded-lg">Resolution: {c.resolution}</p>}
                    <p className="text-xs text-slate-400 mt-2">{new Date(c.created_at).toLocaleDateString()}</p>
                  </div>
                ))}
              </div>
            )}
            <Button onClick={() => navigate('/complaints')} className="mt-4 bg-sky-500 hover:bg-sky-600 text-white rounded-full">
              <MessageSquare className="w-4 h-4 mr-2" /> Manage Complaints
            </Button>
          </TabsContent>

          <TabsContent value="proofs">
            <h2 className="text-2xl font-bold text-slate-900 mb-4">Proof Approvals (Counsellor-Verified)</h2>
            <div className="flex flex-wrap gap-3 items-end mb-4">
              <div>
                <Label className="text-xs text-slate-500">Date From</Label>
                <Input type="date" value={proofDateFrom} onChange={e => setProofDateFrom(e.target.value)}
                  className="rounded-xl text-sm w-44" data-testid="proof-date-from" />
              </div>
              <div>
                <Label className="text-xs text-slate-500">Date To</Label>
                <Input type="date" value={proofDateTo} onChange={e => setProofDateTo(e.target.value)}
                  className="rounded-xl text-sm w-44" data-testid="proof-date-to" />
              </div>
              <Button onClick={handleFilterProofs} className="bg-sky-500 hover:bg-sky-600 text-white rounded-xl h-10 px-4" data-testid="filter-proofs-btn">
                <Filter className="w-4 h-4 mr-1" /> Filter
              </Button>
            </div>
            {pendingProofs.length === 0 ? (
              <div className="bg-white rounded-3xl p-8 border-2 border-slate-100 text-center">
                <Shield className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                <p className="text-slate-600">No proofs pending your approval</p>
              </div>
            ) : (
              <div className="space-y-3">
                {pendingProofs.map(proof => (
                  <div key={proof.proof_id} className="bg-white rounded-2xl border-2 border-slate-100 p-5" data-testid={`proof-${proof.proof_id}`}>
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h3 className="font-bold text-slate-900">{proof.class_title || proof.class_details?.title || 'Class'}</h3>
                        <p className="text-sm text-slate-500">Submitted: {proof.submitted_at ? new Date(proof.submitted_at).toLocaleDateString() : '—'}</p>
                      </div>
                      <span className="bg-amber-100 text-amber-800 px-3 py-1 rounded-full text-xs font-semibold">
                        Awaiting Admin
                      </span>
                    </div>
                    {proof.class_details && (
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-3">
                        <div className="bg-slate-50 rounded-lg p-2 text-xs">
                          <p className="text-slate-500">Subject</p>
                          <p className="font-medium text-slate-800">{proof.class_details.subject}</p>
                        </div>
                        <div className="bg-slate-50 rounded-lg p-2 text-xs">
                          <p className="text-slate-500">Date</p>
                          <p className="font-medium text-slate-800">{proof.class_details.date}</p>
                        </div>
                        <div className="bg-slate-50 rounded-lg p-2 text-xs">
                          <p className="text-slate-500">Type</p>
                          <p className="font-medium text-slate-800">{proof.class_details.is_demo ? 'Demo' : 'Regular'}</p>
                        </div>
                        <div className="bg-slate-50 rounded-lg p-2 text-xs">
                          <p className="text-slate-500">Time</p>
                          <p className="font-medium text-slate-800">{proof.class_details.start_time} - {proof.class_details.end_time}</p>
                        </div>
                      </div>
                    )}
                    <div className="flex items-center gap-4 mb-3 text-sm">
                      {proof.teacher_details && (
                        <span className="text-slate-600">Teacher: <strong>{proof.teacher_details.name}</strong> ({proof.teacher_details.teacher_code || '—'})</span>
                      )}
                      {proof.student_details && (
                        <span className="text-slate-600">Student: <strong>{proof.student_details.name}</strong></span>
                      )}
                    </div>
                    {proof.description && <p className="text-sm text-slate-600 bg-slate-50 rounded-lg p-3 mb-3">{proof.description}</p>}
                    <div className="flex gap-2">
                      <Button onClick={() => handleApproveProof(proof.proof_id, true)} className="bg-emerald-500 hover:bg-emerald-600 text-white rounded-full flex-1" data-testid={`approve-proof-${proof.proof_id}`}>
                        <Check className="w-4 h-4 mr-1" /> Approve & Credit Teacher
                      </Button>
                      <Button onClick={() => handleApproveProof(proof.proof_id, false)} variant="outline" className="rounded-full border-red-200 text-red-600 flex-1" data-testid={`reject-proof-${proof.proof_id}`}>
                        <X className="w-4 h-4 mr-1" /> Reject
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="badges">
            <h2 className="text-2xl font-bold text-slate-900 mb-4">Badge Management</h2>
            <div className="bg-white rounded-3xl border-2 border-slate-100 p-6 max-w-xl mb-6">
              <h3 className="font-semibold text-slate-800 mb-3 flex items-center gap-2"><Award className="w-5 h-5 text-violet-500" /> Assign Badge</h3>
              <div className="space-y-3">
                <div>
                  <Label>Select Teacher/Counsellor</Label>
                  <select value={badgeTarget} onChange={e => setBadgeTarget(e.target.value)}
                    className="w-full rounded-xl border-2 border-slate-200 px-3 py-2 text-sm" data-testid="badge-user-select">
                    <option value="">Choose...</option>
                    <optgroup label="Teachers">
                      {teachers.map(t => <option key={t.user_id} value={t.user_id}>{t.name} ({t.teacher_code || t.email})</option>)}
                    </optgroup>
                  </select>
                </div>
                <div>
                  <Label>Badge Name</Label>
                  <Input value={badgeName} onChange={e => setBadgeName(e.target.value)}
                    placeholder="e.g., Star Teacher, Top Performer, Mentor"
                    className="rounded-xl" data-testid="badge-name-input" />
                </div>
                <Button onClick={handleAssignBadge} className="bg-violet-500 hover:bg-violet-600 text-white rounded-full" data-testid="assign-badge-btn">
                  <Award className="w-4 h-4 mr-2" /> Assign Badge
                </Button>
              </div>
            </div>
            {/* Show users with badges */}
            <div className="space-y-2">
              {teachers.filter(t => t.badges?.length > 0).map(t => (
                <div key={t.user_id} className="bg-white rounded-xl border border-slate-100 p-3 flex items-center justify-between">
                  <div>
                    <p className="font-semibold text-slate-900 text-sm">{t.name}</p>
                    <p className="text-xs text-slate-500">{t.teacher_code || t.email}</p>
                  </div>
                  <div className="flex gap-1">
                    {t.badges.map((b, i) => (
                      <span key={i} className="bg-violet-100 text-violet-700 px-3 py-1 rounded-full text-xs font-medium">{b}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </TabsContent>
        </Tabs>
      </div>

      <Dialog open={showCreditsDialog} onOpenChange={setShowCreditsDialog}>
        <DialogContent className="sm:max-w-md rounded-3xl">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold text-slate-900">Adjust Credits</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleAdjustCredits} className="space-y-4 mt-4">
            <div>
              <Label>Action</Label>
              <select
                value={creditAction}
                onChange={(e) => setCreditAction(e.target.value)}
                className="w-full rounded-xl border-2 border-slate-200 px-3 py-2"
                data-testid="credit-action-select"
              >
                <option value="add">Add Credits</option>
                <option value="deduct">Deduct Credits</option>
              </select>
            </div>
            <div>
              <Label>Amount</Label>
              <Input
                type="number"
                step="0.1"
                value={creditAmount}
                onChange={(e) => setCreditAmount(e.target.value)}
                className="rounded-xl"
                required
                data-testid="credit-amount-input"
              />
            </div>
            <Button
              type="submit"
              className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-full py-6 font-bold"
              data-testid="submit-adjust-credits-button"
            >
              Adjust Credits
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AdminDashboard;
