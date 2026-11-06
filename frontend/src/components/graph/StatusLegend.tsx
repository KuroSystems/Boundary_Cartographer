import { StatusPill } from '../StatusPill';
import { STATUS_ALLOWED, STATUS_BLOCKED, STATUS_CANDIDATE, STATUS_DISPROVED } from '../../api/types';

// StatusLegend (FE-04): every status is conveyed by color AND line style AND a
// text label — never color alone. Candidate is dashed and labeled as
// unverified.
export function StatusLegend() {
  return (
    <div className="panel" data-testid="status-legend">
      <h2>Legend</h2>
      <ul className="legend-list">
        <li>
          <StatusPill status={STATUS_BLOCKED} /> <span className="legend-line blocked" /> blocked —
          denied by policy
        </li>
        <li>
          <StatusPill status={STATUS_ALLOWED} /> <span className="legend-line allowed" /> allowed —
          passes the policy gate
        </li>
        <li>
          <StatusPill status={STATUS_CANDIDATE} /> <span className="legend-line candidate" />{' '}
          candidate — not verified
        </li>
        <li>
          <StatusPill status={STATUS_DISPROVED} /> <span className="legend-line disproved" />{' '}
          disproved — structurally impossible
        </li>
      </ul>
    </div>
  );
}
