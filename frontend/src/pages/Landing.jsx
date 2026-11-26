import { Link } from 'react-router-dom';
import { Logo } from '../components/Layout';
import { DeviceIcon, FaceIdIcon, LockIcon, MailIcon } from '../components/Icons';
import { useAuth } from '../context/AuthContext';

const FEATURES = [
  { icon: <FaceIdIcon size={22} />, title: 'Biometric sign-in', text: 'Face ID, Touch ID, Windows Hello or a security key through WebAuthn. Your biometrics never leave your device.' },
  { icon: <MailIcon size={22} />, title: 'One-time codes', text: 'A six-digit code by email or SMS that expires in minutes and works exactly once.' },
  { icon: <DeviceIcon size={22} />, title: 'One active device', text: 'Signing in on a new device ends the previous session instantly, enforced on the server.' },
  { icon: <LockIcon size={22} />, title: 'Brute-force protection', text: 'Five consecutive failed attempts lock the account for one hour, wherever you try from.' },
];

export default function Landing() {
  const { status } = useAuth();
  const signedIn = status === 'authenticated';
  return (
    <div className="landing">
      <header className="landing__nav">
        <Logo />
        <nav className="landing__nav-links" aria-label="Account">
          {signedIn ? (
            <Link className="btn btn--primary btn--md" to="/dashboard">Open dashboard</Link>
          ) : (
            <>
              <Link className="btn btn--ghost btn--md" to="/login">Sign in</Link>
              <Link className="btn btn--primary btn--md" to="/register">Create account</Link>
            </>
          )}
        </nav>
      </header>

      <main id="main">
        <section className="hero">
          <p className="eyebrow">Secure identity platform</p>
          <h1 className="hero__title">Sign in without passwords.<br />Stay in control of every device.</h1>
          <p className="hero__lead">
            Verified by one-time codes and hardware-backed biometrics, with server-enforced sessions and
            automatic lockout protection.
          </p>
          <div className="hero__cta">
            <Link className="btn btn--primary btn--lg" to={signedIn ? '/dashboard' : '/register'}>
              {signedIn ? 'Open dashboard' : 'Create your account'}
            </Link>
            {!signedIn && (
              <Link className="btn btn--secondary btn--lg" to="/login">
                Sign in
              </Link>
            )}
          </div>
        </section>

        <section className="features" aria-label="Features">
          {FEATURES.map((f) => (
            <article className="feature card" key={f.title}>
              <div className="feature__icon">{f.icon}</div>
              <h2 className="feature__title">{f.title}</h2>
              <p className="feature__text">{f.text}</p>
            </article>
          ))}
        </section>
      </main>

      <footer className="landing__footer">Passwordless authentication · Django + React + WebAuthn</footer>
    </div>
  );
}
