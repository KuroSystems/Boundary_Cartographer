import type { Path } from '../../api/types';
import { StatusPill } from '../StatusPill';
import { primaryReason } from '../../lib/layout';

// PathDetailPanel (FE-04): selected path's hops, rule_refs, reasons (code +
// rule_id + message) and evidence_ids (linked to the evidence view).
export function PathDetailPanel({ path }: { path: Path | null }) {
  if (!path) {
    return (
      <div className="panel" data-testid="path-detail">
        <h2>Path detail</h2>
        <p>Select a path from the rail to inspect its hops and reasons.</p>
      </div>
    );
  }
  const reason = primaryReason(path);
  return (
    <div className="panel" data-testid="path-detail">
      <h2>
        <span className="mono">{path.path_id}</span> <StatusPill status={path.status} />
      </h2>
      {reason && (
        <p>
          Primary reason: <code className="mono">{reason.code}</code> (rule{' '}
          <code className="mono">{reason.rule_id}</code>)
        </p>
      )}
      <p>
        rule_refs: <code className="mono">{path.rule_refs.join(', ') || '—'}</code>
      </p>
      <table className="data">
        <thead>
          <tr>
            <th>Step</th>
            <th>From</th>
            <th>To</th>
            <th>Kind</th>
            <th>Actor</th>
            <th>Purpose</th>
          </tr>
        </thead>
        <tbody>
          {path.hops.map((h) => (
            <tr key={h.step}>
              <td>{h.step}</td>
              <td className="mono">{h.from}</td>
              <td className="mono">{h.to}</td>
              <td>{h.kind}</td>
              <td className="mono">{h.actor}</td>
              <td>{h.purpose}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {path.reasons.length > 0 && (
        <>
          <h3>Reasons</h3>
          <ul>
            {path.reasons.map((r, i) => (
              <li key={i}>
                <code className="mono">{r.code}</code> (rule <code className="mono">{r.rule_id}</code>:{' '}
                {r.message} — evidence:{' '}
                <code className="mono">{r.evidence_ids.join(', ')}</code>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
