import { getApiError, API , apiFetch} from '../utils/api';
import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { ArrowLeft, Upload, Download, Trash2, FileText, Loader2, BookOpen, Filter } from 'lucide-react';


const LearningKit = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [kits, setKits] = useState([]);
  const [grades, setGrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [selectedGrade, setSelectedGrade] = useState('');
  const [uploadForm, setUploadForm] = useState({ title: '', grade: '', description: '' });
  const [file, setFile] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      const [userRes, gradesRes] = await Promise.all([
        apiFetch(`${API}/auth/me`, { credentials: 'include' }),
        apiFetch(`${API}/learning-kit/grades`, { credentials: 'include' })
      ]);
      if (!userRes.ok) { navigate('/login'); return; }
      const userData = await userRes.json();
      setUser(userData);
      if (gradesRes.ok) setGrades(await gradesRes.json());

      // Fetch kits
      const gradeParam = userData.role === 'student' && userData.grade ? `?grade=${userData.grade}` : (selectedGrade ? `?grade=${selectedGrade}` : '');
      const kitsRes = await apiFetch(`${API}/learning-kit${gradeParam}`, { credentials: 'include' });
      if (kitsRes.ok) setKits(await kitsRes.json());
    } catch { toast.error('Failed to load'); }
    finally { setLoading(false); }
  }, [navigate, selectedGrade]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file || !uploadForm.title || !uploadForm.grade) {
      toast.error('Title, grade, and file are required');
      return;
    }
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('title', uploadForm.title);
      formData.append('grade', uploadForm.grade);
      formData.append('description', uploadForm.description);
      formData.append('file', file);
      const res = await apiFetch(`${API}/admin/learning-kit/upload`, {
        method: 'POST', credentials: 'include', body: formData
      });
      if (!res.ok) throw new Error(await getApiError(res));
      toast.success('Learning kit uploaded!');
      setUploadForm({ title: '', grade: '', description: '' });
      setFile(null);
      fetchData();
    } catch (err) { toast.error(err.message); }
    finally { setUploading(false); }
  };

  const handleDelete = async (kitId) => {
    if (!window.confirm('Delete this kit?')) return;
    try {
      const res = await apiFetch(`${API}/admin/learning-kit/${kitId}`, { method: 'DELETE', credentials: 'include' });
      if (!res.ok) throw new Error(await getApiError(res));
      toast.success('Kit deleted');
      fetchData();
    } catch (err) { toast.error(err.message); }
  };

  const handleDownload = (kitId) => {
    window.open(`${API}/learning-kit/download/${kitId}`, '_blank');
  };

  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const backPath = user?.role === 'admin' ? '/admin-dashboard'
    : user?.role === 'teacher' ? '/teacher-dashboard'
    : '/student-dashboard';

  if (loading) return (
    <div className="min-h-screen bg-gradient-to-br from-sky-50 via-white to-amber-50 flex items-center justify-center">
      <Loader2 className="w-10 h-10 animate-spin text-sky-500" />
    </div>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-sky-50 via-white to-amber-50">
      <div className="sticky top-0 z-50 backdrop-blur-xl bg-white/80 border-b border-slate-200">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" onClick={() => navigate(backPath)} className="rounded-full" data-testid="back-btn">
              <ArrowLeft className="w-4 h-4" />
            </Button>
            <div>
              <h1 className="text-xl font-bold text-slate-900" style={{ fontFamily: 'Fredoka, sans-serif' }}>
                <BookOpen className="w-5 h-5 inline mr-2 text-sky-500" />Learning Kit
              </h1>
              <p className="text-xs text-slate-500">
                {user?.role === 'student' ? `Materials for Class ${user.grade || 'All'}` : 'Manage study materials by grade'}
              </p>
            </div>
          </div>
          {user?.role !== 'student' && (
            <div className="flex items-center gap-2">
              <select value={selectedGrade} onChange={e => setSelectedGrade(e.target.value)}
                className="rounded-xl border-2 border-slate-200 px-3 py-2 text-sm" data-testid="filter-grade">
                <option value="">All Grades</option>
                {['1','2','3','4','5','6','7','8','9','10','11','12','UG','PG','Other'].map(g => (
                  <option key={g} value={g}>{g === 'UG' || g === 'PG' || g === 'Other' ? g : `Class ${g}`}</option>
                ))}
              </select>
              <Button onClick={fetchData} variant="outline" className="rounded-xl" data-testid="apply-filter">
                <Filter className="w-4 h-4" />
              </Button>
            </div>
          )}
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Admin Upload */}
        {user?.role === 'admin' && (
          <div className="bg-white rounded-3xl border-2 border-slate-100 shadow-[0_8px_30px_rgb(0,0,0,0.04)] p-6">
            <h3 className="font-bold text-slate-900 mb-4 flex items-center gap-2">
              <Upload className="w-5 h-5 text-sky-500" /> Upload New Material
            </h3>
            <form onSubmit={handleUpload} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <Label className="text-sm">Title *</Label>
                  <Input value={uploadForm.title} onChange={e => setUploadForm({...uploadForm, title: e.target.value})}
                    className="rounded-xl" placeholder="e.g., Math Workbook" required data-testid="kit-title" />
                </div>
                <div>
                  <Label className="text-sm">Grade *</Label>
                  <select value={uploadForm.grade} onChange={e => setUploadForm({...uploadForm, grade: e.target.value})}
                    className="w-full rounded-xl border-2 border-slate-200 px-3 py-2 text-sm h-10" required data-testid="kit-grade">
                    <option value="">Select...</option>
                    {['1','2','3','4','5','6','7','8','9','10','11','12','UG','PG','Other'].map(g => (
                      <option key={g} value={g}>{g === 'UG' || g === 'PG' || g === 'Other' ? g : `Class ${g}`}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <Label className="text-sm">Description</Label>
                  <Input value={uploadForm.description} onChange={e => setUploadForm({...uploadForm, description: e.target.value})}
                    className="rounded-xl" placeholder="Brief description" data-testid="kit-description" />
                </div>
              </div>
              <div className="flex items-center gap-4">
                <Input type="file" onChange={e => setFile(e.target.files[0])}
                  accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.jpg,.png"
                  className="flex-1 rounded-xl" data-testid="kit-file" />
                <Button type="submit" disabled={uploading}
                  className="bg-sky-500 hover:bg-sky-600 text-white rounded-full px-8" data-testid="upload-kit-btn">
                  {uploading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Upload className="w-4 h-4 mr-2" />}
                  Upload
                </Button>
              </div>
            </form>
          </div>
        )}

        {/* Kit List */}
        {kits.length === 0 ? (
          <div className="bg-white rounded-3xl border-2 border-slate-100 p-12 text-center">
            <BookOpen className="w-16 h-16 text-slate-200 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-slate-600 mb-2">No Materials Available</h3>
            <p className="text-slate-400 text-sm">
              {user?.role === 'admin' ? 'Upload your first learning kit above.' : 'No materials are available for your grade yet.'}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {kits.map(kit => (
              <div key={kit.kit_id} className="bg-white rounded-2xl border-2 border-slate-100 overflow-hidden hover:-translate-y-1 transition-all duration-200 shadow-[0_4px_15px_rgb(0,0,0,0.04)]" data-testid={`kit-${kit.kit_id}`}>
                <div className="bg-gradient-to-r from-sky-500 to-violet-500 p-4">
                  <div className="flex items-center justify-between">
                    <FileText className="w-8 h-8 text-white/80" />
                    <span className="bg-white/20 text-white text-xs font-medium px-3 py-1 rounded-full">
                      Class {kit.grade}
                    </span>
                  </div>
                </div>
                <div className="p-5">
                  <h3 className="font-bold text-slate-900 mb-1 truncate">{kit.title}</h3>
                  {kit.description && <p className="text-xs text-slate-500 mb-2 truncate">{kit.description}</p>}
                  <div className="flex items-center gap-3 text-xs text-slate-400 mb-4">
                    <span>{kit.file_type?.toUpperCase()}</span>
                    <span>{formatSize(kit.file_size)}</span>
                  </div>
                  <div className="flex gap-2">
                    <Button onClick={() => handleDownload(kit.kit_id)} className="flex-1 bg-sky-500 hover:bg-sky-600 text-white rounded-full text-sm" data-testid={`download-${kit.kit_id}`}>
                      <Download className="w-4 h-4 mr-1" /> Download
                    </Button>
                    {user?.role === 'admin' && (
                      <Button onClick={() => handleDelete(kit.kit_id)} variant="outline" className="rounded-full border-red-200 text-red-500 text-sm" data-testid={`delete-${kit.kit_id}`}>
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default LearningKit;
