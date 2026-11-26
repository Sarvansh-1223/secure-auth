import { useEffect } from 'react';
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import ProtectedRoute, { PublicOnlyRoute } from './components/ProtectedRoute';
import { AuthProvider, useAuth } from './context/AuthContext';
import AccountLocked from './pages/AccountLocked';
import Biometric from './pages/Biometric';
import Dashboard from './pages/Dashboard';
import Landing from './pages/Landing';
import Login from './pages/Login';
import OtpVerify from './pages/OtpVerify';
import Register from './pages/Register';
import SecuritySettings from './pages/SecuritySettings';
import SessionReplaced from './pages/SessionReplaced';
import VerifyCode from './pages/VerifyCode';

/** If the server tells us this session was replaced while we're on a signed-in page, go to the notice screen. */
function SessionWatcher() {
  const { status, endReason } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  useEffect(() => {
    if (status === 'anonymous' && endReason === 'SESSION_REPLACED' && pathname !== '/session-replaced') {
      navigate('/session-replaced', { replace: true });
    }
  }, [status, endReason, pathname, navigate]);
  return null;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <SessionWatcher />
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/register" element={<PublicOnlyRoute><Register /></PublicOnlyRoute>} />
          <Route path="/verify" element={<PublicOnlyRoute><VerifyCode /></PublicOnlyRoute>} />
          <Route path="/login" element={<PublicOnlyRoute><Login /></PublicOnlyRoute>} />
          <Route path="/login/code" element={<PublicOnlyRoute><OtpVerify /></PublicOnlyRoute>} />
          <Route path="/login/biometric" element={<PublicOnlyRoute><Biometric /></PublicOnlyRoute>} />
          <Route path="/session-replaced" element={<SessionReplaced />} />
          <Route path="/locked" element={<AccountLocked />} />
          <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/security" element={<ProtectedRoute><SecuritySettings /></ProtectedRoute>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
