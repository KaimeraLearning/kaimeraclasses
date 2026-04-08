import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { toast } from 'sonner';
import { GraduationCap, LogOut, CreditCard, Calendar, Clock, Users, User, MessageSquare, Save } from 'lucide-react';
import { format, parseISO } from 'date-fns';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const StudentDashboard = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [credits, setCredits] = useState(0);
  const [upcomingClasses, setUpcomingClasses] = useState([]);
  const [pastClasses, setPastClasses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showProfileDialog, setShowProfileDialog] = useState(false);
  const [profileData, setProfileData] = useState({ institute: '', goal: '', preferred_time_slot: '', phone: '' });

  useEffect(() => { fetchDashboardData(); }, []);

  const fetchDashboardData = async () => {
    try {
      const [userRes, dashboardRes] = await Promise.all([
        fetch(`${API}/auth/me`, { credentials: 'include' }),
        fetch(`${API}/student/dashboard`, { credentials: 'include' })
      ]);
      if (!userRes.ok || !dashboardRes.ok) throw new Error('Failed to fetch data');
      const userData = await userRes.json();
      const dashboardData = await dashboardRes.json();
      setUser(userData);
      setCredits(dashboardData.credits);
      setUpcomingClasses(dashboardData.upcoming_classes);
      setPastClasses(dashboardData.past_classes);
      setProfileData({
        institute: userData.institute || '', goal: userData.goal || '',
        preferred_time_slot: userData.preferred_time_slot || '', phone: userData.phone || ''
      });
      setLoading(false);
    } catch (error) {
      toast.error('Failed to load dashboard');
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    try { await fetch(`${API}/auth/logout`, { method: 'POST', credentials: 'include' }); navigate('/login'); } catch {}
  };

  const handleCancelBooking = async (classId) => {
    try {
      const response = await fetch(`${API}/classes/cancel/${classId}`, { method: 'POST', credentials: 'include' });
      if (!response.ok) throw new Error((await response.json()).detail);
      toast.success('Booking cancelled and credits refunded');
      fetchDashboardData();
    } catch (error) { toast.error(error.message); }
  };

  const handleUpdateProfile = async () => {
    try {
      const response = await fetch(`${API}/student/update-profile`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
        body: JSON.stringify(profileData)
      });
      if (!response.ok) throw new Error((await response.json()).detail);
      toast.success('Profile updated!');
      setShowProfileDialog(false);
      fetchDashboardData();
    } catch (error) { toast.error(error.message); }
  };

  const canJoinClass = (classDate, startTime) => {
    const now = new Date();
    const classDateTime = new Date(`${classDate}T${startTime}:00`);
    return now >= new Date(classDateTime.getTime() - 5 * 60000) && now <= classDateTime;
  };

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="w-16 h-16 border-4 border-sky-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-white/80 border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <GraduationCap className="w-10 h-10 text-sky-500" strokeWidth={2.5} />
              <h1 className="text-2xl font-bold text-slate-900">Kaimera Learning</h1>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right">
                <p className="text-sm text-slate-600">Welcome back,</p>
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
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-gradient-to-br from-sky-500 to-sky-600 rounded-3xl p-6 text-white shadow-[4px_4px_0px_0px_rgba(14,165,233,0.3)]">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sky-100 text-sm font-medium mb-1">Available Credits</p>
                <p className="text-4xl font-bold" data-testid="credits-balance">{credits}</p>
              </div>
              <CreditCard className="w-12 h-12 text-sky-200" />
            </div>
            <Button onClick={() => navigate('/browse-classes')} className="w-full mt-4 bg-white text-sky-600 hover:bg-slate-50 rounded-full font-bold" data-testid="buy-credits-button">
              Buy More Credits
            </Button>
          </div>
          <div className="bg-white rounded-3xl p-6 border-2 border-slate-100 shadow-[4px_4px_0px_0px_rgba(226,232,240,1)]">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-600 text-sm font-medium mb-1">Upcoming Classes</p>
                <p className="text-4xl font-bold text-slate-900">{upcomingClasses.length}</p>
              </div>
              <Calendar className="w-12 h-12 text-amber-400" />
            </div>
          </div>
          <div className="bg-white rounded-3xl p-6 border-2 border-slate-100 shadow-[4px_4px_0px_0px_rgba(226,232,240,1)]">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-600 text-sm font-medium mb-1">Completed Classes</p>
                <p className="text-4xl font-bold text-slate-900">{pastClasses.length}</p>
              </div>
              <GraduationCap className="w-12 h-12 text-emerald-500" />
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="flex flex-wrap gap-3 mb-8">
          <Button onClick={() => navigate('/browse-classes')} className="bg-amber-400 hover:bg-amber-500 text-slate-900 rounded-full px-6 py-5 font-bold shadow-[0_4px_14px_0_rgba(245,158,11,0.39)]" data-testid="browse-classes-button">
            Browse Available Classes
          </Button>
          <Button onClick={() => setShowProfileDialog(true)} variant="outline" className="rounded-full px-6 py-5 font-bold" data-testid="edit-profile-button">
            <User className="w-4 h-4 mr-2" /> Edit Profile
          </Button>
          <Button onClick={() => navigate('/complaints')} variant="outline" className="rounded-full px-6 py-5 font-bold" data-testid="complaints-button">
            <MessageSquare className="w-4 h-4 mr-2" /> Complaints
          </Button>
        </div>

        {/* Upcoming Classes */}
        <div className="mb-8">
          <h2 className="text-xl font-bold text-slate-900 mb-4">Upcoming Classes</h2>
          {upcomingClasses.length === 0 ? (
            <div className="bg-white rounded-3xl p-8 border-2 border-slate-100 text-center">
              <p className="text-slate-600">No upcoming classes. Browse and book a class!</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {upcomingClasses.map(cls => (
                <div key={cls.class_id} className="bg-white rounded-3xl border-2 border-slate-200 shadow-[4px_4px_0px_0px_rgba(226,232,240,1)] overflow-hidden" data-testid={`upcoming-class-${cls.class_id}`}>
                  <div className="p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <h3 className="text-xl font-bold text-slate-900 mb-1">{cls.title}</h3>
                        <p className="text-sm text-slate-600">{cls.teacher_name}</p>
                      </div>
                      <div className="flex gap-2">
                        <span className="bg-sky-100 text-sky-800 px-3 py-1 rounded-full text-xs font-semibold">{cls.subject}</span>
                        {cls.is_demo && <span className="bg-violet-100 text-violet-800 px-3 py-1 rounded-full text-xs font-semibold">DEMO</span>}
                      </div>
                    </div>
                    <div className="space-y-2 mb-4">
                      <div className="flex items-center gap-2 text-slate-600">
                        <Calendar className="w-4 h-4" /><span className="text-sm">{format(parseISO(cls.date), 'MMM dd, yyyy')}</span>
                      </div>
                      <div className="flex items-center gap-2 text-slate-600">
                        <Clock className="w-4 h-4" /><span className="text-sm">{cls.start_time} - {cls.end_time}</span>
                      </div>
                      <div className="flex items-center gap-2 text-slate-600">
                        <Users className="w-4 h-4" /><span className="text-sm">{cls.enrolled_students.length} / {cls.max_students} students</span>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      {canJoinClass(cls.date, cls.start_time) && (
                        <Button onClick={() => navigate(`/class/${cls.class_id}`)} className="flex-1 bg-emerald-500 hover:bg-emerald-600 text-white rounded-full font-bold" data-testid={`join-class-button-${cls.class_id}`}>
                          Join Class
                        </Button>
                      )}
                      <Button onClick={() => handleCancelBooking(cls.class_id)} variant="outline" className="flex-1 rounded-full border-2 hover:bg-red-50 hover:border-red-200" data-testid={`cancel-booking-button-${cls.class_id}`}>
                        Cancel Booking
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Past Classes */}
        <div>
          <h2 className="text-xl font-bold text-slate-900 mb-4">Past Classes</h2>
          {pastClasses.length === 0 ? (
            <div className="bg-white rounded-3xl p-8 border-2 border-slate-100 text-center">
              <p className="text-slate-600">No past classes yet.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {pastClasses.map(cls => (
                <div key={cls.class_id} className="bg-white rounded-3xl border-2 border-slate-100 p-6 opacity-80">
                  <h3 className="text-lg font-bold text-slate-900 mb-1">{cls.title}</h3>
                  <p className="text-sm text-slate-600 mb-2">{cls.teacher_name}</p>
                  <p className="text-xs text-slate-500">{format(parseISO(cls.date), 'MMM dd, yyyy')}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Edit Profile Dialog */}
      <Dialog open={showProfileDialog} onOpenChange={setShowProfileDialog}>
        <DialogContent className="sm:max-w-md rounded-3xl">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold text-slate-900">Edit Profile</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <div>
              <Label>Phone Number</Label>
              <Input value={profileData.phone} onChange={e => setProfileData({ ...profileData, phone: e.target.value })}
                className="rounded-xl" placeholder="Your phone number" data-testid="profile-phone-input" />
            </div>
            <div>
              <Label>Institute</Label>
              <Input value={profileData.institute} onChange={e => setProfileData({ ...profileData, institute: e.target.value })}
                className="rounded-xl" placeholder="Your school/college/institute" data-testid="profile-institute-input" />
            </div>
            <div>
              <Label>Goal</Label>
              <Input value={profileData.goal} onChange={e => setProfileData({ ...profileData, goal: e.target.value })}
                className="rounded-xl" placeholder="e.g., Crack JEE, Learn Guitar" data-testid="profile-goal-input" />
            </div>
            <div>
              <Label>Preferred Time Slot</Label>
              <Input value={profileData.preferred_time_slot} onChange={e => setProfileData({ ...profileData, preferred_time_slot: e.target.value })}
                className="rounded-xl" placeholder="e.g., Weekdays 5-7 PM" data-testid="profile-timeslot-input" />
            </div>
            <Button onClick={handleUpdateProfile} className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-full py-6 font-bold" data-testid="save-profile-button">
              <Save className="w-5 h-5 mr-2" /> Save Profile
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default StudentDashboard;
