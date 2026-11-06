import { useDemoRun } from '../api/useDemoData';

export function ApprovalsPage() {
  const run = useDemoRun();
  if (run.isLoading) return <p>Loading…</p>;
  if (run.error) return <p role="alert">Failed to load run.</p>;
  const approval = run.data!.approval;

  return (
    <div className="panel">
      <h2>Approval queue — status: {approval.status}</h2>
      <p>
        The queue records decisions only: <code className="mono">applied</code> is always false,{' '}
        <code className="mono">simulated</code> always true. No policy or tool action is performed.
      </p>
      <table className="data">
        <thead>
          <tr>
            <th>ID</th>
            <th>Subject</th>
            <th>Status</th>
            <th>Decided by</th>
            <th>Applied</th>
            <th>Simulated</th>
          </tr>
        </thead>
        <tbody>
          {approval.items.map((item) => (
            <tr key={item.approval_id}>
              <td className="mono">{item.approval_id}</td>
              <td className="mono">
                {item.subject.type}:{item.subject.id}
              </td>
              <td>{item.status}</td>
              <td>{item.decided_by ?? '—'}</td>
              <td>{String(item.applied)}</td>
              <td>{String(item.simulated)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
