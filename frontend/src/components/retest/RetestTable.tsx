import { Link } from 'react-router-dom';
import type { Retest } from '../../api/types';
import { DECISION_TO_PILL, STATUS_ALLOWED, STATUS_BLOCKED } from '../../api/types';
import { StatusPill } from '../StatusPill';

// RetestTable (FE-08): RT-1..RT-3 with workflow, expected, actual, pass/fail,
// and evidence refs (linked to the evidence view).
export function RetestTable({ retests }: { retests: Retest[] }) {
  return (
    <div className="panel" data-testid="retest-table">
      <h2>Retests against the simulated policy</h2>
      <table className="data">
        <thead>
          <tr>
            <th scope="col">Retest</th>
            <th scope="col">Workflow</th>
            <th scope="col">Expected</th>
            <th scope="col">Actual</th>
            <th scope="col">Result</th>
            <th scope="col">Evidence</th>
          </tr>
        </thead>
        <tbody>
          {retests.map((r) => (
            <tr key={r.retest_id} data-testid={`retest-row-${r.retest_id}`}>
              <td className="mono">{r.retest_id}</td>
              <td>{r.name}</td>
              <td>
                <StatusPill status={DECISION_TO_PILL[r.expected] ?? STATUS_ALLOWED} />
              </td>
              <td>
                <StatusPill status={DECISION_TO_PILL[r.actual] ?? STATUS_ALLOWED} />
              </td>
              <td>
                {r.passed ? (
                  <span className="retest-result retest-pass">PASS</span>
                ) : (
                  <span className="retest-result retest-fail" role="alert">
                    FAIL — retest did not match expectation
                  </span>
                )}
              </td>
              <td className="mono">
                {r.evidence_ids.map((e) => (
                  <Link key={e} to={`/evidence#${encodeURIComponent(e)}`} className="source-id-link">
                    {e}
                  </Link>
                ))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p style={{ color: 'var(--text-dim)', fontSize: '0.8rem' }}>
        <StatusPill status={STATUS_BLOCKED} /> RT-1 stays blocked ·{' '}
        <StatusPill status={STATUS_ALLOWED} /> RT-2/RT-3 stay allowed — legitimate workflows are not broken
      </p>
    </div>
  );
}
