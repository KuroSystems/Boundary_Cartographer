import { useDemoRun } from '../api/useDemoData';

export function GraphPage() {
  const run = useDemoRun();
  if (run.isLoading) return <p>Loading…</p>;
  if (run.error) return <p role="alert">Failed to load run.</p>;
  const g = run.data!.graph;

  return (
    <div>
      <div className="panel">
        <h2>Graph</h2>
        <p>
          {g.nodes.length} nodes · {g.edges.length} edges
        </p>
      </div>
      <div className="panel">
        <h2>Nodes</h2>
        <table className="data">
          <thead>
            <tr>
              <th>ID</th>
              <th>Kind</th>
              <th>Label</th>
              <th>Risk</th>
            </tr>
          </thead>
          <tbody>
            {g.nodes.map((n) => (
              <tr key={n.id}>
                <td className="mono">{n.id}</td>
                <td>{n.kind}</td>
                <td>{n.label}</td>
                <td>{n.risk ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="panel">
        <h2>Edges</h2>
        <table className="data">
          <thead>
            <tr>
              <th>ID</th>
              <th>From</th>
              <th>To</th>
              <th>Kind</th>
              <th>Trust</th>
            </tr>
          </thead>
          <tbody>
            {g.edges.map((e) => (
              <tr key={e.id}>
                <td className="mono">{e.id}</td>
                <td className="mono">{e.from}</td>
                <td className="mono">{e.to}</td>
                <td>{e.kind}</td>
                <td>{e.trust ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
