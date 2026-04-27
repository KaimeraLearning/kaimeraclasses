import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { Camera, PhoneOff, ArrowLeft, Loader2 } from 'lucide-react';
import { getApiError, API } from '../utils/api';

const JITSI_SCRIPT_SRC = 'https://meet.jit.si/external_api.js';

const loadJitsiScript = () => new Promise((resolve, reject) => {
  if (window.JitsiMeetExternalAPI) return resolve();
  const existing = document.querySelector(`script[src="${JITSI_SCRIPT_SRC}"]`);
  if (existing) {
    existing.addEventListener('load', () => resolve());
    existing.addEventListener('error', () => reject(new Error('Jitsi script load failed')));
    return;
  }
  const s = document.createElement('script');
  s.src = JITSI_SCRIPT_SRC;
  s.async = true;
  s.onload = () => resolve();
  s.onerror = () => reject(new Error('Jitsi script load failed'));
  document.head.appendChild(s);
});

const VideoClass = () => {
  const { classId } = useParams();
  const navigate = useNavigate();
  const containerRef = useRef(null);
  const apiRef = useRef(null);
  const [user, setUser] = useState(null);
  const [classInfo, setClassInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isTeacher, setIsTeacher] = useState(false);
  const [jitsiReady, setJitsiReady] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [userRes, statusRes] = await Promise.all([
        fetch(`${API}/auth/me`, { credentials: 'include' }),
        fetch(`${API}/classes/status/${classId}`, { credentials: 'include' })
      ]);
      if (!userRes.ok) throw new Error('Authentication failed. Please log in again.');
      if (!statusRes.ok) throw new Error(await getApiError(statusRes));
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

  // Embed Jitsi iframe once class is in_progress and we have a room name
  useEffect(() => {
    if (!classInfo || loading) return;
    if (classInfo.status !== 'in_progress' || !classInfo.jitsi_room) return;
    if (apiRef.current) return;

    const start = async () => {
      try {
        await loadJitsiScript();
        if (!containerRef.current) return;

        const domain = classInfo.jitsi_domain || 'meet.jit.si';
        const isMod = !!classInfo.is_moderator;
        const options = {
          roomName: classInfo.jitsi_room,
          parentNode: containerRef.current,
          width: '100%',
          height: '100%',
          userInfo: {
            displayName: user?.name || (isMod ? 'Teacher' : 'Student'),
            email: user?.email || ''
          },
          configOverwrite: {
            prejoinPageEnabled: false,
            disableDeepLinking: true,
            startWithAudioMuted: !isMod,
            startWithVideoMuted: false,
            enableWelcomePage: false,
            enableClosePage: false,
            disableInviteFunctions: true,
            readOnlyName: true,
            requireDisplayName: false
          },
          interfaceConfigOverwrite: {
            MOBILE_APP_PROMO: false,
            SHOW_JITSI_WATERMARK: false,
            SHOW_BRAND_WATERMARK: false,
            DEFAULT_REMOTE_DISPLAY_NAME: 'Participant',
            TOOLBAR_BUTTONS: isMod
              ? ['microphone', 'camera', 'desktop', 'fullscreen', 'fodeviceselection', 'hangup', 'chat', 'raisehand', 'videoquality', 'tileview', 'mute-everyone', 'security']
              : ['microphone', 'camera', 'fullscreen', 'fodeviceselection', 'hangup', 'chat', 'raisehand', 'videoquality', 'tileview']
          }
        };

        const api = new window.JitsiMeetExternalAPI(domain, options);
        apiRef.current = api;
        setJitsiReady(true);

        api.addListener('videoConferenceJoined', () => {
          if (isMod) {
            // Lock the room with a per-class password derived from class_id (informational; not crypto)
            // Free meet.jit.si moderator can also enable lobby manually; here we just rely on app-level gating.
            toast.success('Class connected — you are the host.');
          } else {
            toast.success('Joined class.');
          }
        });
        api.addListener('readyToClose', () => {
          handleLeave();
        });
      } catch (err) {
        console.error('Jitsi init error:', err);
        toast.error('Failed to load video. Please refresh the page.');
      }
    };

    start();

    return () => {
      try { apiRef.current && apiRef.current.dispose(); } catch {}
      apiRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [classInfo, loading, user]);

  const handleStartClass = async () => {
    try {
      const res = await fetch(`${API}/classes/start/${classId}`, { method: 'POST', credentials: 'include' });
      if (!res.ok) throw new Error(await getApiError(res));
      toast.success('Class started!');
      fetchData();
    } catch (error) { toast.error(error.message); }
  };

  const handleEndClass = async () => {
    if (!window.confirm('End the class session?')) return;
    try {
      const res = await fetch(`${API}/classes/end/${classId}`, { method: 'POST', credentials: 'include' });
      if (!res.ok) throw new Error(await getApiError(res));
      try { apiRef.current && apiRef.current.dispose(); } catch {}
      apiRef.current = null;
      toast.success('Class ended');
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

  const handleLeave = () => {
    try { apiRef.current && apiRef.current.dispose(); } catch {}
    apiRef.current = null;
    navigate(isTeacher ? '/teacher-dashboard' : '/student-dashboard');
  };

  if (loading) return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center">
      <Loader2 className="w-16 h-16 animate-spin text-sky-400" />
    </div>
  );

  // Student: waiting for teacher
  if (!isTeacher && classInfo?.status !== 'in_progress') {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="bg-white/10 backdrop-blur-xl rounded-3xl p-12 border border-white/20 text-center text-white max-w-md">
          <Loader2 className="w-16 h-16 animate-spin mx-auto mb-6 text-sky-400" />
          <h2 className="text-2xl font-bold mb-3">{classInfo?.title}</h2>
          <p className="text-white/70 mb-2">by {classInfo?.teacher_name}</p>
          <p className="text-amber-400 font-semibold mb-6">Waiting for teacher to start...</p>
          <Button onClick={() => navigate('/student-dashboard')} variant="outline" className="rounded-full border-white/30 text-white hover:bg-white/10">
            <ArrowLeft className="w-4 h-4 mr-2" /> Back
          </Button>
        </div>
      </div>
    );
  }

  // Teacher: start class
  if (isTeacher && classInfo?.status !== 'in_progress') {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="bg-white/10 backdrop-blur-xl rounded-3xl p-12 border border-white/20 text-center text-white max-w-md">
          <h2 className="text-2xl font-bold mb-3">{classInfo?.title}</h2>
          <p className="text-white/70 mb-6">Start the class to open the live video room</p>
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

  // Class in progress — embedded Jitsi iframe (filling container)
  return (
    <div className="h-screen bg-slate-900 flex flex-col">
      {/* Top bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-slate-800 border-b border-slate-700 z-10">
        <div className="flex items-center gap-3">
          <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
          <span className="text-white font-semibold text-sm">{classInfo?.title}</span>
          <span className="text-slate-400 text-xs">LIVE</span>
        </div>
        <div className="flex items-center gap-2">
          {isTeacher && (
            <Button onClick={handleTakeScreenshot} className="bg-sky-600 hover:bg-sky-700 text-white rounded-full px-4 text-sm" data-testid="screenshot-button">
              <Camera className="w-4 h-4 mr-2" /> Screenshot
            </Button>
          )}
          {isTeacher ? (
            <Button onClick={handleEndClass} className="bg-red-600 hover:bg-red-700 text-white rounded-full px-4 text-sm" data-testid="end-class-button">
              <PhoneOff className="w-4 h-4 mr-2" /> End Class
            </Button>
          ) : (
            <Button onClick={handleLeave} className="bg-red-600 hover:bg-red-700 text-white rounded-full px-4 text-sm" data-testid="leave-class-button">
              <PhoneOff className="w-4 h-4 mr-2" /> Leave
            </Button>
          )}
        </div>
      </div>

      {/* Jitsi iframe container — fills the rest of the viewport */}
      <div ref={containerRef} className="flex-1 relative bg-black" id="jitsi-container" data-testid="jitsi-container">
        {!jitsiReady && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center text-white">
              <Loader2 className="w-12 h-12 animate-spin mx-auto mb-4 text-sky-400" />
              <p>Connecting to video...</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default VideoClass;
