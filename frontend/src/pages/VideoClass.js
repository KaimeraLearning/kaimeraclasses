import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Phone, Mic, Video, Users } from 'lucide-react';

const VideoClass = () => {
  const { classId } = useParams();
  const navigate = useNavigate();

  const handleLeaveClass = () => {
    navigate('/student-dashboard');
  };

  return (
    <div className="min-h-screen bg-slate-900 relative flex items-center justify-center"
         style={{
           backgroundImage: 'url(https://images.unsplash.com/photo-1611623516688-c47bb8d43311?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzNzl8MHwxfHNlYXJjaHwyfHxzdHVkZW50JTIwbGVhcm5pbmclMjBvbmxpbmUlMjBmcmllbmRseXxlbnwwfHx8fDE3NzU2NDI4MDl8MA&ixlib=rb-4.1.0&q=85)',
           backgroundSize: 'cover',
           backgroundPosition: 'center',
           height: '100vh'
         }}>
      {/* Overlay */}
      <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm"></div>

      {/* Content */}
      <div className="relative z-10 text-center text-white">
        <div className="bg-white/10 backdrop-blur-xl rounded-3xl p-12 border-2 border-white/20 max-w-2xl">
          <div className="w-24 h-24 bg-sky-500 rounded-full flex items-center justify-center mx-auto mb-6">
            <Video className="w-12 h-12 text-white" />
          </div>
          <h1 className="text-4xl font-bold mb-4">Video Class Session</h1>
          <p className="text-xl text-white/80 mb-8">
            This is a placeholder for the video call integration.
          </p>
          <p className="text-white/70 mb-8">
            Class ID: {classId}
          </p>
        </div>
      </div>

      {/* Floating Controls */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-20">
        <div className="bg-white/10 backdrop-blur-xl rounded-full border-2 border-white/20 p-4 flex items-center gap-4">
          <Button
            className="w-14 h-14 rounded-full bg-slate-700/50 hover:bg-slate-600/50"
            data-testid="toggle-mic-button"
          >
            <Mic className="w-6 h-6 text-white" />
          </Button>
          <Button
            className="w-14 h-14 rounded-full bg-slate-700/50 hover:bg-slate-600/50"
            data-testid="toggle-video-button"
          >
            <Video className="w-6 h-6 text-white" />
          </Button>
          <Button
            className="w-14 h-14 rounded-full bg-slate-700/50 hover:bg-slate-600/50"
            data-testid="view-participants-button"
          >
            <Users className="w-6 h-6 text-white" />
          </Button>
          <Button
            onClick={handleLeaveClass}
            className="w-14 h-14 rounded-full bg-red-500 hover:bg-red-600"
            data-testid="leave-class-button"
          >
            <Phone className="w-6 h-6 text-white" />
          </Button>
        </div>
      </div>
    </div>
  );
};

export default VideoClass;
