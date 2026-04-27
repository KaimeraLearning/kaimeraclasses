import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { Camera, PhoneOff, ArrowLeft, Loader2, ExternalLink } from 'lucide-react';
import { getApiError, API } from '../utils/api';

const VideoClass = () => {
  const { classId } = useParams();
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [classInfo, setClassInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isTeacher, setIsTeacher] = useState(false);
  const [zoomOpened, setZoomOpened] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [userRes, statusRes] = await Promise.all([
        fetch(`${API}/auth/me`, { credentials: 'include' }),
        fetch(`${API}/classes/status/${classId}`, { credentials: 'include' })
      ]);
      if (!userRes.ok) throw new Error('Authentication failed. Please log in again.');
      if (!statusRes.ok) throw new Error('Class not found or you do not have access.');
      const userData = await userRes.json();
      const classData = await statusRes.json();
      setUser(userData);
      setClassInfo(classData);
      setIsTeacher(userData.role === 'teacher' && classData.teacher_id === userData.user_id);
      setLoading(false);
    } catch (error) {
      toast.error(error.message || 'Failed to load class data');
      setLoading(false);
    }
  }, [classId]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleStartClass = async () => {
    try {
      const res = await fetch(`${API}/classes/start/${classId}`, { method: 'POST', credentials: 'include' });
      if (!res.ok) throw new Error(await getApiError(res));
      const data = await res.json();
      toast.success('Class started! Zoom meeting created.');
      fetchData();
      // Auto-open Zoom
      if (data.zoom_join_url) {
        window.open(data.zoom_join_url, '_blank');
        setZoomOpened(true);
      }
    } catch (error) { toast.error(error.message); }
  };

  const handleEndClass = async () => {
    if (!window.confirm('End the class session?')) return;
    try {
      const res = await fetch(`${API}/classes/end/${classId}`, { method: 'POST', credentials: 'include' });
      if (!res.ok) throw new Error(await getApiError(res));
      const data = await res.json();
      toast.success(data.message);
      navigate('/teacher-dashboard');
    } catch (error) { toast.error(error.message); }
  };

  const handleTakeScreenshot = async () => {
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: { displaySurface: 'browser' },
        preferCurrentTab: true
      });
      const track = stream.getVideoTracks()[0];
      const imageCapture = new ImageCapture(track);
      const bitmap = await imageCapture.grabFrame();
      track.stop();
      const canvas = document.createElement('canvas');
      canvas.width = bitmap.width;
      canvas.height = bitmap.height;
      canvas.getContext('2d').drawImage(bitmap, 0, 0);
      canvas.toBlob((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `class-proof-${classId}-${Date.now()}.png`;
        a.click();
        URL.revokeObjectURL(url);
        toast.success('Screenshot captured!');
      }, 'image/png');
    } catch {
      toast.error('Screenshot failed. Please allow screen capture.');
    }
  };

  if (loading) return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center">
      <Loader2 className="w-16 h-16 animate-spin text-sky-400" />
    </div>
  );

  // Student: class not in progress
  if (!isTeacher && classInfo?.status !== 'in_progress') {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="bg-white/10 backdrop-blur-xl rounded-3xl p-12 border border-white/20 text-center text-white max-w-md">
          <Loader2 className="w-16 h-16 animate-spin mx-auto mb-6 text-sky-400" />
          <h2 className="text-2xl font-bold mb-3">{classInfo?.title}</h2>
          <p className="text-white/70 mb-2">by {classInfo?.teacher_name}</p>
          <p className="text-amber-400 font-semibold mb-6">Waiting for teacher to start...</p>
          <Button onClick={() => navigate('/student-dashboard')} variant="outline" className="rounded-full border-white/30 text-white hover:bg-white/10" data-testid="back-to-dashboard">
            <ArrowLeft className="w-4 h-4 mr-2" /> Back
          </Button>
        </div>
      </div>
    );
  }

  // Teacher: class not started
  if (isTeacher && classInfo?.status !== 'in_progress') {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="bg-white/10 backdrop-blur-xl rounded-3xl p-12 border border-white/20 text-center text-white max-w-md">
          <h2 className="text-2xl font-bold mb-3">{classInfo?.title}</h2>
          <p className="text-white/70 mb-6">Start the class to create a Zoom meeting</p>
          <Button onClick={handleStartClass} className="w-full bg-emerald-500 hover:bg-emerald-600 text-white rounded-full py-6 font-bold text-lg mb-4" data-testid="start-class-button">
            Start Class Now
          </Button>
          <Button onClick={() => navigate('/teacher-dashboard')} variant="outline" className="w-full rounded-full border-white/30 text-white hover:bg-white/10">
            <ArrowLeft className="w-4 h-4 mr-2" /> Back
          </Button>
        </div>
      </div>
    );
  }

  // Class in progress
  return (
    <div className="min-h-screen bg-slate-900 flex flex-col">
      <div className="flex items-center justify-between px-4 py-3 bg-slate-800 border-b border-slate-700">
        <div className="flex items-center gap-3">
          <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
          <span className="text-white font-semibold">{classInfo?.title}</span>
          <span className="text-slate-400 text-xs">LIVE</span>
        </div>
        <div className="flex items-center gap-2">
          {isTeacher && (
            <Button onClick={handleTakeScreenshot} className="bg-sky-600 hover:bg-sky-700 text-white rounded-full px-4 text-sm" data-testid="screenshot-button">
              <Camera className="w-4 h-4 mr-2" /> Screenshot
            </Button>
          )}
          {isTeacher && (
            <Button onClick={handleEndClass} className="bg-red-600 hover:bg-red-700 text-white rounded-full px-4 text-sm" data-testid="end-class-button">
              <PhoneOff className="w-4 h-4 mr-2" /> End Class
            </Button>
          )}
          {!isTeacher && (
            <Button onClick={() => navigate('/student-dashboard')} className="bg-red-600 hover:bg-red-700 text-white rounded-full px-4 text-sm" data-testid="leave-class-button">
              <PhoneOff className="w-4 h-4 mr-2" /> Leave
            </Button>
          )}
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center p-8">
        <div className="bg-white/10 backdrop-blur-xl rounded-3xl p-12 border border-white/20 text-center text-white max-w-lg w-full">
          <div className="w-20 h-20 bg-sky-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
            <ExternalLink className="w-10 h-10 text-sky-400" />
          </div>
          <h2 className="text-2xl font-bold mb-3">Zoom Meeting Active</h2>
          <p className="text-white/70 mb-6">Your class is running on Zoom. Click below to join or rejoin the meeting.</p>

          {classInfo?.zoom_join_url && (
            <Button onClick={() => { window.open(classInfo.zoom_join_url, '_blank'); setZoomOpened(true); }}
              className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-full py-6 font-bold text-lg mb-4" data-testid="join-zoom-btn">
              <ExternalLink className="w-5 h-5 mr-2" /> {zoomOpened ? 'Rejoin Zoom Meeting' : 'Join Zoom Meeting'}
            </Button>
          )}

          {zoomOpened && (
            <p className="text-emerald-400 text-sm font-semibold">Zoom opened in a new tab. Keep this page open to end the class when done.</p>
          )}

          {isTeacher && (
            <div className="mt-6 pt-4 border-t border-white/10">
              <p className="text-white/50 text-xs mb-2">Take a screenshot of the Zoom call for proof</p>
              <Button onClick={handleTakeScreenshot} variant="outline" className="rounded-full border-white/20 text-white hover:bg-white/10 text-sm">
                <Camera className="w-4 h-4 mr-2" /> Capture Screenshot
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default VideoClass;
