import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { authApi } from '../api/auth';
import CodeEntry from '../components/CodeEntry';
import { MailIcon, PhoneIcon } from '../components/Icons';
import { AuthLayout, CardHeading } from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import { clearPending, loadPending } from '../utils/pending';

/** Registration step 2: prove ownership of the email / phone. Success also signs the user in. */
export default function VerifyCode() {
  const { state } = useLocation();
  const navigate = useNavigate();
  const { signIn } = useAuth();
  const pending = loadPending();
  const identifier = state?.identifier || (pending.purpose === 'register' ? pending.identifier : null);

  if (!identifier) return <Navigate to="/register" replace />;
  const isEmail = identifier.includes('@');

  return (
    <AuthLayout back={{ to: '/register', label: 'Change details' }}>
      <CardHeading
        icon={isEmail ? <MailIcon size={22} /> : <PhoneIcon size={22} />}
        title={isEmail ? 'Check your email' : 'Check your phone'}
      />
      <CodeEntry
        identifier={identifier}
        initialCooldownUntil={pending.cooldownUntil}
        submitLabel="Verify and create account"
        onVerify={async (code) => {
          const res = await authApi.registerVerify(identifier, code);
          signIn(res);
          clearPending();
          navigate('/dashboard', { replace: true, state: { welcome: true } });
        }}
        onResend={() => authApi.registerResend(identifier).then(() => ({ resend_after_seconds: 30 }))}
      />
    </AuthLayout>
  );
}
