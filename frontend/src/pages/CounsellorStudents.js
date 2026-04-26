import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { toast } from 'sonner';
import { ArrowLeft, User, CreditCard, Calendar, MapPin, Target, CalendarClock, Phone, Search } from 'lucide-react';

import { API } from '../utils/api';

const CounsellorStudents = () => {
  const navigate = useNavigate();
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [studentProfile, setStudentProfile] = useState(null);
  const [showDetailsDialog, setShowDetailsDialog] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => { fetchStudents(); }, []);

  const fetchStudents = async () => {
    try {
      const response = await fetch(`${API}/counsellor/dashboard`, { credentials: 'include' });
      if (!response.ok) throw new Error('Failed to fetch');
      const data = await response.json();
      setStudents(data.all_students || []);
      setLoading(false);
    } catch (error) {
      toast.error('Failed to load students');
      setLoading(false);
    }
  };

  const handleViewDetails = async (student) => {
    setSelectedStudent(student);
    setStudentProfile(null);
    setShowDetailsDialog(true);
    try {
      const res = await fetch(`${API}/counsellor/student-profile/${student.user_id}`, { credentials: 'include' });
      if (res.ok) setStudentProfile(await res.json());
    } catch (error) { console.error(error); }
  };

  const filteredStudents = students.filter(s =>
    !searchQuery ||
    s.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.email?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.student_code?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.phone?.includes(searchQuery) ||
    s.institute?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.city?.toLowerCase().includes(searchQuery.toLowerCase())
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
          <div className="flex items-center gap-4">
            <Button onClick={() => navigate('/counsellor-dashboard')} variant="outline" className="rounded-full">
              <ArrowLeft className="w-4 h-4 mr-2" /> Back
            </Button>
            <h1 className="text-2xl font-bold text-slate-900">All Students ({students.length})</h1>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Search Bar */}
        <div className="relative mb-6">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <Input
            placeholder="Search by name, email, phone, ID, institute, or city..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="pl-10 rounded-xl border-2 border-slate-200 bg-white"
            data-testid="counsellor-student-search"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredStudents.map(student => (
            <div key={student.user_id}
              className="bg-white rounded-2xl border-2 border-slate-200 p-6 hover:shadow-lg transition-all cursor-pointer"
              onClick={() => handleViewDetails(student)} data-testid={`student-card-${student.user_id}`}>
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <h3 className="font-bold text-slate-900 text-lg">{student.name}</h3>
                  <p className="text-sm text-slate-600">{student.email}</p>
                </div>
                <User className="w-10 h-10 text-sky-500 opacity-30" />
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-2 text-slate-600">
                  <CreditCard className="w-4 h-4" />
                  <span>{student.credits} credits</span>
                </div>
                {student.institute && (
                  <div className="flex items-center gap-2 text-slate-600">
                    <MapPin className="w-4 h-4" />
                    <span>{student.institute}</span>
                  </div>
                )}
                {student.goal && (
                  <div className="flex items-center gap-2 text-slate-600">
                    <Target className="w-4 h-4" />
                    <span>{student.goal}</span>
                  </div>
                )}
                <div className="flex items-center gap-2 text-slate-600">
                  <Calendar className="w-4 h-4" />
                  <span>Joined: {new Date(student.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Student Details Dialog */}
      <Dialog open={showDetailsDialog} onOpenChange={(open) => { setShowDetailsDialog(open); if (!open) setStudentProfile(null); }}>
        <DialogContent className="sm:max-w-2xl rounded-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold text-slate-900">Student Profile</DialogTitle>
          </DialogHeader>
          {selectedStudent && (
            <div className="space-y-5">
              <div className="bg-gradient-to-br from-sky-500 to-sky-600 rounded-2xl p-6 text-white">
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center">
                    <User className="w-8 h-8" />
                  </div>
                  <div>
                    <h3 className="text-2xl font-bold">{selectedStudent.name}</h3>
                    <p className="text-sky-100">{selectedStudent.email}</p>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-50 rounded-xl p-4">
                  <p className="text-sm text-slate-600 mb-1"><CreditCard className="w-3 h-3 inline mr-1" />Credits</p>
                  <p className="text-2xl font-bold text-slate-900">{selectedStudent.credits}</p>
                </div>
                <div className="bg-slate-50 rounded-xl p-4">
                  <p className="text-sm text-slate-600 mb-1"><Phone className="w-3 h-3 inline mr-1" />Phone</p>
                  <p className="text-lg font-semibold text-slate-900">{selectedStudent.phone || 'Not provided'}</p>
                </div>
                <div className="bg-slate-50 rounded-xl p-4">
                  <p className="text-sm text-slate-600 mb-1"><MapPin className="w-3 h-3 inline mr-1" />Institute</p>
                  <p className="text-lg font-semibold text-slate-900">{selectedStudent.institute || 'Not provided'}</p>
                </div>
                <div className="bg-slate-50 rounded-xl p-4">
                  <p className="text-sm text-slate-600 mb-1"><Target className="w-3 h-3 inline mr-1" />Goal</p>
                  <p className="text-lg font-semibold text-slate-900">{selectedStudent.goal || 'Not provided'}</p>
                </div>
                <div className="bg-slate-50 rounded-xl p-4 col-span-2">
                  <p className="text-sm text-slate-600 mb-1"><CalendarClock className="w-3 h-3 inline mr-1" />Preferred Time Slot</p>
                  <p className="text-lg font-semibold text-slate-900">{selectedStudent.preferred_time_slot || 'Not provided'}</p>
                </div>
                <div className="bg-slate-50 rounded-xl p-4">
                  <p className="text-sm text-slate-600 mb-1">Joined</p>
                  <p className="text-sm font-semibold text-slate-900">{new Date(selectedStudent.created_at).toLocaleDateString()}</p>
                </div>
                <div className="bg-slate-50 rounded-xl p-4">
                  <p className="text-sm text-slate-600 mb-1">User ID</p>
                  <p className="text-xs font-mono text-slate-900">{selectedStudent.user_id}</p>
                </div>
              </div>

              {/* Current Assignment */}
              {studentProfile?.current_assignment ? (
                <div className="bg-emerald-50 rounded-xl p-4 border-2 border-emerald-200">
                  <p className="text-sm font-semibold text-emerald-800 mb-2">Current Assignment</p>
                  <p className="text-slate-900">Teacher: <strong>{studentProfile.current_assignment.teacher_name}</strong></p>
                  <p className="text-sm text-slate-600">Status: {studentProfile.current_assignment.status} | Price: {studentProfile.current_assignment.credit_price}/class</p>
                </div>
              ) : (
                <div className="bg-amber-50 rounded-xl p-4 border-2 border-amber-200">
                  <p className="text-sm text-amber-800 font-semibold">Not currently assigned to any teacher</p>
                </div>
              )}

              {/* Class History */}
              {studentProfile?.class_history && studentProfile.class_history.length > 0 && (
                <div>
                  <p className="text-sm font-semibold text-slate-700 mb-2">Class History ({studentProfile.class_history.length})</p>
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {studentProfile.class_history.map(cls => (
                      <div key={cls.class_id} className={`rounded-lg p-3 ${cls.status === 'cancelled' ? 'bg-red-50' : cls.rescheduled ? 'bg-amber-50' : 'bg-slate-50'}`}>
                        <div className="flex justify-between items-start">
                          <div>
                            <p className="font-medium text-slate-900 text-sm">{cls.title}</p>
                            <p className="text-xs text-slate-500">{cls.date} | {cls.teacher_name}</p>
                            {cls.status === 'cancelled' && cls.cancelled_by && (
                              <p className="text-xs text-red-600 font-semibold mt-0.5">Cancelled by: {cls.cancelled_by}</p>
                            )}
                            {cls.rescheduled && (
                              <p className="text-xs text-amber-700 font-semibold mt-0.5">Rescheduled to: {cls.rescheduled_date} {cls.rescheduled_start_time}-{cls.rescheduled_end_time}</p>
                            )}
                            {cls.reschedule_count > 0 && (
                              <p className="text-xs text-amber-600 mt-0.5">Rescheduled {cls.reschedule_count} time(s)</p>
                            )}
                          </div>
                          <div className="flex flex-col items-end gap-1">
                            <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                              cls.status === 'cancelled' ? 'bg-red-200 text-red-800' :
                              cls.status === 'completed' ? 'bg-emerald-100 text-emerald-800' :
                              cls.status === 'scheduled' ? 'bg-sky-100 text-sky-800' : 'bg-slate-100 text-slate-800'
                            }`}>{cls.status}</span>
                            {cls.rescheduled && <span className="bg-amber-200 text-amber-800 px-2 py-0.5 rounded-full text-[10px] font-bold">RESCHEDULED</span>}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default CounsellorStudents;
