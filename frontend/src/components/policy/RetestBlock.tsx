import type { Retest } from '../../api/types';
import { DECISION_TO_PILL, STATUS_ALLOWED, STATUS_BLOCKED } from '../../api/types';
import { StatusPill } from '../StatusPill';

// RetestBlock (FE-07/FE-08): RT-1..RT-3 side by side — proves the attack paths
// stay blocked (RT-1) while the legitimate workflow stays allowed (RT-2/RT-3).
export function RetestBlock({ retests }: { retests: Retest[] }) {
  return (
    <div className="panel" data-testid="retest-block">
      <h2>Retests against the simulated policy</h2>
      <div className="retest-grid">
        {retests.map((r) => (
          <div
            key={r.retest_id}
            className={`retest-card${r.passed ? ' retest-passed' : ' retest-failed'}`}
            data-testid={`retest-${r.retest_id}`}
          >
            <h3 className="mono">{r.retest_id}</h3>
            <p>{r.name}</p>
            <p>
              expected <StatusPill status={DECISION_TO_PILL[r.expected] ?? STATUS_ALLOWED} /> actual{' '}
              <StatusPill status={DECISION_TO_PILL[r.actual] ?? STATUS_ALLOWED} /> passed{' '}
              {String(r.passed)}
            </p>
          </div>
        ))}
      </div>
      <p style={{ color: 'var(--text-dim)', fontSize: '0.8rem' }}>
        <StatusPill status={STATUS_BLOCKED} /> RT-1 stays blocked ·{' '}
        <StatusPill status={STATUS_ALLOWED} /> RT-2/RT-3 stay allowed — legitimate workflows are not broken
      </p>
    </div>
  );
}
