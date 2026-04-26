import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

import { API } from '../utils/api';

const ProtectedRoute = ({ children, requiredRole }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(null);
  const [user, setUser] = useState(null);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    // If user data passed from AuthCallback, skip auth check
    if (location.state?.user) {
      setUser(location.state.user);
      setIsAuthenticated(true);
      return;
    }

    const checkAuth = async () => {
      try {
        const response = await fetch(`${API}/auth/me`, {
          credentials: 'include'
        });
        
        if (!response.ok) throw new Error('Not authenticated');
        
        const userData = await response.json();
        setUser(userData);
        
        // Check role if required
        if (requiredRole && userData.role !== requiredRole) {
          // Redirect to appropriate dashboard
          if (userData.role === 'student') navigate('/student-dashboard');
          else if (userData.role === 'teacher') navigate('/teacher-dashboard');
          else if (userData.role === 'counsellor') navigate('/counsellor-dashboard');
          else if (userData.role === 'admin') navigate('/admin-dashboard');
          return;
        }
        
        setIsAuthenticated(true);
      } catch (error) {
        setIsAuthenticated(false);
        navigate('/login');
      }
    };

    checkAuth();
  }, [location.state, navigate, requiredRole]);

  if (isAuthenticated === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-sky-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-slate-600 font-medium">Loading...</p>
        </div>
      </div>
    );
  }

  return children;
};

export default ProtectedRoute;
