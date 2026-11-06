import { useDemoRun, useScenario } from '../api/useDemoData';
import { GrantMatrix } from '../components/policy/GrantMatrix';
import { PolicyDiff } from '../components/policy/PolicyDiff';
import { RecommendationCard } from '../components/policy/RecommendationCard';
import { RetestBlock } from '../components/policy/RetestBlock';
import { RuleList } from '../components/policy/RuleList';
import { Skeleton } from '../components/Skeleton';
import { ErrorState } from '../components/ErrorState';

// PolicyView (FE-07): the /policy route — recommendation, simulated diff,
// rules, read-only grant matrix (over-grant flagged), retests. No apply button.
export function PolicyView() {
  const run = useDemoRun();
  const scenario = useScenario();

  if (run.isLoading || scenario.isLoading) return <Skeleton label="Loading policy…" />;
  if (run.error || !run.data || scenario.error || !scenario.data) {
    return (
      <ErrorState
        code="POLICY_UNAVAILABLE"
        message={run.error instanceof Error ? run.error.message : 'unknown error'}
      />
    );
  }

  const r = run.data;
  // Flag grant cells that the recommendation revokes (target identity:tool).
  const revoked = r.recommendation.changes
    .filter((c) => c.op === 'revoke_grant')
    .map((c) => c.target);

  return (
    <div>
      <RecommendationCard rec={r.recommendation} />
      <PolicyDiff diff={r.policy_diff} />
      <RetestBlock retests={r.retests} />
      <RuleList scenario={scenario.data} />
      <GrantMatrix scenario={scenario.data} flagged={revoked} />
    </div>
  );
}
