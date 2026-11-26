import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { authApi } from '../api/auth';
import Alert from '../components/Alert';
import Button from '../components/Button';
import Input from '../components/Input';
import { LockIcon } from '../components/Icons';
import { AuthLayout, CardHeading } from '../components/Layout';
import { useCountdown } from '../hooks/useCountdown';
import { formatDuration } from '../utils/format';
import { loadPending, savePending } from '../utils/pending';
import { normalizeIdentifier, validateIdentifier } from '../utils/validators';

/**
 * Remaining time always comes from the server (GET /auth/lockout-status), so refreshing the page or
 * opening another device shows the same authoritative countdown.
 */
export default function AccountLocked() {
  const { state } = useLocation();
  const navigate = useNavigate();
  const pending = loadPending();
  const initial = state?.identifier || pending.identifier || '';
  const [identifier, setIdentifier] = useState(initial);
  const [fieldError, setFieldError] = useState('');
  const [until, setUntil] = useState(
    state?.retryAfterSeconds ? Date.now() + state.retryAfterSeconds * 1000 : pending.lockedUntil || 0,
  );
  const [checking, setChecking] = useState(!!initial);
  const [notLocked, setNotLocked] = useState(false);
  const remaining = useCountdown(until);

  async function check(id) {
    setChecking(true);
    setNotLocked(false);
    try {
      const res = await authApi.lockoutStatus(id);
      if (res.locked) {
        const target = Date.now() + res.retry_after_seconds * 1000;
        setUntil(target);
        savePending({ identifier: id, lockedUntil: target });
      } else {
        setUntil(0);
        setNotLocked(true);
      }
    } catch {
      /* keep whatever we already know */
    } finally {
      setChecking(false);
    }
  }

  useEffect(() => {
    if (initial) check(initial);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function onSubmit(e) {
    e.preventDefault();
    const msg = validateIdentifier(identifier);
    setFieldError(msg);
    if (!msg) check(normalizeIdentifier(identifier));
  }

  const locked = remaining > 0;
  const total = 3600;
  const pct = Math.min(100, Math.max(0, ((total - remaining) / total) * 100));

  return (
    <AuthLayout>
      <CardHeading
        icon={<LockIcon size={24} />}
        title={locked ? 'Account temporarily locked' : 'Check account status'}
        subtitle={
          locked
            ? 'After five unsuccessful attempts, sign-in is blocked for one hour to protect the account. This applies on every device.'
            : 'Enter the email or mobile number to see whether sign-in is currently blocked.'
        }
      />
      <div className="stack">
        {locked && (
          <div className="lock-timer" role="timer" aria-live="off">
            <span className="lock-timer__label">Try again in</span>
            <span className="lock-timer__value" aria-label={`${Math.ceil(remaining / 60)} minutes remaining`}>{formatDuration(remaining)}</span>
            <div className="progress" aria-hidden="true"><div className="progress__bar" style={{ width: `${pct}%` }} /></div>
          </div>
        )}

        {!locked && notLocked && <Alert variant="success">Sign-in isn’t blocked right now. You can try again.</Alert>}

        {!initial && !locked && (
          <form className="stack" onSubmit={onSubmit} noValidate>
            <Input label="Email or mobile number" value={identifier} onChange={(e) => { setIdentifier(e.target.value); setFieldError(''); }} error={fieldError} />
            <Button type="submit" full loading={checking}>Check status</Button>
          </form>
        )}

        {!locked && (initial || notLocked) && (
          <Button full loading={checking && !notLocked} onClick={() => navigate('/login')}>Back to sign in</Button>
        )}
        {locked && <Link className="btn btn--ghost btn--md btn--full" to="/">Back to home</Link>}
      </div>
    </AuthLayout>
  );
}
