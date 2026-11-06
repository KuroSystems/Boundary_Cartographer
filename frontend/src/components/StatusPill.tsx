import type { PathStatus } from '../api/types';

export function StatusPill({ status }: { status: PathStatus | string }) {
  return <span className={`status-pill status-${status}`}>{status}</span>;
}
