import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { User, Star, FileText, MapPin, GraduationCap, Briefcase, Heart, Calendar } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export function ViewProfilePopup({ open, onOpenChange, userId, userRole }) {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchProfile = async () => {
    if (!userId || !userRole) return;
    setLoading(true);
    try {
      const endpoint = userRole === 'teacher' ? 'teacher/view-profile' : 'counsellor/view-profile';
      const res = await fetch(`${API}/${endpoint}/${userId}`, { credentials: 'include' });
      if (res.ok) setProfile(await res.json());
    } catch {}
    setLoading(false);
  };

  const handleOpenChange = (isOpen) => {
    if (isOpen && userId) fetchProfile();
    if (!isOpen) setProfile(null);
    onOpenChange(isOpen);
  };

  const isTeacher = userRole === 'teacher';
  const accent = isTeacher ? 'sky' : 'violet';

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-lg rounded-3xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isTeacher ? 'Teacher' : 'Counselor'} Profile</DialogTitle>
        </DialogHeader>
        {loading && <div className="flex justify-center py-8"><div className={`w-8 h-8 border-4 border-${accent}-500 border-t-transparent rounded-full animate-spin`}></div></div>}
        {profile && (
          <div className="space-y-4" data-testid="profile-popup-content">
            {/* Header */}
            <div className={`bg-gradient-to-br ${isTeacher ? 'from-sky-400 to-sky-500' : 'from-violet-400 to-violet-500'} rounded-2xl p-5 text-white`}>
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center overflow-hidden shrink-0">
                  {profile.profile_picture ? (
                    <img src={profile.profile_picture} alt="" className="w-full h-full object-cover" />
                  ) : (
                    <User className="w-8 h-8" />
                  )}
                </div>
                <div className="min-w-0">
                  <h3 className="text-xl font-bold truncate">{profile.name}</h3>
                  <p className="text-white/80 text-sm">{profile.email}</p>
                  {profile.phone && <p className="text-white/70 text-xs mt-0.5">{profile.phone}</p>}
                  {isTeacher && profile.teacher_code && <p className="text-white/70 font-mono text-xs mt-0.5">ID: {profile.teacher_code}</p>}
                  {!isTeacher && <p className="text-white/70 font-mono text-xs mt-0.5">ID: {profile.counselor_id || profile.user_id?.slice(-8)?.toUpperCase()}</p>}
                </div>
              </div>
            </div>

            {/* Scores */}
            <div className="grid grid-cols-2 gap-3">
              {isTeacher && (
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 text-center">
                  <p className="text-[10px] text-amber-600 font-medium">KLAT Score</p>
                  <p className="text-lg font-bold text-amber-700">{profile.klat_score || 'N/A'}</p>
                </div>
              )}
              {!isTeacher && (
                <div className="bg-violet-50 border border-violet-200 rounded-xl p-3 text-center">
                  <p className="text-[10px] text-violet-600 font-medium">KL-CAT Score</p>
                  <p className="text-lg font-bold text-violet-700">{profile.klcat_score || 'N/A'}</p>
                </div>
              )}
              <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3 text-center">
                <p className="text-[10px] text-emerald-600 font-medium">Star Rating</p>
                <p className="text-lg font-bold text-emerald-700">{(profile.star_rating ?? 5).toFixed(1)}<span className="text-xs">/5</span></p>
              </div>
            </div>

            {/* Personal Details */}
            <div className="space-y-2">
              {profile.bio && (
                <div className="bg-slate-50 rounded-xl p-3">
                  <p className="text-[10px] text-slate-500 font-medium mb-1 flex items-center gap-1"><User className="w-3 h-3" /> Bio</p>
                  <p className="text-sm text-slate-800">{profile.bio}</p>
                </div>
              )}
              <div className="grid grid-cols-2 gap-2">
                {profile.age && (
                  <div className="bg-slate-50 rounded-xl p-3">
                    <p className="text-[10px] text-slate-500 font-medium mb-1">Age</p>
                    <p className="text-sm font-medium text-slate-800">{profile.age}</p>
                  </div>
                )}
                {profile.date_of_birth && (
                  <div className="bg-slate-50 rounded-xl p-3">
                    <p className="text-[10px] text-slate-500 font-medium mb-1 flex items-center gap-1"><Calendar className="w-3 h-3" /> Date of Birth</p>
                    <p className="text-sm font-medium text-slate-800">{profile.date_of_birth}</p>
                  </div>
                )}
                {profile.address && (
                  <div className="bg-slate-50 rounded-xl p-3">
                    <p className="text-[10px] text-slate-500 font-medium mb-1 flex items-center gap-1"><MapPin className="w-3 h-3" /> Address</p>
                    <p className="text-sm font-medium text-slate-800">{profile.address}</p>
                  </div>
                )}
                {profile.education_qualification && (
                  <div className="bg-slate-50 rounded-xl p-3">
                    <p className="text-[10px] text-slate-500 font-medium mb-1 flex items-center gap-1"><GraduationCap className="w-3 h-3" /> Education</p>
                    <p className="text-sm font-medium text-slate-800">{profile.education_qualification}</p>
                  </div>
                )}
                {profile.interests_hobbies && (
                  <div className="bg-slate-50 rounded-xl p-3">
                    <p className="text-[10px] text-slate-500 font-medium mb-1 flex items-center gap-1"><Heart className="w-3 h-3" /> Interests & Hobbies</p>
                    <p className="text-sm font-medium text-slate-800">{profile.interests_hobbies}</p>
                  </div>
                )}
              </div>
              {(profile.teaching_experience || profile.experience) && (
                <div className="bg-slate-50 rounded-xl p-3">
                  <p className="text-[10px] text-slate-500 font-medium mb-1 flex items-center gap-1"><Briefcase className="w-3 h-3" /> {isTeacher ? 'Teaching Experience' : 'Experience'}</p>
                  <p className="text-sm text-slate-800">{profile.teaching_experience || profile.experience}</p>
                </div>
              )}
            </div>

            {/* Resume */}
            {profile.resume_name && (
              <div className="bg-sky-50 border border-sky-200 rounded-xl p-3 flex items-center gap-2">
                <FileText className="w-4 h-4 text-sky-600 shrink-0" />
                <span className="text-sm font-medium text-sky-800 truncate">{profile.resume_name}</span>
                {profile.resume_base64 && <a href={profile.resume_base64} target="_blank" rel="noreferrer" className="ml-auto text-xs text-sky-600 hover:underline shrink-0">View Resume</a>}
              </div>
            )}

            {/* Badges */}
            {profile.badges?.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {profile.badges.map((b, i) => (
                  <span key={i} className="bg-violet-100 text-violet-700 px-3 py-1 rounded-full text-xs font-medium">{b}</span>
                ))}
              </div>
            )}

            {/* Empty state */}
            {!profile.bio && !profile.age && !profile.education_qualification && !profile.address && !profile.interests_hobbies && !profile.teaching_experience && !profile.experience && (
              <div className="text-center py-4 text-slate-400 text-sm">No detailed profile information added yet</div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
