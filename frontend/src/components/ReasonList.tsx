import type { Path } from '../api/types';
import { reasonCopy } from '../lib/pathCopy';

// ReasonList (FE-05): a path's reasons with operator-readable copy per code.
export function ReasonList({ path }: { path: Path | null }) {
  if (!path) return null;
  if (path.reasons.length === 0) {
    return (
      <div className="panel" data-testid="reason-list">
        <h2>Reasons</h2>
        <p>No policy reasons — this path was not verified as blocked.</p>
      </div>
    );
  }
  return (
    <div className="panel" data-testid="reason-list">
      <h2>
        Reasons for <span className="mono">{path.path_id}</span>
      </h2>
      <ul>
        {path.reasons.map((r, i) => (
          <li key={i}>
            <code className="mono">{r.code}</code> (rule <code className="mono">{r.rule_id}</code>){' '}
            — {reasonCopy(r.code)}
          </li>
        ))}
      </ul>
    </div>
  );
}
