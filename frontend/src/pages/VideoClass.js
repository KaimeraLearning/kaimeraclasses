import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { Camera, PhoneOff, ArrowLeft, Loader2 } from 'lucide-react';
import { getApiError } from '../utils/api';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const VideoClass = () => {
  const { classId } = useParams();
  const navigate = useNavigate();
  const jitsiContainerRef = useRef(null);
  const jitsiApiRef = useRef(null);
  const [user, setUser] = useState(null);
  const [classInfo, setClassInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [jitsiLoaded, setJitsiLoaded] = useState(false);
  const [isTeacher, setIsTeacher] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [userRes, statusRes] = await Promise.all([
        fetch(`${API}/auth/me`, { credentials: 'include' }),
        fetch(`${API}/classes/status/${classId}`, { credentials: 'include' })
      ]);
      if (!userRes.ok || !statusRes.ok) throw new Error('Failed to load');
      const userData = await userRes.json();
      const classData = await statusRes.json();
      setUser(userData);
      setClassInfo(classData);
      setIsTeacher(userData.role === 'teacher' && classData.teacher_id === userData.user_id);
      setLoading(false);
    } catch (error) {
      toast.error('Failed to load class data');
      setLoading(false);
    }
  }, [classId]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Load Jitsi Meet script
  useEffect(() => {
    if (!classInfo || loading) return;
    const script = document.createElement('script');
    script.src = 'https://meet.jit.si/external_api.js';
    script.async = true;
    script.onload = () => setJitsiLoaded(true);
    script.onerror = () => toast.error('Failed to load video system');
    document.body.appendChild(script);
    return () => { document.body.removeChild(script); };
  }, [classInfo, loading]);

  // Initialize Jitsi when loaded
  useEffect(() => {
    if (!jitsiLoaded || !user || !classInfo || !jitsiContainerRef.current) return;
    if (jitsiApiRef.current) return; // Already initialized

    const roomName = `kaimera-${classId}`;
    try {
      const api = new window.JitsiMeetExternalAPI('meet.jit.si', {
        roomName: roomName,
        parentNode: jitsiContainerRef.current,
        width: '100%',
        height: '100%',
        configOverwrite: {
          startWithAudioMuted: false,
          startWithVideoMuted: false,
          prejoinPageEnabled: false,
          disableDeepLinking: true,
          toolbarButtons: [
            'camera', 'chat', 'desktop', 'fullscreen',
            'hangup', 'microphone', 'participants-pane',
            'raisehand', 'tileview', 'toggle-camera'
          ]
        },
        interfaceConfigOverwrite: {
          SHOW_JITSI_WATERMARK: false,
          SHOW_WATERMARK_FOR_GUESTS: false,
          DEFAULT_BACKGROUND: '#0f172a',
          TOOLBAR_ALWAYS_VISIBLE: true
        },
        userInfo: {
          displayName: user.name,
          email: user.email
        }
      });

      api.addListener('readyToClose', () => {
        handleLeave();
      });

      jitsiApiRef.current = api;
    } catch (error) {
      console.error('Jitsi init error:', error);
      toast.error('Failed to start video');
    }

    return () => {
      if (jitsiApiRef.current) {
        jitsiApiRef.current.dispose();
        jitsiApiRef.current = null;
      }
    };
  }, [jitsiLoaded, user, classInfo, classId]);

  const handleStartClass = async () => {
    try {
      const res = await fetch(`${API}/classes/start/${classId}`, { method: 'POST', credentials: 'include' });
      if (!res.ok) throw new Error(await getApiError(res));
      toast.success('Class started! Students can now join.');
      fetchData();
    } catch (error) { toast.error(error.message); }
  };

  const handleEndClass = async () => {
    if (!window.confirm('End the class session? Students will be disconnected.')) return;
    try {
      const res = await fetch(`${API}/classes/end/${classId}`, { method: 'POST', credentials: 'include' });
      if (!res.ok) throw new Error(await getApiError(res));
      const data = await res.json();
      if (jitsiApiRef.current) { jitsiApiRef.current.dispose(); jitsiApiRef.current = null; }
      toast.success(data.message);
      navigate('/teacher-dashboard');
    } catch (error) { toast.error(error.message); }
  };

  const handleTakeScreenshot = async () => {
    // Primary: Use Jitsi's native API (avoids CORS on iframe)
    if (jitsiApiRef.current) {
      try {
        const data = await jitsiApiRef.current.captureLargeVideoScreenshot();
        if (data && data.dataURL) {
          const a = document.createElement('a');
          a.href = data.dataURL;
          a.download = `class-screenshot-${classId}-${Date.now()}.png`;
          a.click();
          toast.success('Screenshot captured and saved!');
          return;
        }
      } catch (err) {
        console.warn('Jitsi screenshot failed, trying fallback:', err);
      }
    }

    // Fallback: Screen Capture API (user picks screen/tab)
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({ video: { displaySurface: 'browser' } });
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
        a.download = `class-screenshot-${classId}-${Date.now()}.png`;
        a.click();
        URL.revokeObjectURL(url);
        toast.success('Screenshot saved!');
      }, 'image/png');
    } catch (fallbackError) {
      toast.error('Screenshot failed. Ensure video is unmuted or use your device\'s screenshot feature.');
    }
  };

  const handleLeave = () => {
    if (jitsiApiRef.current) { jitsiApiRef.current.dispose(); jitsiApiRef.current = null; }
    navigate(isTeacher ? '/teacher-dashboard' : '/student-dashboard');
  };

  if (loading) return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center">
      <div className="text-center text-white">
        <Loader2 className="w-16 h-16 animate-spin mx-auto mb-4 text-sky-400" />
        <p className="text-lg">Loading class...</p>
      </div>
    </div>
  );

  // If student and class not in progress, show waiting screen
  if (!isTeacher && classInfo?.status !== 'in_progress') {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-center text-white max-w-md">
          <div className="bg-white/10 backdrop-blur-xl rounded-3xl p-12 border border-white/20">
            <Loader2 className="w-16 h-16 animate-spin mx-auto mb-6 text-sky-400" />
            <h2 className="text-2xl font-bold mb-3">{classInfo?.title}</h2>
            <p className="text-white/70 mb-2">by {classInfo?.teacher_name}</p>
            <p className="text-amber-400 font-semibold mb-6">Waiting for teacher to start the class...</p>
            <Button onClick={() => navigate('/student-dashboard')} variant="outline" className="rounded-full border-white/30 text-white hover:bg-white/10" data-testid="back-to-dashboard">
              <ArrowLeft className="w-4 h-4 mr-2" /> Back to Dashboard
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // Teacher hasn't started yet - show start button
  if (isTeacher && classInfo?.status !== 'in_progress') {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-center text-white max-w-md">
          <div className="bg-white/10 backdrop-blur-xl rounded-3xl p-12 border border-white/20">
            <h2 className="text-2xl font-bold mb-3">{classInfo?.title}</h2>
            <p className="text-white/70 mb-6">Click below to start the class and open the video room</p>
            <Button onClick={handleStartClass} className="w-full bg-emerald-500 hover:bg-emerald-600 text-white rounded-full py-6 font-bold text-lg mb-4" data-testid="start-class-button">
              Start Class Now
            </Button>
            <Button onClick={() => navigate('/teacher-dashboard')} variant="outline" className="w-full rounded-full border-white/30 text-white hover:bg-white/10" data-testid="back-to-dashboard">
              <ArrowLeft className="w-4 h-4 mr-2" /> Back to Dashboard
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // Class is in progress - show Jitsi
  return (
    <div className="h-screen bg-slate-900 flex flex-col">
      {/* Top bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-slate-800/80 border-b border-slate-700 z-10">
        <div className="flex items-center gap-3">
          <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
          <span className="text-white font-semibold text-sm">{classInfo?.title}</span>
          <span className="text-slate-400 text-xs">LIVE</span>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={handleTakeScreenshot} className="bg-sky-600 hover:bg-sky-700 text-white rounded-full px-4 py-2 text-sm" data-testid="screenshot-button">
            <Camera className="w-4 h-4 mr-2" /> Screenshot
          </Button>
          {isTeacher && (
            <Button onClick={handleEndClass} className="bg-red-600 hover:bg-red-700 text-white rounded-full px-4 py-2 text-sm" data-testid="end-class-button">
              <PhoneOff className="w-4 h-4 mr-2" /> End Class
            </Button>
          )}
          {!isTeacher && (
            <Button onClick={handleLeave} className="bg-red-600 hover:bg-red-700 text-white rounded-full px-4 py-2 text-sm" data-testid="leave-class-button">
              <PhoneOff className="w-4 h-4 mr-2" /> Leave
            </Button>
          )}
        </div>
      </div>

      {/* Jitsi container */}
      <div ref={jitsiContainerRef} className="flex-1" id="jitsi-container" data-testid="jitsi-container">
        {!jitsiLoaded && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-white">
              <Loader2 className="w-12 h-12 animate-spin mx-auto mb-4 text-sky-400" />
              <p>Connecting to video room...</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default VideoClass;
