import { ApiError } from '../api/client';
import type { ApiClient } from '../api/client';
import { apiClient } from '../api/selectClient';
import { useDemoRun } from '../api/useDemoData';
import { useApproval } from '../hooks/useApproval';
import { ApprovalCard } from '../components/approval/ApprovalCard';
import { ApprovalConsequences } from '../components/approval/ApprovalConsequences';
import { Skeleton } from '../components/Skeleton';
import { ErrorState } from '../components/ErrorState';

// ApprovalsView (FE-09): the /approvals route. The queue records decisions
// only — after deciding, the run's paths are still shown unchanged (they are
// never refetched as if policy had changed).
export function ApprovalsView() {
  const run = useDemoRun();

  if (run.isLoading) return <Skeleton label="Loading run…" />;
  if (run.error || !run.data) {
    return (
      <ErrorState
        code="RUN_UNAVAILABLE"
        message={run.error instanceof Error ? run.error.message : 'unknown error'}
      />
    );
  }

  return <ApprovalsInner run={run.data} />;
}

export function ApprovalsInner({
  run,
  client = apiClient,
}: {
  run: NonNullable<ReturnType<typeof useDemoRun>['data']>;
  client?: ApiClient;
}) {
  const { approval, conflict, deciding, error, decide } = useApproval(run, client);

  return (
    <div>
      <div className="panel">
        <h2>Approval queue — status: {approval.status}</h2>
        {conflict && (
          <p role="alert" data-testid="conflict-note">
            already decided — refreshed from source (HTTP 409 APPROVAL_ALREADY_DECIDED)
          </p>
        )}
        {error && !(error instanceof ApiError && error.status === 409) && (
          <p role="alert" data-testid="approval-error">
            decision failed and was rolled back: {error.message}
          </p>
        )}
      </div>
      {approval.items.map((item) => (
        <ApprovalCard key={item.approval_id} item={item} deciding={deciding} onDecide={decide} />
      ))}
      <ApprovalConsequences />
      <div className="panel" data-testid="paths-unchanged">
        <h2>Run paths (unchanged by any decision)</h2>
        <p className="mono" style={{ fontSize: '0.8rem' }}>
          {run.paths.map((p) => `${p.path_id}=${p.status}`).join(' · ')}
        </p>
      </div>
    </div>
  );
}
