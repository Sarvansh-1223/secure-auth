import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { authApi } from '../api/auth';
import Alert from '../components/Alert';
import Button from '../components/Button';
import { FaceIdIcon, LockIcon } from '../components/Icons';
import Input from '../components/Input';
import { AuthLayout, CardHeading } from '../components/Layout';
import { loadPending, savePending } from '../utils/pending';
import { normalizeIdentifier, validateIdentifier } from '../utils/validators';

export default function Login() {
  const navigate = useNavigate();
  const { state } = useLocation();
  const [identifier, setIdentifier] = useState(loadPending().identifier || '');
  const [error, setError] = useState('');
  const [formError, setFormError] = useState(state?.expired ? 'Your session expired. Please sign in again.' : '');
  const [busy, setBusy] = useState(false);

  function goLocked(err, id) {
    const secs = err.details?.retry_after_seconds ?? 3600;
    savePending({ identifier: id, lockedUntil: Date.now() + secs * 1000 });
    navigate('/locked', { state: { identifier: id, retryAfterSeconds: secs } });
  }

  function check() {
    const msg = validateIdentifier(identifier);
    setError(msg);
    return !msg;
  }

  async function sendCode(e) {
    e.preventDefault();
    setFormError('');
    if (!check()) return;
    const id = normalizeIdentifier(identifier);
    setBusy(true);
    try {
      const res = await authApi.otpRequest(id);
      savePending({ identifier: id, purpose: 'login', cooldownUntil: Date.now() + res.resend_after_seconds * 1000 });
      navigate('/login/code', { state: { identifier: id } });
    } catch (err) {
      if (err.code === 'ACCOUNT_LOCKED') goLocked(err, id);
      else if (err.code === 'RESEND_THROTTLED') {
        savePending({ identifier: id, purpose: 'login', cooldownUntil: Date.now() + (err.details?.retry_after_seconds ?? 30) * 1000 });
        navigate('/login/code', { state: { identifier: id } }); // a code was already sent moments ago
      } else if (err.code === 'VALIDATION_ERROR') setError('Enter a valid email address or mobile number.');
      else setFormError(err.code === 'RATE_LIMITED' ? 'Too many requests. Please wait a moment.' : err.message);
    } finally {
      setBusy(false);
    }
  }

  function useBiometrics() {
    setFormError('');
    if (!check()) return;
    const id = normalizeIdentifier(identifier);
    savePending({ identifier: id, purpose: 'login' });
    navigate('/login/biometric', { state: { identifier: id } });
  }

  return (
    <AuthLayout back={{ to: '/', label: 'Home' }}>
      <CardHeading icon={<LockIcon size={22} />} title="Welcome back" subtitle="Sign in with a code or your device’s biometrics." />
      <form className="stack" onSubmit={sendCode} noValidate>
        <Input
          label="Email or mobile number"
          autoComplete="username webauthn"
          inputMode="email"
          placeholder="you@company.com or +14155552671"
          value={identifier}
          onChange={(e) => { setIdentifier(e.target.value); setError(''); }}
          error={error}
          autoFocus
        />
        <Alert variant={state?.expired ? 'info' : 'error'}>{formError}</Alert>
        <Button type="submit" full loading={busy}>Email me a six-digit code</Button>
        <div className="divider"><span>or</span></div>
        <Button variant="secondary" full onClick={useBiometrics}>
          <FaceIdIcon size={18} /> Use Face ID / Touch ID / Windows Hello
        </Button>
        <p className="muted center small">
          New here? <Link to="/register">Create an account</Link>
        </p>
      </form>
    </AuthLayout>
  );
}
