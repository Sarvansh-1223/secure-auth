import { useCallback, useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { authApi } from '../api/auth';
import Alert from '../components/Alert';
import Button from '../components/Button';
import { CheckIcon, DeviceIcon, FaceIdIcon, ShieldIcon } from '../components/Icons';
import Spinner from '../components/Spinner';
import { useAuth } from '../context/AuthContext';
import { useBiometricEnrollment } from '../hooks/useBiometricEnrollment';
import { useWebAuthnSupport } from '../hooks/useWebAuthnSupport';
import { formatDateTime, METHOD_LABEL } from '../utils/format';

export default function Dashboard() {
  const { user, session, setBiometricEnrolled } = useAuth();
  const { state } = useLocation();
  const support = useWebAuthnSupport();
  const [settings, setSettings] = useState(null);
  const [loadError, setLoadError] = useState('');
  const [enrolledNow, setEnrolledNow] = useState(false);

  const load = useCallback(async () => {
    try {
      setSettings(await authApi.securitySettings());
      setLoadError('');
    } catch (err) {
      if (!err.code?.startsWith('SESSION')) setLoadError(err.message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const { enroll, busy, error } = useBiometricEnrollment(() => {
    setEnrolledNow(true);
    setBiometricEnrolled(true);
    load();
  });

  const enrolled = settings ? settings.credentials.length > 0 : null;
  const canOffer = support.checked && support.supported && support.secure && enrolled === false;

  return (
    <div className="page">
      <div className="page__head">
        <div>
          <p className="eyebrow">Dashboard</p>
          <h1 className="page__title">Welcome, {user?.surname}</h1>
        </div>
      </div>

      {state?.welcome && <Alert variant="success" title="Account verified">Your {user?.email ? 'email' : 'number'} is verified and you’re signed in.</Alert>}
      {enrolledNow && <Alert variant="success" title="Biometric sign-in enabled">Next time you can sign in with just a look or a touch.</Alert>}
      <Alert variant="error">{loadError}</Alert>

      {canOffer && (
        <section className="card promo">
          <div className="promo__icon"><FaceIdIcon size={26} /></div>
          <div className="promo__body">
            <h2>Enable Face ID / Touch ID / Windows Hello</h2>
            <p className="muted">Skip the email code next time. Your biometrics stay on this device; we only store a public key.</p>
            <Alert variant="error">{error}</Alert>
          </div>
          <Button loading={busy} onClick={() => enroll('platform', session?.device?.label)}>Set up biometrics</Button>
        </section>
      )}

      <div className="grid-cards">
        <section className="card tile" aria-labelledby="t-session">
          <div className="tile__head"><DeviceIcon size={18} /><h2 id="t-session">This device</h2><span className="badge badge--success">Active</span></div>
          <dl className="kv">
            <div><dt>Device</dt><dd>{session?.device?.label}</dd></div>
            <div><dt>Signed in</dt><dd>{formatDateTime(session?.started_at)}</dd></div>
            <div><dt>Method</dt><dd>{METHOD_LABEL[session?.auth_method] || session?.auth_method}</dd></div>
            <div><dt>Session ends</dt><dd>{formatDateTime(session?.expires_at)}</dd></div>
          </dl>
        </section>

        <section className="card tile" aria-labelledby="t-account">
          <div className="tile__head"><ShieldIcon size={18} /><h2 id="t-account">Account</h2></div>
          <dl className="kv">
            <div><dt>{user?.email ? 'Email' : 'Mobile'}</dt><dd>{user?.email || user?.phone} <span className="badge badge--success"><CheckIcon size={12} /> Verified</span></dd></div>
            <div><dt>Surname</dt><dd>{user?.surname}</dd></div>
            <div><dt>Date of birth</dt><dd>{user?.date_of_birth}</dd></div>
            <div><dt>Biometrics</dt><dd>{enrolled === null ? <Spinner size={14} /> : enrolled ? `${settings.credentials.length} registered` : 'Not set up'}</dd></div>
          </dl>
        </section>

        <section className="card tile" aria-labelledby="t-policy">
          <div className="tile__head"><ShieldIcon size={18} /><h2 id="t-policy">Protection</h2></div>
          <ul className="check-list">
            <li><CheckIcon size={16} /> One active device at a time</li>
            <li><CheckIcon size={16} /> Locked for 1 hour after 5 failed attempts</li>
            <li><CheckIcon size={16} /> Server-side sessions, revoked instantly</li>
            <li><CheckIcon size={16} /> Codes expire in 5 minutes, single use</li>
          </ul>
          <Link className="btn btn--secondary btn--md" to="/security">Manage security</Link>
        </section>
      </div>
    </div>
  );
}
