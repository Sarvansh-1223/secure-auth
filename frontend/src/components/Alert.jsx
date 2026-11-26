import { AlertIcon, CheckIcon, ShieldIcon } from './Icons';

const ICON = { error: AlertIcon, warning: AlertIcon, success: CheckIcon, info: ShieldIcon };

export default function Alert({ variant = 'info', title, children, className = '' }) {
  if (!children && !title) return null;
  const Icon = ICON[variant];
  return (
    <div className={`alert alert--${variant} ${className}`} role={variant === 'error' ? 'alert' : 'status'}>
      <Icon size={18} className="alert__icon" />
      <div>
        {title && <strong className="alert__title">{title}</strong>}
        {children && <div className="alert__body">{children}</div>}
      </div>
    </div>
  );
}
