import { Link } from 'react-router-dom';
import type { PolicyDiff as PolicyDiffT } from '../../api/types';
import { STATUS_BLOCKED } from '../../api/types';
import { StatusPill } from '../StatusPill';

// PolicyDiff (FE-07): before/after snapshots side by side with op badges and
// changed-entry highlighting. The SIMULATED banner is persistent and
// non-dismissible — this view has no apply affordance at all.

function Snapshot({ label, snap, changedTargets }: {
  label: string;
  snap: PolicyDiffT['before'];
  changedTargets: Set<string>;
}) {
  return (
    <div className="diff-side" data-testid={`diff-${label}`}>
      <h3 className="mono">{snap.policy_id}</h3>
      <h4>Rules</h4>
      <ul>
        {snap.rules.map((r) => (
          <li key={r.id} className="mono">
            {r.id} — <span className="diff-summary">{r.summary}</span>
          </li>
        ))}
      </ul>
      <h4>Grants</h4>
      <ul>
        {snap.grants.map((g) => {
          const key = `${g.identity}:${g.tool}`;
          const changed = changedTargets.has(key);
          return (
            <li key={key} className={`mono${changed ? ' diff-changed' : ''}`}>
              {key} <span className="diff-scopes">{g.scopes.join(', ')}</span>
              {changed && <span className="diff-marker"> changed</span>}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function PolicyDiff({ diff }: { diff: PolicyDiffT }) {
  const changedTargets = new Set(
    diff.changes.map((c) => (c.target.includes(':') ? c.target : '')).filter(Boolean),
  );
  return (
    <div className="panel" data-testid="policy-diff">
      <h2>Policy diff</h2>
      {diff.simulated && (
        <p className="simulated-banner" role="note" data-testid="simulated-banner">
          SIMULATED — not applied. This diff is computed in memory; no policy was changed.
        </p>
      )}
      <div className="diff-grid">
        <Snapshot label="before" snap={diff.before} changedTargets={changedTargets} />
        <Snapshot label="after" snap={diff.after} changedTargets={changedTargets} />
      </div>
      <h3>Changes</h3>
      <table className="data">
        <thead>
          <tr>
            <th scope="col">Op</th>
            <th scope="col">Target</th>
            <th scope="col">Rule</th>
            <th scope="col">Summary</th>
          </tr>
        </thead>
        <tbody>
          {diff.changes.map((c) => (
            <tr key={`${c.op}-${c.target}`}>
              <td>
                <span className={`op-badge op-${c.op}`}>{c.op}</span>
              </td>
              <td className="mono">
                <Link to="/graph">{c.target}</Link>
              </td>
              <td className="mono">{c.rule_id}</td>
              <td>{c.summary}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p style={{ color: 'var(--text-dim)', fontSize: '0.8rem' }}>
        status: <StatusPill status={STATUS_BLOCKED} /> nothing here is applied — approval only records a
        decision
      </p>
    </div>
  );
}
