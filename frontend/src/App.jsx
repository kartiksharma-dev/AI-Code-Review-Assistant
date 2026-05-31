import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Dashboard from './pages/Dashboard';
import History from './pages/History';
import VerifyEmail from './pages/VerifyEmail';
import { Toaster } from 'react-hot-toast';
import useStore from './store/useStore';
import { checkSession } from './services/api';

const ProtectedRoute = ({ children }) => {
  const { user, isGuest, isLoadingSession } = useStore();
  if (isLoadingSession) {
    return <div className="h-screen bg-slate-950 flex items-center justify-center text-slate-400">Loading session...</div>;
  }
  if (!user && !isGuest) {
    return <Navigate to="/login" replace />;
  }
  return children;
};

function App() {
  const { setUser, setIsLoadingSession } = useStore();

  useEffect(() => {
    const initSession = async () => {
      const session = await checkSession();
      if (session && session.authenticated) {
        setUser(session.user);
      }
      setIsLoadingSession(false);
    };
    initSession();
  }, []);

  return (
    <Router>
      <Toaster position="bottom-right" toastOptions={{ 
        style: {
          background: '#1e293b',
          color: '#f8fafc',
          border: '1px solid #334155'
        }
      }} />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/verify-email" element={<VerifyEmail />} />
        <Route path="/dashboard" element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        } />
        <Route path="/history" element={
          <ProtectedRoute>
            <History />
          </ProtectedRoute>
        } />
      </Routes>
    </Router>
  );
}

export default App;
