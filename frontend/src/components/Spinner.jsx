export default function Spinner({ size = 20, label = 'Loading' }) {
  return (
    <span className="spinner" role={label ? 'status' : undefined} aria-label={label || undefined} style={{ width: size, height: size }} />
  );
}

export function PageLoader({ label = 'Loading…' }) {
  return (
    <div className="page-loader">
      <Spinner size={28} label={label} />
    </div>
  );
}
