import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';
import { GraduationCap, LogOut, Check, X, DollarSign, MessageSquare, UserPlus, Copy } from 'lucide-react';

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
    name: '', email: '', password: '', institute: '', goal: '', preferred_time_slot: '', phone: ''
  });

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
      setNewStudent({ name: '', email: '', password: '', institute: '', goal: '', preferred_time_slot: '', phone: '' });
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
        <Tabs defaultValue="teachers" className="w-full">
          <TabsList className="mb-8">
            <TabsTrigger value="teachers" data-testid="teachers-tab">Teachers</TabsTrigger>
            <TabsTrigger value="students" data-testid="students-tab">Add Student</TabsTrigger>
            <TabsTrigger value="classes" data-testid="classes-tab">Classes</TabsTrigger>
            <TabsTrigger value="transactions" data-testid="transactions-tab">Transactions</TabsTrigger>
            <TabsTrigger value="complaints" data-testid="complaints-tab">Complaints ({complaints.length})</TabsTrigger>
          </TabsList>

          <TabsContent value="teachers">
            <h2 className="text-2xl font-bold text-slate-900 mb-4">Teacher Approvals</h2>
            {teachers.length === 0 ? (
              <div className="bg-white rounded-3xl p-8 border-2 border-slate-100 text-center">
                <p className="text-slate-600">No teachers to display</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {teachers.map((teacher) => (
                  <div
                    key={teacher.user_id}
                    className="bg-white rounded-2xl border-2 border-slate-200 p-6"
                    data-testid={`teacher-card-${teacher.user_id}`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h3 className="font-bold text-slate-900">{teacher.name}</h3>
                        <p className="text-sm text-slate-600">{teacher.email}</p>
                        <p className="text-sm text-slate-500 mt-2">Credits: {teacher.credits}</p>
                      </div>
                      <div>
                        {teacher.is_approved ? (
                          <span className="bg-emerald-100 text-emerald-800 px-3 py-1 rounded-full text-xs font-semibold">
                            Approved
                          </span>
                        ) : (
                          <span className="bg-amber-100 text-amber-800 px-3 py-1 rounded-full text-xs font-semibold">
                            Pending
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex gap-2 mt-4">
                      {!teacher.is_approved && (
                        <>
                          <Button
                            onClick={() => handleApproveTeacher(teacher.user_id, true)}
                            className="flex-1 bg-emerald-500 hover:bg-emerald-600 text-white rounded-full"
                            data-testid={`approve-teacher-button-${teacher.user_id}`}
                          >
                            <Check className="w-4 h-4 mr-2" />
                            Approve
                          </Button>
                          <Button
                            onClick={() => handleApproveTeacher(teacher.user_id, false)}
                            variant="outline"
                            className="flex-1 rounded-full"
                            data-testid={`reject-teacher-button-${teacher.user_id}`}
                          >
                            <X className="w-4 h-4 mr-2" />
                            Reject
                          </Button>
                        </>
                      )}
                      <Button
                        onClick={() => {
                          setSelectedUser(teacher.user_id);
                          setShowCreditsDialog(true);
                        }}
                        variant="outline"
                        className="rounded-full"
                        data-testid={`adjust-credits-button-${teacher.user_id}`}
                      >
                        <DollarSign className="w-4 h-4 mr-2" />
                        Adjust Credits
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
                    <div><Label>Institute</Label><Input value={newStudent.institute} onChange={e => setNewStudent({...newStudent, institute: e.target.value})} className="rounded-xl" data-testid="student-institute-input" /></div>
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
            {classes.length === 0 ? (
              <div className="bg-white rounded-3xl p-8 border-2 border-slate-100 text-center">
                <p className="text-slate-600">No classes created yet</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {classes.map((cls) => (
                  <div
                    key={cls.class_id}
                    className="bg-white rounded-2xl border-2 border-slate-200 p-4"
                    data-testid={`class-card-${cls.class_id}`}
                  >
                    <h3 className="font-bold text-slate-900">{cls.title}</h3>
                    <p className="text-sm text-slate-600">{cls.teacher_name}</p>
                    <p className="text-xs text-slate-500 mt-2">
                      {cls.enrolled_students.length} / {cls.max_students} students
                    </p>
                    <span className="inline-block mt-2 bg-sky-100 text-sky-800 px-2 py-1 rounded-full text-xs font-semibold">
                      {cls.status}
                    </span>
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
