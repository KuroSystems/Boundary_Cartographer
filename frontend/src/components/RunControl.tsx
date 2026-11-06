// RunControl — idle/loading/success/error states over ApiClient.startRun (FE-03).

import { ApiError } from '../api/client';
import type { ApiClient } from '../api/client';
import { apiClient } from '../api/selectClient';
import { useRun } from '../hooks/useRun';
import { EmptyState } from './EmptyState';
import { ErrorState } from './ErrorState';
import { Skeleton } from './Skeleton';
import { StatusPill } from './StatusPill';
import { STATUS_ALLOWED, STATUS_BLOCKED, STATUS_DISPROVED } from '../api/types';

export function RunControl({ client = apiClient }: { client?: ApiClient }) {
  const { run, status, error, startRun, reset } = useRun(client);

  if (status === 'pending') {
    return <Skeleton label="Running analysis…" />;
  }

  if (status === 'error') {
    const code = error instanceof ApiError ? error.code : 'UNKNOWN';
    return (
      <ErrorState
        code={code}
        message={error?.message ?? 'unknown error'}
        onRetry={() => startRun()}
      />
    );
  }

  if (status === 'success' && run) {
    const c = run.summary.counts;
    return (
      <div className="panel" data-testid="run-summary">
        <h2>Run summary</h2>
        <p>{run.summary.headline}</p>
        <div className="counts">
          <span>
            <span className="count">{c.blocked_paths}</span> <StatusPill status={STATUS_BLOCKED} />
          </span>
          <span>
            <span className="count">{c.allowed_paths}</span> <StatusPill status={STATUS_ALLOWED} />
          </span>
          <span>
            <span className="count">{c.disproved_paths}</span>{' '}
            <StatusPill status={STATUS_DISPROVED} />
          </span>
        </div>
        <p className="mono" style={{ color: 'var(--text-dim)' }}>
          run {run.run_id}
        </p>
        <button type="button" onClick={() => startRun()}>
          Run again
        </button>{' '}
        <button type="button" onClick={() => reset()}>
          Clear
        </button>
      </div>
    );
  }

  // idle — empty state with the Run CTA
  return (
    <EmptyState
      title="No run yet"
      message="Run the offline analysis against the demo scenario. Fixture mode needs no server."
      action={
        <button type="button" onClick={() => startRun()}>
          Run analysis
        </button>
      }
    />
  );
}
