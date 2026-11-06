// Skeleton — loading placeholder (FE-03).

export function Skeleton({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="panel" data-testid="skeleton" aria-busy="true">
      <p>{label}</p>
      <div className="mono" style={{ color: 'var(--text-dim)' }}>
        ▓▒░ ▓▒░ ▓▒░
      </div>
    </div>
  );
}
