import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Alert from './Alert';
import Button from './Button';
import OtpInput from './OtpInput';
import { useCountdown } from '../hooks/useCountdown';
import { maskIdentifier } from '../utils/validators';
import { savePending } from '../utils/pending';

/**
 * Shared six-digit code form (registration verification + login).
 * onVerify(code) -> resolves on success (caller navigates); onResend() -> resolves with { resend_after_seconds }.
 */
export default function CodeEntry({ identifier, onVerify, onResend, initialCooldownUntil, submitLabel = 'Verify and continue' }) {
  const navigate = useNavigate();
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [resending, setResending] = useState(false);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [cooldownUntil, setCooldownUntil] = useState(initialCooldownUntil || 0);
  const wait = useCountdown(cooldownUntil);

  function handleApiError(err) {
    if (err.code === 'ACCOUNT_LOCKED') {
      const secs = err.details?.retry_after_seconds ?? 3600;
      savePending({ identifier, lockedUntil: Date.now() + secs * 1000 });
      navigate('/locked', { replace: true, state: { identifier, retryAfterSeconds: secs } });
      return;
    }
    if (err.code === 'INVALID_CREDENTIALS') {
      const left = err.details?.remaining_attempts;
      setError(
        `That code is incorrect or has expired.${
          left != null ? ` ${left} ${left === 1 ? 'attempt' : 'attempts'} left before this account is locked for one hour.` : ''
        }`,
      );
    } else if (err.code === 'RATE_LIMITED') {
      setError('Too many attempts from your connection. Please wait a moment and try again.');
    } else {
      setError(err.message);
    }
    setCode('');
  }

  async function submit(value = code) {
    if (value.length !== 6 || busy) return;
    setBusy(true);
    setError('');
    setInfo('');
    try {
      await onVerify(value);
    } catch (err) {
      handleApiError(err);
    } finally {
      setBusy(false);
    }
  }

  async function resend() {
    setResending(true);
    setError('');
    setInfo('');
    try {
      const res = await onResend();
      const secs = res?.resend_after_seconds ?? 30;
      const until = Date.now() + secs * 1000;
      setCooldownUntil(until);
      savePending({ cooldownUntil: until });
      setInfo('A new code is on its way. Older codes no longer work.');
      setCode('');
    } catch (err) {
      if (err.code === 'RESEND_THROTTLED') {
        const secs = err.details?.retry_after_seconds ?? 30;
        setCooldownUntil(Date.now() + secs * 1000);
        setError(secs > 120 ? 'You’ve reached the hourly limit for codes. Please try again later.' : 'Please wait before requesting another code.');
      } else if (err.code === 'ACCOUNT_LOCKED') handleApiError(err);
      else setError(err.message);
    } finally {
      setResending(false);
    }
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
      noValidate
    >
      <p className="muted center">
        Enter the 6-digit code sent to <strong>{maskIdentifier(identifier)}</strong>. It expires in 5 minutes.
      </p>
      <div className="stack">
        <OtpInput value={code} onChange={setCode} onComplete={submit} disabled={busy} error={!!error} />
        <Alert variant="error">{error}</Alert>
        <Alert variant="success">{info}</Alert>
        <Button type="submit" full loading={busy} disabled={code.length !== 6}>
          {submitLabel}
        </Button>
        <div className="center">
          <Button variant="ghost" size="sm" onClick={resend} disabled={wait > 0} loading={resending}>
            {wait > 0 ? `Resend code in ${wait}s` : 'Resend code'}
          </Button>
        </div>
      </div>
    </form>
  );
}
