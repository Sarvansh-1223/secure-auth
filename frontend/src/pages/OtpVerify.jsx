import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { authApi } from '../api/auth';
import CodeEntry from '../components/CodeEntry';
import { MailIcon } from '../components/Icons';
import { AuthLayout, CardHeading } from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import { clearPending, loadPending } from '../utils/pending';

/** Login method 1: six-digit verification code. */
export default function OtpVerify() {
  const { state } = useLocation();
  const navigate = useNavigate();
  const { signIn } = useAuth();
  const pending = loadPending();
  const identifier = state?.identifier || pending.identifier;

  if (!identifier) return <Navigate to="/login" replace />;

  return (
    <AuthLayout back={{ to: '/login', label: 'Use a different method' }}>
      <CardHeading icon={<MailIcon size={22} />} title="Enter your code" />
      <CodeEntry
        identifier={identifier}
        initialCooldownUntil={pending.cooldownUntil}
        submitLabel="Sign in"
        onVerify={async (code) => {
          const res = await authApi.otpVerify(identifier, code);
          signIn(res);
          clearPending();
          navigate('/dashboard', { replace: true });
        }}
        onResend={() => authApi.otpResend(identifier)}
      />
      <p className="muted center small mt">
        Prefer biometrics? <Link to="/login/biometric" state={{ identifier }}>Use Face ID / fingerprint</Link>
      </p>
    </AuthLayout>
  );
}
