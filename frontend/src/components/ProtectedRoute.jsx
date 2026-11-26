import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { AppShell } from './Layout';
import { PageLoader } from './Spinner';

/** Renders signed-in screens. Access is decided by the server (/me); this only reflects it. */
export default function ProtectedRoute({ children }) {
  const { status, endReason } = useAuth();
  const location = useLocation();

  if (status === 'loading') return <PageLoader label="Checking your session…" />;
  if (status === 'anonymous') {
    if (endReason === 'SESSION_REPLACED') return <Navigate to="/session-replaced" replace />;
    return <Navigate to="/login" replace state={{ from: location.pathname, expired: endReason === 'SESSION_EXPIRED' }} />;
  }
  return <AppShell>{children}</AppShell>;
}

/** Keeps signed-in users out of the login/registration screens. */
export function PublicOnlyRoute({ children }) {
  const { status } = useAuth();
  if (status === 'loading') return <PageLoader />;
  if (status === 'authenticated') return <Navigate to="/dashboard" replace />;
  return children;
}
