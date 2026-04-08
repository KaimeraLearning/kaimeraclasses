import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { ArrowLeft, Plus, Trash2, CalendarDays, ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const COLORS = ['#0ea5e9', '#8b5cf6', '#f59e0b', '#10b981', '#ef4444', '#ec4899', '#06b6d4'];

const TeacherCalendar = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [entries, setEntries] = useState([]);
  const [currentDate, setCurrentDate] = useState(new Date());
  const [showAddForm, setShowAddForm] = useState(false);
  const [selectedDate, setSelectedDate] = useState('');
  const [form, setForm] = useState({ title: '', description: '', subject: '', color: '#0ea5e9' });

  const yearMonth = `${currentDate.getFullYear()}-${String(currentDate.getMonth() + 1).padStart(2, '0')}`;

  const fetchEntries = useCallback(async () => {
    try {
      const res = await fetch(`${API}/teacher/calendar?month=${yearMonth}`, { credentials: 'include' });
      if (!res.ok && res.status === 401) { navigate('/login'); return; }
      if (res.ok) setEntries(await res.json());
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }, [navigate, yearMonth]);

  useEffect(() => { fetchEntries(); }, [fetchEntries]);

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!selectedDate || !form.title) { toast.error('Date and title required'); return; }
    try {
      const res = await fetch(`${API}/teacher/calendar`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date: selectedDate, ...form })
      });
      if (!res.ok) throw new Error((await res.json()).detail);
      toast.success('Entry added');
      setShowAddForm(false);
      setForm({ title: '', description: '', subject: '', color: '#0ea5e9' });
      fetchEntries();
    } catch (err) { toast.error(err.message); }
  };

  const handleDelete = async (entryId) => {
    try {
      const res = await fetch(`${API}/teacher/calendar/${entryId}`, { method: 'DELETE', credentials: 'include' });
      if (!res.ok) throw new Error((await res.json()).detail);
      toast.success('Entry removed');
      fetchEntries();
    } catch (err) { toast.error(err.message); }
  };

  const prevMonth = () => setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1));
  const nextMonth = () => setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1));

  // Calendar rendering
  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();
  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const monthName = currentDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

  const calendarDays = [];
  for (let i = 0; i < firstDay; i++) calendarDays.push(null);
  for (let d = 1; d <= daysInMonth; d++) calendarDays.push(d);

  const getEntriesForDay = (day) => {
    const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    return entries.filter(e => e.date === dateStr);
  };

  const todayStr = new Date().toISOString().split('T')[0];

  if (loading) return (
    <div className="min-h-screen bg-gradient-to-br from-sky-50 via-white to-amber-50 flex items-center justify-center">
      <Loader2 className="w-10 h-10 animate-spin text-sky-500" />
    </div>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-sky-50 via-white to-amber-50">
      <div className="sticky top-0 z-50 backdrop-blur-xl bg-white/80 border-b border-slate-200">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" onClick={() => navigate('/teacher-dashboard')} className="rounded-full" data-testid="back-btn">
              <ArrowLeft className="w-4 h-4" />
            </Button>
            <div>
              <h1 className="text-xl font-bold text-slate-900" style={{ fontFamily: 'Fredoka, sans-serif' }}>
                <CalendarDays className="w-5 h-5 inline mr-2 text-sky-500" />Content Planner
              </h1>
              <p className="text-xs text-slate-500">Plan your teaching content ahead</p>
            </div>
          </div>
          <Button onClick={() => { setShowAddForm(true); setSelectedDate(todayStr); }}
            className="bg-sky-500 hover:bg-sky-600 text-white rounded-full" data-testid="add-entry-btn">
            <Plus className="w-4 h-4 mr-1" /> Add Plan
          </Button>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Month navigation */}
        <div className="flex items-center justify-between mb-6">
          <Button variant="ghost" onClick={prevMonth} className="rounded-full" data-testid="prev-month">
            <ChevronLeft className="w-5 h-5" />
          </Button>
          <h2 className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'Fredoka, sans-serif' }}>{monthName}</h2>
          <Button variant="ghost" onClick={nextMonth} className="rounded-full" data-testid="next-month">
            <ChevronRight className="w-5 h-5" />
          </Button>
        </div>

        {/* Calendar grid */}
        <div className="bg-white rounded-3xl border-2 border-slate-100 shadow-[0_8px_30px_rgb(0,0,0,0.04)] overflow-hidden">
          {/* Day headers */}
          <div className="grid grid-cols-7 bg-slate-50 border-b border-slate-200">
            {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(d => (
              <div key={d} className="py-3 text-center text-xs font-semibold text-slate-500">{d}</div>
            ))}
          </div>
          {/* Days */}
          <div className="grid grid-cols-7">
            {calendarDays.map((day, i) => {
              if (!day) return <div key={`empty-${i}`} className="min-h-[100px] border-b border-r border-slate-100 bg-slate-50/50" />;
              const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
              const dayEntries = getEntriesForDay(day);
              const isToday = dateStr === todayStr;
              return (
                <div key={day} className={`min-h-[100px] border-b border-r border-slate-100 p-1.5 cursor-pointer hover:bg-sky-50/50 transition-colors ${isToday ? 'bg-sky-50' : ''}`}
                  onClick={() => { setSelectedDate(dateStr); setShowAddForm(true); }}
                  data-testid={`day-${dateStr}`}>
                  <span className={`inline-flex items-center justify-center w-7 h-7 text-sm font-medium rounded-full mb-1 ${isToday ? 'bg-sky-500 text-white' : 'text-slate-700'}`}>
                    {day}
                  </span>
                  <div className="space-y-1">
                    {dayEntries.map(entry => (
                      <div key={entry.entry_id} className="group flex items-center justify-between rounded-lg px-2 py-1 text-xs text-white"
                        style={{ backgroundColor: entry.color || '#0ea5e9' }}>
                        <span className="truncate font-medium">{entry.title}</span>
                        <button onClick={e => { e.stopPropagation(); handleDelete(entry.entry_id); }}
                          className="opacity-0 group-hover:opacity-100 ml-1 flex-shrink-0" data-testid={`del-${entry.entry_id}`}>
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Add form dialog */}
        {showAddForm && (
          <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={() => setShowAddForm(false)}>
            <div className="bg-white rounded-3xl p-6 w-full max-w-md shadow-xl" onClick={e => e.stopPropagation()} data-testid="add-form">
              <h3 className="text-lg font-bold text-slate-900 mb-4">Plan Content for {selectedDate}</h3>
              <form onSubmit={handleAdd} className="space-y-4">
                <div>
                  <Label>Title *</Label>
                  <Input value={form.title} onChange={e => setForm({...form, title: e.target.value})}
                    className="rounded-xl" placeholder="e.g., Algebra Chapter 3" required data-testid="entry-title" />
                </div>
                <div>
                  <Label>Subject</Label>
                  <Input value={form.subject} onChange={e => setForm({...form, subject: e.target.value})}
                    className="rounded-xl" placeholder="e.g., Mathematics" data-testid="entry-subject" />
                </div>
                <div>
                  <Label>Description</Label>
                  <textarea value={form.description} onChange={e => setForm({...form, description: e.target.value})}
                    className="w-full bg-slate-50 border-2 border-slate-200 rounded-xl px-4 py-3 text-sm resize-none h-20 focus:outline-none focus:ring-4 focus:ring-sky-500/20 focus:border-sky-500"
                    placeholder="Notes about the content..." data-testid="entry-desc" />
                </div>
                <div>
                  <Label>Color</Label>
                  <div className="flex gap-2 mt-1">
                    {COLORS.map(c => (
                      <button key={c} type="button" onClick={() => setForm({...form, color: c})}
                        className={`w-8 h-8 rounded-full border-2 transition-all ${form.color === c ? 'border-slate-900 scale-110' : 'border-transparent'}`}
                        style={{ backgroundColor: c }} />
                    ))}
                  </div>
                </div>
                <div className="flex gap-3">
                  <Button type="submit" className="flex-1 bg-sky-500 hover:bg-sky-600 text-white rounded-full" data-testid="save-entry">
                    Save
                  </Button>
                  <Button type="button" variant="outline" onClick={() => setShowAddForm(false)} className="rounded-full">
                    Cancel
                  </Button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default TeacherCalendar;
