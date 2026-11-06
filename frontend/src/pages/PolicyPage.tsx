import { useDemoRun } from '../api/useDemoData';

export function PolicyPage() {
  const run = useDemoRun();
  if (run.isLoading) return <p>Loading…</p>;
  if (run.error) return <p role="alert">Failed to load run.</p>;
  const d = run.data!.policy_diff;
  const rec = run.data!.recommendation;

  return (
    <div>
      <div className="panel">
        <h2>Policy diff (simulated: {String(d.simulated)})</h2>
        <p className="mono">
          {d.before.policy_id} → {d.after.policy_id}
        </p>
        <table className="data">
          <thead>
            <tr>
              <th>Change</th>
              <th>Op</th>
              <th>Target</th>
              <th>Summary</th>
            </tr>
          </thead>
          <tbody>
            {d.changes.map((c) => (
              <tr key={c.change_id}>
                <td className="mono">{c.change_id}</td>
                <td className="mono">{c.op}</td>
                <td className="mono">{c.target}</td>
                <td>{c.summary}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="panel">
        <h2>Recommendation {rec.recommendation_id}</h2>
        <p className="mono">generated from: {rec.generated_from.join(', ')}</p>
        <table className="data">
          <thead>
            <tr>
              <th>Change</th>
              <th>Op</th>
              <th>Target</th>
            </tr>
          </thead>
          <tbody>
            {rec.changes.map((c) => (
              <tr key={c.change_id}>
                <td className="mono">{c.change_id}</td>
                <td className="mono">{c.op}</td>
                <td className="mono">{c.target}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="panel">
        <h2>Retests</h2>
        <table className="data">
          <thead>
            <tr>
              <th>Retest</th>
              <th>Expected</th>
              <th>Actual</th>
              <th>Passed</th>
            </tr>
          </thead>
          <tbody>
            {run.data!.retests.map((r) => (
              <tr key={r.retest_id}>
                <td className="mono">{r.retest_id}</td>
                <td>{r.expected}</td>
                <td>{r.actual}</td>
                <td>{String(r.passed)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
