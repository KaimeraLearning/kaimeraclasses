import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { ArrowLeft, ChevronLeft, ChevronRight, Calendar as CalendarIcon, Clock, Users, AlertCircle } from 'lucide-react';
import { format, addMonths, subMonths, startOfMonth, endOfMonth, eachDayOfInterval } from 'date-fns';

import { API , apiFetch} from '../utils/api';

const TeacherCalendar = () => {
  const navigate = useNavigate();
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [classes, setClasses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedDay, setSelectedDay] = useState(null);
  const [dayClasses, setDayClasses] = useState([]);

  useEffect(() => { fetchSchedule(); }, []);

  const fetchSchedule = async () => {
    try {
      const res = await apiFetch(`${API}/teacher/schedule`, { credentials: 'include' });
      if (!res.ok) throw new Error('Failed to fetch schedule');
      setClasses(await res.json());
    } catch (err) { toast.error(err.message); }
    setLoading(false);
  };

  const getClassesForDate = (date) => {
    const dateStr = format(date, 'yyyy-MM-dd');
    return classes.filter(cls => {
      const startDate = cls.date;
      const endDate = cls.end_date || cls.date;
      return dateStr >= startDate && dateStr <= endDate;
    });
  };

  const handleDayClick = (date) => {
    const dc = getClassesForDate(date);
    setSelectedDay(format(date, 'yyyy-MM-dd'));
    setDayClasses(dc);
  };

  const renderCalendar = () => {
    const monthStart = startOfMonth(currentMonth);
    const monthEnd = endOfMonth(currentMonth);
    const daysInMonth = eachDayOfInterval({ start: monthStart, end: monthEnd });
    const firstDayOfWeek = monthStart.getDay();
    const leadingEmptyCells = Array(firstDayOfWeek).fill(null);
    const today = format(new Date(), 'yyyy-MM-dd');

    return (
      <div className="grid grid-cols-7 gap-1.5">
        {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
          <div key={day} className="text-center font-semibold text-slate-600 py-2 text-xs">{day}</div>
        ))}
        {leadingEmptyCells.map((_, idx) => <div key={`e-${idx}`} className="aspect-square" />)}
        {daysInMonth.map(date => {
          const dateStr = format(date, 'yyyy-MM-dd');
          const dc = getClassesForDate(date);
          const hasClasses = dc.length > 0;
          const isToday = dateStr === today;
          const isSelected = dateStr === selectedDay;
          const hasLive = dc.some(c => c.status === 'in_progress');
          const hasCancelled = dc.some(c => c.cancelled_today);

          let bgClass = 'bg-white border-slate-200 hover:border-sky-300';
          if (isSelected) bgClass = 'bg-sky-100 border-sky-500 ring-2 ring-sky-200';
          else if (hasLive) bgClass = 'bg-emerald-100 border-emerald-400';
          else if (hasCancelled) bgClass = 'bg-red-50 border-red-300';
          else if (hasClasses) bgClass = 'bg-sky-50 border-sky-300';

          return (
            <div key={dateStr} onClick={() => handleDayClick(date)}
              className={`aspect-square rounded-xl border-2 p-1 cursor-pointer transition-all ${bgClass}`}>
              <div className={`text-xs font-bold ${isToday ? 'text-sky-600' : 'text-slate-700'}`}>
                {format(date, 'd')}
                {isToday && <span className="ml-0.5 text-[8px] text-sky-500">TODAY</span>}
              </div>
              {hasClasses && (
                <div className="mt-0.5 space-y-0.5">
                  {dc.slice(0, 2).map(cls => (
                    <div key={cls.class_id} className={`text-[9px] font-bold px-0.5 py-0 rounded truncate ${
                      cls.status === 'in_progress' ? 'bg-emerald-200 text-emerald-800' :
                      cls.cancelled_today ? 'bg-red-200 text-red-700' :
                      'bg-sky-200 text-sky-800'
                    }`}>
                      {cls.start_time}
                    </div>
                  ))}
                  {dc.length > 2 && <div className="text-[8px] text-slate-500 font-medium">+{dc.length - 2} more</div>}
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
      <div className="w-16 h-16 border-4 border-sky-500 border-t-transparent rounded-full animate-spin" />
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-white/80 border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center gap-4">
            <Button onClick={() => navigate('/teacher-dashboard')} variant="outline" className="rounded-full" data-testid="back-btn">
              <ArrowLeft className="w-4 h-4 mr-2" /> Back
            </Button>
            <div>
              <h1 className="text-2xl font-bold text-slate-900">My Schedule Planner</h1>
              <p className="text-sm text-slate-600">{classes.length} scheduled classes</p>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Calendar */}
          <div className="lg:col-span-2 bg-white rounded-3xl border-2 border-slate-200 p-6">
            <div className="flex items-center justify-between mb-6">
              <Button onClick={() => setCurrentMonth(subMonths(currentMonth, 1))} variant="outline" className="rounded-full" data-testid="prev-month"><ChevronLeft className="w-5 h-5" /></Button>
              <div className="flex items-center gap-3">
                <CalendarIcon className="w-6 h-6 text-sky-500" />
                <h2 className="text-xl font-bold text-slate-900" data-testid="current-month">{format(currentMonth, 'MMMM yyyy')}</h2>
              </div>
              <Button onClick={() => setCurrentMonth(addMonths(currentMonth, 1))} variant="outline" className="rounded-full" data-testid="next-month"><ChevronRight className="w-5 h-5" /></Button>
            </div>
            {renderCalendar()}

            <div className="mt-6 flex flex-wrap items-center gap-3 text-xs">
              <div className="flex items-center gap-1.5"><div className="w-4 h-3 bg-sky-200 rounded" /><span className="text-slate-600">Scheduled</span></div>
              <div className="flex items-center gap-1.5"><div className="w-4 h-3 bg-emerald-200 rounded" /><span className="text-slate-600">Live</span></div>
              <div className="flex items-center gap-1.5"><div className="w-4 h-3 bg-red-200 rounded" /><span className="text-slate-600">Cancelled</span></div>
            </div>
          </div>

          {/* Day Detail Panel */}
          <div className="bg-white rounded-3xl border-2 border-slate-200 p-6">
            <h3 className="text-lg font-bold text-slate-900 mb-4 flex items-center gap-2">
              <Clock className="w-5 h-5 text-sky-500" />
              {selectedDay ? format(new Date(selectedDay + 'T00:00'), 'EEEE, MMM d') : 'Select a day'}
            </h3>
            {!selectedDay ? (
              <p className="text-sm text-slate-400 text-center py-8">Click on a date to see class details</p>
            ) : dayClasses.length === 0 ? (
              <p className="text-sm text-slate-400 text-center py-8">No classes on this day</p>
            ) : (
              <div className="space-y-3">
                {dayClasses.map(cls => (
                  <div key={cls.class_id} className={`rounded-2xl border-2 p-4 ${
                    cls.status === 'in_progress' ? 'border-emerald-300 bg-emerald-50' :
                    cls.cancelled_today ? 'border-red-200 bg-red-50' :
                    'border-slate-200 bg-slate-50'
                  }`} data-testid={`day-class-${cls.class_id}`}>
                    <div className="flex items-start justify-between mb-1">
                      <h4 className="font-bold text-slate-900 text-sm">{cls.title}</h4>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        cls.status === 'in_progress' ? 'bg-emerald-200 text-emerald-800' :
                        cls.cancelled_today ? 'bg-red-200 text-red-800' :
                        'bg-sky-200 text-sky-800'
                      }`}>
                        {cls.status === 'in_progress' ? 'LIVE' : cls.cancelled_today ? 'CANCELLED' : 'SCHEDULED'}
                      </span>
                    </div>
                    <p className="text-xs text-slate-600 flex items-center gap-1"><Clock className="w-3 h-3" /> {cls.start_time} - {cls.end_time}</p>
                    <p className="text-xs text-slate-600 flex items-center gap-1 mt-0.5"><Users className="w-3 h-3" /> {cls.enrolled_students?.length || 0} student(s)</p>
                    {cls.is_demo && <span className="inline-block mt-1 bg-violet-100 text-violet-700 px-2 py-0.5 rounded-full text-[10px] font-semibold">DEMO</span>}
                    {cls.cancelled_today && (
                      <div className="mt-2 bg-red-100 rounded-lg p-2 flex items-center gap-1.5 text-xs text-red-700 font-medium">
                        <AlertCircle className="w-3 h-3" /> Student cancelled this session
                      </div>
                    )}
                    {cls.rescheduled && (
                      <div className="mt-2 bg-sky-100 rounded-lg p-2 text-xs text-sky-700 font-medium">
                        Rescheduled to {cls.rescheduled_date} {cls.rescheduled_start_time}-{cls.rescheduled_end_time}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default TeacherCalendar;
