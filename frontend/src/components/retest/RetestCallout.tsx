import { Link } from 'react-router-dom';
import type { Retest } from '../../api/types';

// RetestCallout (FE-08): green callout proving the legitimate workflow still
// passes — links to the RT-2 evidence record and to path P3 on the graph.
export function RetestCallout({ retests }: { retests: Retest[] }) {
  const rt2 = retests.find((r) => r.retest_id === 'RT-2');
  if (!rt2) return null;
  const evidenceId = rt2.evidence_ids[0];
  return (
    <div className="retest-callout" role="note" data-testid="retest-callout">
      <strong>Legitimate document summarization still allowed.</strong> RT-2 expected{' '}
      {rt2.expected}, actual {rt2.actual} — see{' '}
      {evidenceId && (
        <Link to={`/evidence#${encodeURIComponent(evidenceId)}`} className="mono">
          evidence {evidenceId}
        </Link>
      )}{' '}
      and <Link to="/graph">path P3</Link> on the graph.
    </div>
  );
}
