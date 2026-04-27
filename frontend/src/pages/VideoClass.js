import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { Camera, PhoneOff, ArrowLeft, Loader2, ExternalLink } from 'lucide-react';
import { getApiError, API } from '../utils/api';

const VideoClass = () => {
  const { classId } = useParams();
  const navigate = useNavigate();
  const zoomContainerRef = useRef(null);
  const zoomClientRef = useRef(null);
  const [user, setUser] = useState(null);
  const [classInfo, setClassInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isTeacher, setIsTeacher] = useState(false);
  const [zoomReady, setZoomReady] = useState(false);
  const [zoomFailed, setZoomFailed] = useState(false);

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

  // Join Zoom embedded when class is in progress
  useEffect(() => {
    if (!classInfo || loading || !classInfo.zoom_meeting_id || classInfo.status !== 'in_progress') return;
    if (zoomClientRef.current || zoomFailed) return;

    const joinZoom = async () => {
      try {
        // Create a dedicated DOM element outside React's control
        const zoomRoot = document.createElement('div');
        zoomRoot.id = 'zoom-sdk-root';
        zoomRoot.style.cssText = 'width:100%;height:100%;position:absolute;top:0;left:0;';
        if (zoomContainerRef.current) {
          zoomContainerRef.current.appendChild(zoomRoot);
        }

        // Wait one frame so the container has measured dimensions
        await new Promise((r) => requestAnimationFrame(() => r()));
        const rootWidth = zoomRoot.clientWidth || window.innerWidth;
        const rootHeight = zoomRoot.clientHeight || (window.innerHeight - 64);

        const ZoomMtgEmbedded = (await import('@zoom/meetingsdk/embedded')).default;
        const client = ZoomMtgEmbedded.createClient();

        await client.init({
          zoomAppRoot: zoomRoot,
          language: 'en-US',
          patchJsMedia: true,
          leaveOnPageUnload: true,
          customize: {
            video: {
              isResizable: false,
              viewSizes: {
                default: { width: rootWidth, height: rootHeight },
                ribbon: { width: 300, height: rootHeight }
              }
            },
            toolbar: { buttons: [] }
          }
        });

        await client.join({
          signature: classInfo.zoom_signature,
          sdkKey: classInfo.zoom_sdk_key,
          meetingNumber: classInfo.zoom_meeting_id,
          password: classInfo.zoom_password || '',
          userName: user?.name || 'Participant',
          userEmail: user?.email || ''
        });

        // Force-resize after join in case Zoom rendered before layout settled
        try {
          const ms = client.getMeetingClient && client.getMeetingClient();
          if (ms && ms.getMediaStream) {
            const stream = ms.getMediaStream();
            if (stream && stream.resizeVideoCanvas) {
              stream.resizeVideoCanvas({ width: zoomRoot.clientWidth, height: zoomRoot.clientHeight });
            }
          }
        } catch {}

        // Window resize handler keeps the SDK matched to container
        const onResize = () => {
          try {
            const ms = client.getMeetingClient && client.getMeetingClient();
            const stream = ms && ms.getMediaStream && ms.getMediaStream();
            if (stream && stream.resizeVideoCanvas && zoomRoot) {
              stream.resizeVideoCanvas({ width: zoomRoot.clientWidth, height: zoomRoot.clientHeight });
            }
          } catch {}
        };
        window.addEventListener('resize', onResize);
        zoomClientRef.current = client;
        zoomClientRef.current._onResize = onResize;
        setZoomReady(true);
        toast.success('Connected to video class!');
      } catch (err) {
        console.error('Zoom SDK error:', err);
        setZoomFailed(true);
      }
    };

    joinZoom();

    return () => {
      if (zoomClientRef.current) {
        if (zoomClientRef.current._onResize) {
          window.removeEventListener('resize', zoomClientRef.current._onResize);
        }
        try { zoomClientRef.current.leaveMeeting(); } catch {}
        zoomClientRef.current = null;
      }
      // Clean up the zoom root element
      const existing = document.getElementById('zoom-sdk-root');
      if (existing) existing.remove();
    };
  }, [classInfo, loading, user, zoomFailed]);

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
      if (zoomClientRef.current) {
        try { zoomClientRef.current.leaveMeeting(); } catch {}
        zoomClientRef.current = null;
      }
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
    if (zoomClientRef.current) {
      try { zoomClientRef.current.leaveMeeting(); } catch {}
      zoomClientRef.current = null;
    }
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

  // Class in progress — show embedded Zoom or fallback
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

      {/* Zoom container or fallback */}
      <div ref={zoomContainerRef} className="flex-1 relative" id="zoom-container" data-testid="zoom-container">
        {!zoomReady && !zoomFailed && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-white">
              <Loader2 className="w-12 h-12 animate-spin mx-auto mb-4 text-sky-400" />
              <p>Connecting to Zoom...</p>
            </div>
          </div>
        )}

        {zoomFailed && (
          <div className="flex items-center justify-center h-full">
            <div className="bg-white/10 backdrop-blur-xl rounded-3xl p-12 border border-white/20 text-center text-white max-w-lg">
              <ExternalLink className="w-16 h-16 text-sky-400 mx-auto mb-4" />
              <h2 className="text-xl font-bold mb-3">Open Zoom Meeting</h2>
              <p className="text-white/70 mb-6">Embedded view unavailable. Join via Zoom app instead.</p>
              {classInfo?.zoom_join_url && (
                <Button onClick={() => window.open(classInfo.zoom_join_url, '_blank')}
                  className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-full py-6 font-bold text-lg" data-testid="join-zoom-btn">
                  <ExternalLink className="w-5 h-5 mr-2" /> Open Zoom Meeting
                </Button>
              )}
              {isTeacher && (
                <div className="mt-4 pt-4 border-t border-white/10">
                  <Button onClick={handleTakeScreenshot} variant="outline" className="rounded-full border-white/20 text-white hover:bg-white/10 text-sm">
                    <Camera className="w-4 h-4 mr-2" /> Capture Screenshot for Proof
                  </Button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default VideoClass;
