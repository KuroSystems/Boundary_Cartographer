import { useDemoRun, useScenario } from '../api/useDemoData';
import { GrantMatrix } from '../components/policy/GrantMatrix';
import { PolicyDiff } from '../components/policy/PolicyDiff';
import { RecommendationCard } from '../components/policy/RecommendationCard';
import { RuleList } from '../components/policy/RuleList';
import { RetestCallout } from '../components/retest/RetestCallout';
import { RetestTable } from '../components/retest/RetestTable';
import { Skeleton } from '../components/Skeleton';
import { ErrorState } from '../components/ErrorState';

// PolicyView (FE-07/FE-08): the /policy route — recommendation, simulated
// diff, retest table + callout, rules, read-only grant matrix (over-grant
// flagged). No apply button.
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
      <RetestTable retests={r.retests} />
      <RetestCallout retests={r.retests} />
      <RuleList scenario={scenario.data} />
      <GrantMatrix scenario={scenario.data} flagged={revoked} />
    </div>
  );
}
