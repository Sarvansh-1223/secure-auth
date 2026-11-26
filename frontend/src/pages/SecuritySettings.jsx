import { useCallback, useEffect, useState } from 'react';
import { authApi } from '../api/auth';
import Alert from '../components/Alert';
import Button from '../components/Button';
import { DeviceIcon, FaceIdIcon, KeyIcon, TrashIcon } from '../components/Icons';
import { PageLoader } from '../components/Spinner';
import { useAuth } from '../context/AuthContext';
import { useBiometricEnrollment } from '../hooks/useBiometricEnrollment';
import { unavailableReason, useWebAuthnSupport } from '../hooks/useWebAuthnSupport';
import { formatDateTime, formatRelative, METHOD_LABEL } from '../utils/format';

export default function SecuritySettings() {
  const { session } = useAuth();
  const support = useWebAuthnSupport();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [removing, setRemoving] = useState(null);

  const load = useCallback(async () => {
    try {
      setData(await authApi.securitySettings());
      setError('');
    } catch (err) {
      if (!err.code?.startsWith('SESSION')) setError(err.message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const { enroll, busy, error: enrollError, clearError } = useBiometricEnrollment(() => {
    setNotice('Biometric credential added.');
    load();
  });
  const [pendingKind, setPendingKind] = useState(null);

  async function add(kind) {
    setNotice('');
    clearError();
    setPendingKind(kind);
    await enroll(kind, kind === 'platform' ? session?.device?.label : 'Security key / phone');
    setPendingKind(null);
  }

  async function remove(id) {
    setRemoving(id);
    setNotice('');
    try {
      await authApi.removeCredential(id);
      setNotice('Credential removed.');
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setRemoving(null);
    }
  }

  if (!data) return error ? <div className="page"><Alert variant="error">{error}</Alert></div> : <PageLoader />;

  const unavailable = support.checked ? unavailableReason(support) : '';
  const canUse = support.checked && support.supported && support.secure;

  return (
    <div className="page">
      <div className="page__head">
        <div>
          <p className="eyebrow">Security</p>
          <h1 className="page__title">Security settings</h1>
        </div>
      </div>
      <Alert variant="success">{notice}</Alert>
      <Alert variant="error">{error}</Alert>

      <section className="card section" aria-labelledby="s-bio">
        <div className="section__head">
          <div>
            <h2 id="s-bio"><FaceIdIcon size={18} /> Biometric sign-in</h2>
            <p className="muted">Face ID, Touch ID, Windows Hello, phones and security keys, through WebAuthn. We store only public keys.</p>
          </div>
        </div>

        {unavailable && <Alert variant={canUse ? 'info' : 'warning'}>{unavailable}</Alert>}
        <Alert variant="error">{enrollError}</Alert>

        {data.credentials.length === 0 ? (
          <p className="empty">No biometric credentials yet.</p>
        ) : (
          <ul className="list">
            {data.credentials.map((c) => (
              <li className="list__item" key={c.id}>
                <div className="list__icon">{c.attachment === 'cross-platform' ? <KeyIcon size={18} /> : <FaceIdIcon size={18} />}</div>
                <div className="list__main">
                  <strong>{c.nickname}</strong>
                  <span className="muted small">
                    {c.attachment === 'cross-platform' ? 'Phone / security key' : 'This-device biometrics'} · added {formatDateTime(c.created_at)} · last used {c.last_used_at ? formatRelative(c.last_used_at) : 'never'}
                  </span>
                </div>
                <Button variant="danger" size="sm" loading={removing === c.id} onClick={() => remove(c.id)} aria-label={`Remove ${c.nickname}`}>
                  <TrashIcon size={14} /> Remove
                </Button>
              </li>
            ))}
          </ul>
        )}

        <div className="row">
          <Button loading={busy && pendingKind === 'platform'} disabled={!canUse || busy} onClick={() => add('platform')}>
            <FaceIdIcon size={16} /> Add this device’s biometrics
          </Button>
          <Button variant="secondary" loading={busy && pendingKind === 'cross-platform'} disabled={!canUse || busy} onClick={() => add('cross-platform')}>
            <KeyIcon size={16} /> Add phone or security key
          </Button>
        </div>
      </section>

      <section className="card section" aria-labelledby="s-dev">
        <div className="section__head">
          <div>
            <h2 id="s-dev"><DeviceIcon size={18} /> Devices</h2>
            <p className="muted">Only one device can be active. Signing in elsewhere ends the active session instantly.</p>
          </div>
        </div>
        <ul className="list">
          {data.devices.map((d) => (
            <li className="list__item" key={d.id}>
              <div className="list__icon"><DeviceIcon size={18} /></div>
              <div className="list__main">
                <strong>{d.label}</strong>
                <span className="muted small">First seen {formatDateTime(d.first_seen_at)} · last active {formatRelative(d.last_seen_at)}</span>
              </div>
              <div className="list__badges">
                {d.is_current && <span className="badge badge--info">This device</span>}
                <span className={`badge ${d.is_active ? 'badge--success' : ''}`}>{d.is_active ? 'Active' : 'Signed out'}</span>
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section className="card section" aria-labelledby="s-act">
        <div className="section__head">
          <div>
            <h2 id="s-act">Recent sign-in activity</h2>
            <p className="muted">Five consecutive failures lock the account for {data.policy.lockout_minutes} minutes.</p>
          </div>
        </div>
        {data.recent_activity.length === 0 ? (
          <p className="empty">No activity yet.</p>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>When</th><th>Method</th><th>Result</th><th>IP address</th></tr></thead>
              <tbody>
                {data.recent_activity.map((a, i) => (
                  <tr key={i}>
                    <td>{formatDateTime(a.at)}</td>
                    <td>{METHOD_LABEL[a.method] || a.method}</td>
                    <td><span className={`badge ${a.success ? 'badge--success' : 'badge--danger'}`}>{a.success ? 'Success' : 'Failed'}</span></td>
                    <td>{a.ip_address || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
