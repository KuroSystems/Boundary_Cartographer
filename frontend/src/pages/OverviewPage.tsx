import { useDemoRun, useScenario } from '../api/useDemoData';
import { STATUS_ALLOWED, STATUS_BLOCKED, STATUS_CANDIDATE, STATUS_DISPROVED } from '../api/types';
import { StatusPill } from '../components/StatusPill';

export function OverviewPage() {
  const scenario = useScenario();
  const run = useDemoRun();

  if (scenario.isLoading || run.isLoading) return <p>Loading…</p>;
  if (scenario.error || run.error) return <p role="alert">Failed to load demo data.</p>;

  const s = run.data!;
  const c = s.summary.counts;

  return (
    <div>
      <div className="panel">
        <h2>{s.summary.headline}</h2>
        <p>
          run <code className="mono">{s.run_id}</code> · scenario{' '}
          <code className="mono">{s.scenario_id}</code> · engine{' '}
          <code className="mono">{s.engine.policy_engine}</code> · deterministic:{' '}
          {String(s.deterministic)}
        </p>
      </div>
      <div className="panel">
        <h2>Path verdicts</h2>
        <div className="counts">
          <span>
            <span className="count">{c.blocked_paths}</span> <StatusPill status={STATUS_BLOCKED} />
          </span>
          <span>
            <span className="count">{c.allowed_paths}</span> <StatusPill status={STATUS_ALLOWED} />
          </span>
          <span>
            <span className="count">{c.candidate_paths}</span>{' '}
            <StatusPill status={STATUS_CANDIDATE} />
          </span>
          <span>
            <span className="count">{c.disproved_paths}</span>{' '}
            <StatusPill status={STATUS_DISPROVED} />
          </span>
        </div>
        <table className="data">
          <thead>
            <tr>
              <th>Path</th>
              <th>Status</th>
              <th>Basis</th>
              <th>Rules</th>
            </tr>
          </thead>
          <tbody>
            {s.paths.map((p) => (
              <tr key={p.path_id}>
                <td className="mono">{p.path_id}</td>
                <td>
                  <StatusPill status={p.status} />
                </td>
                <td className="mono">{p.basis}</td>
                <td className="mono">{p.rule_refs.join(', ') || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="panel">
        <h2>Scenario</h2>
        <p>
          {scenario.data!.name} · {scenario.data!.manifest.tools.length} tools ·{' '}
          {scenario.data!.identities.length} identities · sensitive sinks:{' '}
          {s.summary.sensitive_sinks.join(', ')}
        </p>
      </div>
    </div>
  );
}
