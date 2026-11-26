import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Button from './Button';
import { LogoutIcon, ShieldIcon } from './Icons';

export function Logo({ to = '/' }) {
  return (
    <Link to={to} className="logo" aria-label="Secure Auth home">
      <span className="logo__mark">
        <ShieldIcon size={18} />
      </span>
      <span className="logo__text">Secure Auth</span>
    </Link>
  );
}

/** Centered card used by every pre-login screen. */
export function AuthLayout({ children, wide = false, back }) {
  return (
    <div className="auth-shell">
      <header className="auth-shell__header">
        <Logo />
      </header>
      <main className="auth-shell__main" id="main">
        <div className={`card auth-card ${wide ? 'auth-card--wide' : ''}`}>
          {back && (
            <Link to={back.to} className="back-link">
              ← {back.label}
            </Link>
          )}
          {children}
        </div>
      </main>
      <footer className="auth-shell__footer">
        <span>Passwordless · Device-bound sessions · WebAuthn</span>
      </footer>
    </div>
  );
}

export function CardHeading({ icon, title, subtitle }) {
  return (
    <div className="card-heading">
      {icon && <div className="card-heading__icon">{icon}</div>}
      <h1 className="card-heading__title">{title}</h1>
      {subtitle && <p className="card-heading__subtitle">{subtitle}</p>}
    </div>
  );
}

/** Top navigation for signed-in screens. */
export function AppShell({ children }) {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  async function handleSignOut() {
    await signOut();
    navigate('/', { replace: true });
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="app-nav">
        <div className="app-nav__inner">
          <Logo to="/dashboard" />
          <nav className="app-nav__links" aria-label="Primary">
            <NavLink to="/dashboard">Dashboard</NavLink>
            <NavLink to="/security">Security</NavLink>
          </nav>
          <div className="app-nav__user">
            <span className="app-nav__name" title={user?.email || user?.phone}>
              {user?.surname}
            </span>
            <Button variant="ghost" size="sm" onClick={handleSignOut}>
              <LogoutIcon size={16} /> Sign out
            </Button>
          </div>
        </div>
      </header>
      <main className="app-main" id="main">
        {children}
      </main>
    </div>
  );
}
