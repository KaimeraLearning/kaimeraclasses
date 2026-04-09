import { BrowserRouter, Routes, Route, useLocation, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import AuthCallback from './pages/AuthCallback';
import StudentDashboard from './pages/StudentDashboard';
import TeacherDashboard from './pages/TeacherDashboard';
import TeacherClasses from './pages/TeacherClasses';
import AdminDashboard from './pages/AdminDashboard';
import CounsellorDashboard from './pages/CounsellorDashboard';
import CounsellorStudents from './pages/CounsellorStudents';
import CounsellorProofs from './pages/CounsellorProofs';
import TeacherSchedule from './pages/TeacherSchedule';
import BrowseClasses from './pages/BrowseClasses';
import VideoClass from './pages/VideoClass';
import PaymentSuccess from './pages/PaymentSuccess';
import ComplaintsPage from './pages/ComplaintsPage';
import BookDemo from './pages/BookDemo';
import DemoLiveSheet from './pages/DemoLiveSheet';
import DemoFeedback from './pages/DemoFeedback';
import HistoryPage from './pages/HistoryPage';
import WalletPage from './pages/WalletPage';
import LearningKit from './pages/LearningKit';
import TeacherCalendar from './pages/TeacherCalendar';
import ChatPage from './pages/ChatPage';
import ProtectedRoute from './components/ProtectedRoute';
import { Toaster } from './components/ui/sonner';
import './App.css';

function AppRouter() {
  const location = useLocation();
  
  // Check URL fragment for session_id synchronously during render
  if (location.hash?.includes('session_id=')) {
    return <AuthCallback />;
  }
  
  return (
    <>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<Login />} />
        <Route path="/book-demo" element={<BookDemo />} />
        
        {/* Student Routes */}
        <Route path="/student-dashboard" element={
          <ProtectedRoute requiredRole="student">
            <StudentDashboard />
          </ProtectedRoute>
        } />
        <Route path="/browse-classes" element={
          <ProtectedRoute requiredRole="student">
            <BrowseClasses />
          </ProtectedRoute>
        } />
        <Route path="/demo-feedback" element={
          <ProtectedRoute requiredRole="student">
            <DemoFeedback />
          </ProtectedRoute>
        } />
        
        {/* Teacher Routes */}
        <Route path="/teacher-dashboard" element={
          <ProtectedRoute requiredRole="teacher">
            <TeacherDashboard />
          </ProtectedRoute>
        } />
        <Route path="/teacher-classes" element={
          <ProtectedRoute requiredRole="teacher">
            <TeacherClasses />
          </ProtectedRoute>
        } />
        
        {/* Counsellor Routes */}
        <Route path="/counsellor-dashboard" element={
          <ProtectedRoute requiredRole="counsellor">
            <CounsellorDashboard />
          </ProtectedRoute>
        } />
        <Route path="/counsellor/students" element={
          <ProtectedRoute requiredRole="counsellor">
            <CounsellorStudents />
          </ProtectedRoute>
        } />
        <Route path="/counsellor/proofs" element={
          <ProtectedRoute requiredRole="counsellor">
            <CounsellorProofs />
          </ProtectedRoute>
        } />
        <Route path="/counsellor/teacher-schedule/:teacherId" element={
          <ProtectedRoute requiredRole="counsellor">
            <TeacherSchedule />
          </ProtectedRoute>
        } />
        
        {/* Admin Routes */}
        <Route path="/admin-dashboard" element={
          <ProtectedRoute requiredRole="admin">
            <AdminDashboard />
          </ProtectedRoute>
        } />
        
        {/* Shared Auth Routes */}
        <Route path="/demo-live-sheet" element={
          <ProtectedRoute>
            <DemoLiveSheet />
          </ProtectedRoute>
        } />
        <Route path="/history" element={
          <ProtectedRoute>
            <HistoryPage />
          </ProtectedRoute>
        } />
        <Route path="/wallet" element={
          <ProtectedRoute>
            <WalletPage />
          </ProtectedRoute>
        } />
        <Route path="/learning-kit" element={
          <ProtectedRoute>
            <LearningKit />
          </ProtectedRoute>
        } />
        <Route path="/teacher-calendar" element={
          <ProtectedRoute requiredRole="teacher">
            <TeacherCalendar />
          </ProtectedRoute>
        } />
        <Route path="/chat" element={
          <ProtectedRoute>
            <ChatPage />
          </ProtectedRoute>
        } />
        <Route path="/class/:classId" element={
          <ProtectedRoute>
            <VideoClass />
          </ProtectedRoute>
        } />
        
        <Route path="/complaints" element={
          <ProtectedRoute>
            <ComplaintsPage />
          </ProtectedRoute>
        } />
        
        <Route path="/payment-success" element={
          <ProtectedRoute>
            <PaymentSuccess />
          </ProtectedRoute>
        } />
      </Routes>
      <Toaster position="top-center" />
    </>
  );
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AppRouter />
      </BrowserRouter>
    </div>
  );
}

export default App;
