import Spinner from './Spinner';

export default function Button({
  variant = 'primary',
  loading = false,
  full = false,
  size = 'md',
  type = 'button',
  disabled,
  children,
  className = '',
  ...rest
}) {
  const classes = ['btn', `btn--${variant}`, `btn--${size}`, full && 'btn--full', className].filter(Boolean).join(' ');
  return (
    <button type={type} className={classes} disabled={disabled || loading} aria-busy={loading || undefined} {...rest}>
      {loading && <Spinner size={16} label="" />}
      <span className="btn__label">{children}</span>
    </button>
  );
}
