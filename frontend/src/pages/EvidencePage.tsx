import { useDemoRun } from '../api/useDemoData';

export function EvidencePage() {
  const run = useDemoRun();
  if (run.isLoading) return <p>Loading…</p>;
  if (run.error) return <p role="alert">Failed to load run.</p>;
  const records = run.data!.evidence;

  return (
    <div className="panel">
      <h2>Evidence chain ({records.length} records, hash-chained)</h2>
      <table className="data">
        <thead>
          <tr>
            <th>Evidence ID</th>
            <th>Kind</th>
            <th>Summary</th>
            <th>Hash</th>
          </tr>
        </thead>
        <tbody>
          {records.map((r, idx) => (
            <tr key={`${r.evidence_id}-${idx}`}>
              <td className="mono">{r.evidence_id}</td>
              <td>{r.kind}</td>
              <td>{r.summary}</td>
              <td className="mono">{r.hash.slice(0, 19)}…</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
