import { ScenarioOverview } from '../views/ScenarioOverview';
import { useDemoRun } from '../api/useDemoData';
import { StatusPill } from '../components/StatusPill';

// Overview route (FE-01/FE-03): scenario overview + run control on top, the
// latest fixture run's path verdicts below.
export function OverviewPage() {
  const run = useDemoRun();

  return (
    <div>
      <ScenarioOverview />
      {run.data && (
        <div className="panel">
          <h2>Path verdicts</h2>
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
              {run.data.paths.map((p) => (
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
      )}
    </div>
  );
}
