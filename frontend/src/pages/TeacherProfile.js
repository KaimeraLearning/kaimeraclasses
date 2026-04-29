import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { toast } from 'sonner';
import { ArrowLeft, User, Save, Upload, FileText, Lock, Star, Camera } from 'lucide-react';
import { getApiError, API , apiFetch} from '../utils/api';

export default function TeacherProfile() {
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [form, setForm] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showResumeViewer, setShowResumeViewer] = useState(false);

  useEffect(() => { fetchProfile(); }, []);

  const fetchProfile = async () => {
    try {
      const res = await apiFetch(`${API}/teacher/profile`, { credentials: 'include' });
      if (!res.ok) throw new Error(await getApiError(res));
      const data = await res.json();
      setProfile(data);
      setForm({
        bio: data.bio || '', age: data.age || '', date_of_birth: data.date_of_birth || '',
        address: data.address || '', education_qualification: data.education_qualification || '',
        interests_hobbies: data.interests_hobbies || '', teaching_experience: data.teaching_experience || '',
        bank_name: data.bank_name || '', bank_account_number: data.bank_account_number || '',
        bank_ifsc_code: data.bank_ifsc_code || '', profile_picture: data.profile_picture || '',
        klat_score: data.klat_score || ''
      });
    } catch (err) { toast.error(err.message); }
    setLoading(false);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await apiFetch(`${API}/teacher/update-full-profile`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form)
      });
      if (!res.ok) throw new Error(await getApiError(res));
      toast.success('Profile updated successfully!');
      fetchProfile();
    } catch (err) { toast.error(err.message); }
    setSaving(false);
  };

  const handleProfilePic = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) { toast.error('Image must be under 2MB'); return; }
    const reader = new FileReader();
    reader.onload = () => setForm(prev => ({ ...prev, profile_picture: reader.result }));
    reader.readAsDataURL(file);
  };

  const handleResume = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) { toast.error('Resume must be under 5MB'); return; }
    if (!file.name.endsWith('.pdf')) { toast.error('Only PDF files are allowed'); return; }
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const res = await apiFetch(`${API}/teacher/upload-resume`, {
          method: 'POST', credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ resume_base64: reader.result, resume_name: file.name })
        });
        if (!res.ok) throw new Error(await getApiError(res));
        toast.success('Resume uploaded!');
        fetchProfile();
      } catch (err) { toast.error(err.message); }
    };
    reader.readAsDataURL(file);
  };

  const bankLocked = !!profile?.bank_name;

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="w-12 h-12 border-4 border-sky-500 border-t-transparent rounded-full animate-spin"></div>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-white/80 border-b border-slate-200">
        <div className="max-w-3xl mx-auto px-4 py-4 flex items-center gap-3">
          <button onClick={() => navigate(-1)} className="p-2 rounded-full hover:bg-slate-100"><ArrowLeft className="w-5 h-5" /></button>
          <h1 className="text-xl font-bold text-slate-900">My Profile</h1>
        </div>
      </header>

      <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
        {/* Profile Picture + Basic Info */}
        <div className="bg-white rounded-3xl border-2 border-slate-100 p-6" data-testid="profile-header-card">
          <div className="flex items-start gap-6">
            <div className="relative group">
              <div className="w-28 h-28 rounded-full bg-gradient-to-br from-sky-100 to-violet-100 flex items-center justify-center overflow-hidden border-4 border-white shadow-lg">
                {form.profile_picture ? (
                  <img src={form.profile_picture} alt="Profile" className="w-full h-full object-cover" />
                ) : (
                  <User className="w-12 h-12 text-slate-400" />
                )}
              </div>
              <label className="absolute bottom-0 right-0 bg-sky-500 text-white rounded-full w-8 h-8 flex items-center justify-center cursor-pointer hover:bg-sky-600 shadow-md" data-testid="upload-profile-pic">
                <Camera className="w-4 h-4" />
                <input type="file" accept="image/*" className="hidden" onChange={handleProfilePic} />
              </label>
            </div>
            <div className="flex-1">
              <h2 className="text-2xl font-bold text-slate-900">{profile?.name}</h2>
              <p className="text-sm text-slate-500">{profile?.email}</p>
              <p className="text-xs text-slate-400 mt-1">Teacher Code: <span className="font-mono font-bold text-sky-600">{profile?.teacher_code || 'N/A'}</span></p>
              <div className="flex items-center gap-2 mt-2">
                <Star className="w-4 h-4 text-amber-500" />
                <span className="text-sm font-semibold text-slate-700">KLAT Score: <span className="text-amber-600">{profile?.klat_score || 'Not set'}</span></span>
              </div>
            </div>
          </div>
        </div>

        {/* Personal Info */}
        <div className="bg-white rounded-3xl border-2 border-slate-100 p-6 space-y-4" data-testid="personal-info-card">
          <h3 className="font-bold text-slate-900 text-lg">Personal Information</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2"><Label>KLAT Score</Label><Input value={form.klat_score} onChange={e => setForm({...form, klat_score: e.target.value})} placeholder="Enter your KLAT score" className="rounded-xl" data-testid="profile-klat-score" /></div>
            <div><Label>Bio</Label><textarea value={form.bio} onChange={e => setForm({...form, bio: e.target.value})} className="w-full rounded-xl border-2 border-slate-200 px-3 py-2 text-sm" rows={3} data-testid="profile-bio" /></div>
            <div><Label>Age</Label><Input type="number" value={form.age} onChange={e => setForm({...form, age: e.target.value})} className="rounded-xl" data-testid="profile-age" /></div>
            <div><Label>Date of Birth</Label><Input type="date" value={form.date_of_birth} onChange={e => setForm({...form, date_of_birth: e.target.value})} className="rounded-xl" data-testid="profile-dob" /></div>
            <div><Label>Address</Label><Input value={form.address} onChange={e => setForm({...form, address: e.target.value})} className="rounded-xl" data-testid="profile-address" /></div>
            <div><Label>Education Qualification</Label><Input value={form.education_qualification} onChange={e => setForm({...form, education_qualification: e.target.value})} className="rounded-xl" data-testid="profile-education" /></div>
            <div><Label>Interests & Hobbies</Label><Input value={form.interests_hobbies} onChange={e => setForm({...form, interests_hobbies: e.target.value})} className="rounded-xl" data-testid="profile-interests" /></div>
            <div className="sm:col-span-2"><Label>Teaching Experience</Label><textarea value={form.teaching_experience} onChange={e => setForm({...form, teaching_experience: e.target.value})} className="w-full rounded-xl border-2 border-slate-200 px-3 py-2 text-sm" rows={3} data-testid="profile-experience" /></div>
          </div>
        </div>

        {/* Bank Details */}
        <div className="bg-white rounded-3xl border-2 border-slate-100 p-6 space-y-4" data-testid="bank-details-card">
          <div className="flex items-center gap-2">
            <h3 className="font-bold text-slate-900 text-lg">Bank Details</h3>
            {bankLocked && <span className="bg-amber-100 text-amber-700 text-xs px-2 py-0.5 rounded-full flex items-center gap-1"><Lock className="w-3 h-3" /> Locked</span>}
          </div>
          {bankLocked && <p className="text-xs text-amber-600">Bank details are locked after first entry. Contact admin to update.</p>}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div><Label>Bank Name</Label><Input value={form.bank_name} onChange={e => setForm({...form, bank_name: e.target.value})} disabled={bankLocked} className="rounded-xl disabled:bg-slate-100" data-testid="bank-name" /></div>
            <div><Label>Account Number</Label><Input value={form.bank_account_number} onChange={e => setForm({...form, bank_account_number: e.target.value})} disabled={bankLocked} className="rounded-xl disabled:bg-slate-100" data-testid="bank-ac-no" /></div>
            <div><Label>IFSC Code</Label><Input value={form.bank_ifsc_code} onChange={e => setForm({...form, bank_ifsc_code: e.target.value})} disabled={bankLocked} className="rounded-xl disabled:bg-slate-100" data-testid="bank-ifsc" /></div>
          </div>
        </div>

        {/* Resume */}
        <div className="bg-white rounded-3xl border-2 border-slate-100 p-6 space-y-4" data-testid="resume-card">
          <h3 className="font-bold text-slate-900 text-lg">Resume</h3>
          <div className="flex items-center gap-4">
            {profile?.resume_name ? (
              <div className="flex items-center gap-3 bg-emerald-50 border border-emerald-200 rounded-xl px-4 py-3 flex-1">
                <FileText className="w-5 h-5 text-emerald-600" />
                <span className="text-sm font-medium text-emerald-800">{profile.resume_name}</span>
                <button onClick={() => setShowResumeViewer(true)} className="ml-auto text-xs text-sky-600 hover:underline" data-testid="view-resume">View</button>
              </div>
            ) : (
              <p className="text-sm text-slate-500">No resume uploaded yet</p>
            )}
            <label className="cursor-pointer" data-testid="upload-resume-btn">
              <div className="bg-sky-500 hover:bg-sky-600 text-white rounded-full px-4 py-2 text-sm font-medium flex items-center gap-2 transition-colors">
                <Upload className="w-4 h-4" /> Upload PDF
              </div>
              <input type="file" accept=".pdf" className="hidden" onChange={handleResume} />
            </label>
          </div>
        </div>

        {/* Save Button */}
        <Button onClick={handleSave} disabled={saving} className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-full py-6 font-bold text-lg" data-testid="save-profile-btn">
          <Save className="w-5 h-5 mr-2" /> {saving ? 'Saving...' : 'Save Profile'}
        </Button>
      </div>

      {/* Resume Viewer Dialog */}
      <Dialog open={showResumeViewer} onOpenChange={setShowResumeViewer}>
        <DialogContent className="sm:max-w-3xl h-[80vh] rounded-3xl">
          <DialogHeader><DialogTitle>Resume - {profile?.name}</DialogTitle></DialogHeader>
          {profile?.resume_base64 && (
            <iframe src={profile.resume_base64} className="w-full flex-1 min-h-[60vh] rounded-xl" title="Resume" />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
