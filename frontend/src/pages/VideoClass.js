import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { Camera, PhoneOff, ArrowLeft, Loader2 } from 'lucide-react';
import { getApiError, API } from '../utils/api';

const VideoClass = () => {
  const { classId } = useParams();
  const navigate = useNavigate();
  const zoomContainerRef = useRef(null);
  const zoomClientRef = useRef(null);
  const [user, setUser] = useState(null);
  const [classInfo, setClassInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [zoomReady, setZoomReady] = useState(false);
  const [isTeacher, setIsTeacher] = useState(false);

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

  // Join Zoom meeting when class is in progress
  useEffect(() => {
    if (!classInfo || loading || !classInfo.zoom_meeting_id || classInfo.status !== 'in_progress') return;
    if (zoomClientRef.current) return;

    const joinZoom = async () => {
      try {
        const ZoomMtgEmbedded = (await import('@zoom/meetingsdk/embedded')).default;
        const client = ZoomMtgEmbedded.createClient();

        await client.init({
          zoomAppRoot: zoomContainerRef.current,
          language: 'en-US',
          patchJsMedia: true,
          leaveOnPageUnload: true
        });

        await client.join({
          signature: classInfo.zoom_signature,
          sdkKey: classInfo.zoom_sdk_key,
          meetingNumber: classInfo.zoom_meeting_id,
          password: classInfo.zoom_password || '',
          userName: user?.name || 'Participant',
          userEmail: user?.email || ''
        });

        zoomClientRef.current = client;
        setZoomReady(true);
        toast.success('Connected to video class!');
      } catch (err) {
        console.error('Zoom join error:', err);
        // Fallback: open Zoom join URL in new tab
        if (classInfo.zoom_join_url) {
          toast.error('Embedded video failed. Opening Zoom in new tab...');
          window.open(classInfo.zoom_join_url, '_blank');
        } else {
          toast.error('Failed to connect to video class. Please try refreshing.');
        }
      }
    };

    joinZoom();

    return () => {
      if (zoomClientRef.current) {
        try { zoomClientRef.current.leaveMeeting(); } catch {}
        zoomClientRef.current = null;
      }
    };
  }, [classInfo, loading, user]);

  const handleStartClass = async () => {
    try {
      const res = await fetch(`${API}/classes/start/${classId}`, { method: 'POST', credentials: 'include' });
      if (!res.ok) throw new Error(await getApiError(res));
      toast.success('Class started! Students can now join.');
      fetchData();
    } catch (error) { toast.error(error.message); }
  };

  const handleEndClass = async () => {
    if (!window.confirm('End the class session?')) return;
    try {
      const res = await fetch(`${API}/classes/end/${classId}`, { method: 'POST', credentials: 'include' });
      if (!res.ok) throw new Error(await getApiError(res));
      const data = await res.json();
      if (zoomClientRef.current) {
        try { zoomClientRef.current.leaveMeeting(); } catch {}
        zoomClientRef.current = null;
      }
      toast.success(data.message);
      navigate('/teacher-dashboard');
    } catch (error) { toast.error(error.message); }
  };

  const handleTakeScreenshot = async () => {
    // Capture the entire Zoom container showing both teacher and student
    try {
      const container = zoomContainerRef.current;
      if (!container) { toast.error('Video container not ready'); return; }

      // Use html2canvas-like approach: capture via Screen Capture API
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
        toast.success('Screenshot captured! Both teacher and student visible.');
      }, 'image/png');
    } catch (err) {
      toast.error('Screenshot failed. Please allow screen capture when prompted.');
    }
  };

  const handleLeave = () => {
    if (zoomClientRef.current) {
      try { zoomClientRef.current.leaveMeeting(); } catch {}
      zoomClientRef.current = null;
    }
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

  // Student: class not in progress - waiting screen
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

  // Teacher: class not started - show start button
  if (isTeacher && classInfo?.status !== 'in_progress') {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-center text-white max-w-md">
          <div className="bg-white/10 backdrop-blur-xl rounded-3xl p-12 border border-white/20">
            <h2 className="text-2xl font-bold mb-3">{classInfo?.title}</h2>
            <p className="text-white/70 mb-6">Click below to start the Zoom class</p>
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

  // Class is in progress - show Zoom
  return (
    <div className="h-screen bg-slate-900 flex flex-col">
      {/* Top bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-slate-800/80 border-b border-slate-700 z-10">
        <div className="flex items-center gap-3">
          <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
          <span className="text-white font-semibold text-sm">{classInfo?.title}</span>
          <span className="text-slate-400 text-xs">LIVE via Zoom</span>
        </div>
        <div className="flex items-center gap-2">
          {isTeacher && (
            <Button onClick={handleTakeScreenshot} className="bg-sky-600 hover:bg-sky-700 text-white rounded-full px-4 py-2 text-sm" data-testid="screenshot-button">
              <Camera className="w-4 h-4 mr-2" /> Screenshot (Proof)
            </Button>
          )}
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

      {/* Zoom container */}
      <div ref={zoomContainerRef} className="flex-1 relative" id="zoom-container" data-testid="zoom-container">
        {!zoomReady && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-white">
              <Loader2 className="w-12 h-12 animate-spin mx-auto mb-4 text-sky-400" />
              <p>Connecting to Zoom meeting...</p>
              {classInfo?.zoom_join_url && (
                <p className="text-xs text-slate-400 mt-3">
                  If video doesn't load,{' '}
                  <a href={classInfo.zoom_join_url} target="_blank" rel="noopener noreferrer" className="text-sky-400 underline">
                    open in Zoom app
                  </a>
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default VideoClass;
