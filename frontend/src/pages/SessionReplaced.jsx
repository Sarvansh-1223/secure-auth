import { Link } from 'react-router-dom';
import Alert from '../components/Alert';
import { DeviceIcon } from '../components/Icons';
import { AuthLayout, CardHeading } from '../components/Layout';
import { useAuth } from '../context/AuthContext';

/** Shown on the OLD device after the account signs in somewhere else (single-active-device policy). */
export default function SessionReplaced() {
  const { clearEndReason } = useAuth();
  return (
    <AuthLayout>
      <CardHeading
        icon={<DeviceIcon size={24} />}
        title="Signed in on another device"
        subtitle="Your account can only be active on one device at a time. A new sign-in replaced this session, so this device no longer has access."
      />
      <div className="stack">
        <Alert variant="warning" title="Wasn’t you?">
          Sign in again to take this device back, then review your devices and recent activity under Security.
        </Alert>
        <Link className="btn btn--primary btn--md btn--full" to="/login" onClick={clearEndReason}>
          Sign in again
        </Link>
        <Link className="btn btn--ghost btn--md btn--full" to="/" onClick={clearEndReason}>
          Back to home
        </Link>
      </div>
    </AuthLayout>
  );
}
