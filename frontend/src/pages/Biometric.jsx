import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { authApi } from '../api/auth';
import { getAssertion, WebAuthnClientError } from '../api/webauthn';
import Alert from '../components/Alert';
import Button from '../components/Button';
import { FaceIdIcon } from '../components/Icons';
import { AuthLayout, CardHeading } from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import { unavailableReason, useWebAuthnSupport } from '../hooks/useWebAuthnSupport';
import { clearPending, loadPending, savePending } from '../utils/pending';
import { maskIdentifier } from '../utils/validators';

/** Login methods 2 and 3: WebAuthn (platform biometrics, phones, security keys). Falls back to codes. */
export default function Biometric() {
  const { state } = useLocation();
  const navigate = useNavigate();
  const { signIn } = useAuth();
  const support = useWebAuthnSupport();
  const identifier = state?.identifier || loadPending().identifier;
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  if (!identifier) return <Navigate to="/login" replace />;

  const blocked = support.checked && (!support.supported || !support.secure);
  const note = support.checked ? unavailableReason(support) : '';

  async function authenticate() {
    setBusy(true);
    setError('');
    try {
      const { options } = await authApi.webauthnAuthOptions(identifier);
      const credential = await getAssertion(options);
      const res = await authApi.webauthnAuthVerify(credential);
      signIn(res);
      clearPending();
      navigate('/dashboard', { replace: true });
    } catch (err) {
      if (err instanceof WebAuthnClientError) {
        setError(err.kind === 'cancelled' ? 'Biometric sign-in was cancelled or timed out. Try again, or use a code instead.' : err.message);
      } else if (err.code === 'ACCOUNT_LOCKED') {
        const secs = err.details?.retry_after_seconds ?? 3600;
        savePending({ identifier, lockedUntil: Date.now() + secs * 1000 });
        navigate('/locked', { replace: true, state: { identifier, retryAfterSeconds: secs } });
        return;
      } else if (err.code === 'INVALID_CREDENTIALS' || err.code === 'WEBAUTHN_FAILED') {
        const left = err.details?.remaining_attempts;
        setError(
          `Biometric sign-in failed. Make sure you’ve set up biometrics for this account, or use a verification code.${
            left != null ? ` ${left} ${left === 1 ? 'attempt' : 'attempts'} left before a one-hour lock.` : ''
          }`,
        );
      } else {
        setError(err.message);
      }
    } finally {
      setBusy(false);
    }
  }

  async function codeInstead() {
    try {
      const res = await authApi.otpRequest(identifier);
      savePending({ cooldownUntil: Date.now() + res.resend_after_seconds * 1000 });
    } catch (err) {
      if (err.code === 'ACCOUNT_LOCKED') {
        navigate('/locked', { state: { identifier, retryAfterSeconds: err.details?.retry_after_seconds ?? 3600 } });
        return;
      }
    }
    navigate('/login/code', { state: { identifier } });
  }

  return (
    <AuthLayout back={{ to: '/login', label: 'Back' }}>
      <CardHeading
        icon={<FaceIdIcon size={24} />}
        title="Sign in with biometrics"
        subtitle={`Verify it’s you, ${maskIdentifier(identifier)}, with the Face ID, fingerprint, Windows Hello, phone or security key you registered.`}
      />
      <div className="stack">
        <Alert variant={blocked ? 'warning' : 'info'} title={blocked ? 'Biometrics unavailable' : undefined}>
          {note}
        </Alert>
        <Alert variant="error">{error}</Alert>
        <Button full loading={busy} onClick={authenticate} disabled={blocked || !support.checked}>
          <FaceIdIcon size={18} /> Continue with biometrics
        </Button>
        <div className="divider"><span>or</span></div>
        <Button variant="secondary" full onClick={codeInstead}>Email me a six-digit code instead</Button>
        <p className="muted center small">
          Biometric data never leaves your device: your browser proves you unlocked a private key and we verify it
          with the matching public key. <Link to="/register">No account yet?</Link>
        </p>
      </div>
    </AuthLayout>
  );
}
