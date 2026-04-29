import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { ArrowLeft, ChevronLeft, ChevronRight, Calendar as CalendarIcon } from 'lucide-react';
import { format, addMonths, subMonths, startOfMonth, endOfMonth, eachDayOfInterval, parseISO } from 'date-fns';

import { API , apiFetch} from '../utils/api';

const TeacherSchedule = () => {
  const navigate = useNavigate();
  const { teacherId } = useParams();
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [teacher, setTeacher] = useState(null);
  const [classes, setClasses] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTeacherSchedule();
  }, [teacherId]);

  const fetchTeacherSchedule = async () => {
    try {
      const response = await apiFetch(`${API}/admin/classes`, { credentials: 'include' });
      if (!response.ok) throw new Error('Failed to fetch');
      const allClasses = await response.json();
      const teacherClasses = allClasses.filter(c => c.teacher_id === teacherId);
      setClasses(teacherClasses);
      if (teacherClasses.length > 0) setTeacher({ name: teacherClasses[0].teacher_name });
      setLoading(false);
    } catch (error) {
      toast.error('Failed to load schedule');
      setLoading(false);
    }
  };

  const getClassesForDate = (date) => {
    const dateStr = format(date, 'yyyy-MM-dd');
    return classes.filter(cls => {
      const startDate = cls.date;
      const endDate = cls.end_date || cls.date;
      return dateStr >= startDate && dateStr <= endDate;
    });
  };

  const renderCalendar = () => {
    const monthStart = startOfMonth(currentMonth);
    const monthEnd = endOfMonth(currentMonth);
    const daysInMonth = eachDayOfInterval({ start: monthStart, end: monthEnd });
    const firstDayOfWeek = monthStart.getDay();
    const leadingEmptyCells = Array(firstDayOfWeek).fill(null);

    return (
      <div className="grid grid-cols-7 gap-2">
        {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
          <div key={day} className="text-center font-semibold text-slate-600 py-2 text-sm">{day}</div>
        ))}
        {leadingEmptyCells.map((_, idx) => (
          <div key={`empty-${idx}`} className="aspect-square"></div>
        ))}
        {daysInMonth.map(date => {
          const dayClasses = getClassesForDate(date);
          const hasClasses = dayClasses.length > 0;
          const hasLive = dayClasses.some(c => c.status === 'in_progress');
          const hasDismissed = dayClasses.every(c => c.status === 'dismissed');

          let bgClass = 'bg-white border-slate-200';
          if (hasLive) bgClass = 'bg-emerald-100 border-emerald-500';
          else if (hasDismissed) bgClass = 'bg-red-50 border-red-300';
          else if (hasClasses) bgClass = 'bg-sky-100 border-sky-500';

          return (
            <div key={date.toISOString()} className={`aspect-square rounded-xl border-2 p-1.5 ${bgClass}`}>
              <div className="text-sm font-semibold text-slate-900">{format(date, 'd')}</div>
              {hasClasses && (
                <div className="mt-0.5">
                  {dayClasses.map(cls => (
                    <div key={cls.class_id} className="mb-0.5">
                      <div className={`text-[10px] font-bold px-1 py-0.5 rounded ${
                        cls.status === 'in_progress' ? 'bg-emerald-200 text-emerald-800' :
                        cls.status === 'completed' ? 'bg-slate-200 text-slate-600' :
                        cls.status === 'dismissed' ? 'bg-red-200 text-red-700' :
                        'bg-sky-200 text-sky-800'
                      }`}>
                        {cls.status === 'in_progress' ? 'LIVE' :
                         cls.status === 'completed' ? 'DONE' :
                         cls.status === 'dismissed' ? 'OFF' :
                         'BOOKED'}
                      </div>
                      <div className="text-[10px] text-slate-600 truncate">{cls.start_time}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  };

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
            <Button onClick={() => navigate(-1)} variant="outline" className="rounded-full">
              <ArrowLeft className="w-4 h-4 mr-2" /> Back
            </Button>
            <div>
              <h1 className="text-2xl font-bold text-slate-900">Teacher Schedule</h1>
              <p className="text-sm text-slate-600">{teacher?.name}</p>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-3xl border-2 border-slate-200 p-8">
          <div className="flex items-center justify-between mb-8">
            <Button onClick={() => setCurrentMonth(subMonths(currentMonth, 1))} variant="outline" className="rounded-full"><ChevronLeft className="w-5 h-5" /></Button>
            <div className="flex items-center gap-3">
              <CalendarIcon className="w-6 h-6 text-sky-500" />
              <h2 className="text-2xl font-bold text-slate-900">{format(currentMonth, 'MMMM yyyy')}</h2>
            </div>
            <Button onClick={() => setCurrentMonth(addMonths(currentMonth, 1))} variant="outline" className="rounded-full"><ChevronRight className="w-5 h-5" /></Button>
          </div>

          {renderCalendar()}

          <div className="mt-8 flex flex-wrap items-center gap-4 text-sm">
            <div className="flex items-center gap-2"><div className="w-6 h-4 bg-sky-200 rounded text-[10px] text-sky-800 font-bold flex items-center justify-center">BOOKED</div><span className="text-slate-600">Scheduled</span></div>
            <div className="flex items-center gap-2"><div className="w-6 h-4 bg-emerald-200 rounded text-[10px] text-emerald-800 font-bold flex items-center justify-center">LIVE</div><span className="text-slate-600">In Progress</span></div>
            <div className="flex items-center gap-2"><div className="w-6 h-4 bg-slate-200 rounded text-[10px] text-slate-600 font-bold flex items-center justify-center">DONE</div><span className="text-slate-600">Completed</span></div>
            <div className="flex items-center gap-2"><div className="w-6 h-4 bg-red-200 rounded text-[10px] text-red-700 font-bold flex items-center justify-center">OFF</div><span className="text-slate-600">Dismissed</span></div>
          </div>

          <div className="mt-6 bg-slate-50 rounded-xl p-4">
            <p className="text-slate-600">Total classes: <span className="font-bold text-slate-900">{classes.length}</span></p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TeacherSchedule;
