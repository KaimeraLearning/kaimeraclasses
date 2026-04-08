import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { ArrowLeft, ChevronLeft, ChevronRight, Calendar as CalendarIcon } from 'lucide-react';
import { format, addMonths, subMonths, startOfMonth, endOfMonth, eachDayOfInterval, isSameMonth, parseISO } from 'date-fns';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

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
      // Get teacher classes
      const response = await fetch(`${API}/admin/classes`, { credentials: 'include' });
      if (!response.ok) throw new Error('Failed to fetch');
      
      const allClasses = await response.json();
      const teacherClasses = allClasses.filter(c => c.teacher_id === teacherId);
      
      setClasses(teacherClasses);
      
      if (teacherClasses.length > 0) {
        setTeacher({ name: teacherClasses[0].teacher_name });
      }
      
      setLoading(false);
    } catch (error) {
      console.error(error);
      toast.error('Failed to load schedule');
      setLoading(false);
    }
  };

  const getClassesForDate = (date) => {
    const dateStr = format(date, 'yyyy-MM-dd');
    return classes.filter(cls => cls.date === dateStr);
  };

  const renderCalendar = () => {
    const monthStart = startOfMonth(currentMonth);
    const monthEnd = endOfMonth(currentMonth);
    const daysInMonth = eachDayOfInterval({ start: monthStart, end: monthEnd });

    // Get day of week for first day (0 = Sunday)
    const firstDayOfWeek = monthStart.getDay();
    
    // Add empty cells for days before month starts
    const leadingEmptyCells = Array(firstDayOfWeek).fill(null);

    return (
      <div className="grid grid-cols-7 gap-2">
        {/* Day headers */}
        {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
          <div key={day} className="text-center font-semibold text-slate-600 py-2">
            {day}
          </div>
        ))}

        {/* Empty cells */}
        {leadingEmptyCells.map((_, idx) => (
          <div key={`empty-${idx}`} className="aspect-square"></div>
        ))}

        {/* Calendar days */}
        {daysInMonth.map(date => {
          const dayClasses = getClassesForDate(date);
          const hasClasses = dayClasses.length > 0;

          return (
            <div
              key={date.toISOString()}
              className={`aspect-square rounded-xl border-2 p-2 ${
                hasClasses
                  ? 'bg-sky-100 border-sky-500 cursor-pointer hover:bg-sky-200'
                  : 'bg-white border-slate-200'
              }`}
              title={hasClasses ? `${dayClasses.length} class(es)` : ''}
            >
              <div className="text-sm font-semibold text-slate-900">
                {format(date, 'd')}
              </div>
              {hasClasses && (
                <div className="mt-1">
                  <div className="text-xs font-bold text-sky-700">
                    {dayClasses.length} class{dayClasses.length > 1 ? 'es' : ''}
                  </div>
                  {dayClasses.map(cls => (
                    <div key={cls.class_id} className="text-xs text-sky-600 truncate">
                      {cls.start_time}
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

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="w-16 h-16 border-4 border-sky-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-white/80 border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center gap-4">
            <Button onClick={() => navigate('/counsellor-dashboard')} variant="outline" className="rounded-full">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
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
          {/* Month Navigation */}
          <div className="flex items-center justify-between mb-8">
            <Button
              onClick={() => setCurrentMonth(subMonths(currentMonth, 1))}
              variant="outline"
              className="rounded-full"
            >
              <ChevronLeft className="w-5 h-5" />
            </Button>
            
            <div className="flex items-center gap-3">
              <CalendarIcon className="w-6 h-6 text-sky-500" />
              <h2 className="text-2xl font-bold text-slate-900">
                {format(currentMonth, 'MMMM yyyy')}
              </h2>
            </div>

            <Button
              onClick={() => setCurrentMonth(addMonths(currentMonth, 1))}
              variant="outline"
              className="rounded-full"
            >
              <ChevronRight className="w-5 h-5" />
            </Button>
          </div>

          {/* Calendar Grid */}
          {renderCalendar()}

          {/* Legend */}
          <div className="mt-8 flex items-center gap-6 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 bg-sky-100 border-2 border-sky-500 rounded"></div>
              <span className="text-slate-600">Classes Scheduled</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 bg-white border-2 border-slate-200 rounded"></div>
              <span className="text-slate-600">No Classes</span>
            </div>
          </div>

          {/* Total Classes */}
          <div className="mt-6 bg-slate-50 rounded-xl p-4">
            <p className="text-slate-600">
              Total classes scheduled: <span className="font-bold text-slate-900">{classes.length}</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TeacherSchedule;
