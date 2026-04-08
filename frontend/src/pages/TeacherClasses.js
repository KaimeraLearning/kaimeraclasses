import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { ArrowLeft, Calendar, Clock, Users, Trash2 } from 'lucide-react';
import { format, parseISO } from 'date-fns';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const TeacherClasses = () => {
  const navigate = useNavigate();
  const [classes, setClasses] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchClasses();
  }, []);

  const fetchClasses = async () => {
    try {
      const response = await fetch(`${API}/teacher/dashboard`, { credentials: 'include' });
      if (!response.ok) throw new Error('Failed to fetch');
      
      const data = await response.json();
      setClasses(data.classes || []);
      setLoading(false);
    } catch (error) {
      console.error(error);
      toast.error('Failed to load classes');
      setLoading(false);
    }
  };

  const handleDeleteClass = async (classId) => {
    if (!window.confirm('Are you sure you want to delete this class?')) return;

    try {
      const response = await fetch(`${API}/classes/delete/${classId}`, {
        method: 'DELETE',
        credentials: 'include'
      });

      if (!response.ok) throw new Error('Failed to delete');

      toast.success('Class deleted successfully');
      fetchClasses();
    } catch (error) {
      toast.error(error.message);
    }
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
            <Button onClick={() => navigate('/teacher-dashboard')} variant="outline" className="rounded-full">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
            </Button>
            <h1 className="text-2xl font-bold text-slate-900">All Classes</h1>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {classes.length === 0 ? (
          <div className="bg-white rounded-3xl p-12 border-2 border-slate-100 text-center">
            <p className="text-slate-600">No classes created yet</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {classes.map((cls) => (
              <div
                key={cls.class_id}
                className="bg-white rounded-3xl border-2 border-slate-200 shadow-[4px_4px_0px_0px_rgba(226,232,240,1)] p-6"
              >
                <div className="flex items-start justify-between mb-3">
                  <span className="bg-amber-100 text-amber-800 px-3 py-1 rounded-full text-xs font-semibold">
                    {cls.subject}
                  </span>
                  <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                    cls.status === 'scheduled' ? 'bg-emerald-100 text-emerald-800' : 
                    cls.status === 'in_progress' ? 'bg-sky-100 text-sky-800' : 
                    'bg-slate-100 text-slate-800'
                  }`}>
                    {cls.status}
                  </span>
                </div>

                <h3 className="text-xl font-bold text-slate-900 mb-4">{cls.title}</h3>

                <div className="space-y-2 mb-4">
                  <div className="flex items-center gap-2 text-slate-600">
                    <Calendar className="w-4 h-4" />
                    <span className="text-sm">{format(parseISO(cls.date), 'MMM dd, yyyy')}</span>
                  </div>
                  {cls.end_date && (
                    <div className="flex items-center gap-2 text-slate-600">
                      <Calendar className="w-4 h-4" />
                      <span className="text-sm">Ends: {format(parseISO(cls.end_date), 'MMM dd, yyyy')}</span>
                    </div>
                  )}
                  <div className="flex items-center gap-2 text-slate-600">
                    <Clock className="w-4 h-4" />
                    <span className="text-sm">{cls.start_time} - {cls.end_time}</span>
                  </div>
                  <div className="flex items-center gap-2 text-slate-600">
                    <Users className="w-4 h-4" />
                    <span className="text-sm">{cls.enrolled_students.length} / {cls.max_students} students</span>
                  </div>
                </div>

                {cls.status === 'scheduled' && (
                  <div className="space-y-2">
                    <Button
                      onClick={() => navigate(`/class/${cls.class_id}`)}
                      className="w-full bg-emerald-500 hover:bg-emerald-600 text-white rounded-full font-bold"
                    >
                      Start Class
                    </Button>
                    <Button
                      onClick={() => handleDeleteClass(cls.class_id)}
                      variant="outline"
                      className="w-full border-2 border-red-200 hover:bg-red-50 text-red-600 rounded-full font-bold"
                    >
                      <Trash2 className="w-4 h-4 mr-2" />
                      Delete Class
                    </Button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default TeacherClasses;
