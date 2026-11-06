import { useDemoRun } from '../api/useDemoData';
import { DECISION_TO_PILL, STATUS_DISPROVED } from '../api/types';
import { StatusPill } from '../components/StatusPill';

export function ReplayPage() {
  const run = useDemoRun();
  if (run.isLoading) return <p>Loading…</p>;
  if (run.error) return <p role="alert">Failed to load run.</p>;
  const events = run.data!.replay_events;

  return (
    <div className="panel">
      <h2>Replay events ({events.length})</h2>
      <table className="data">
        <thead>
          <tr>
            <th>Event</th>
            <th>Tool</th>
            <th>Actor</th>
            <th>Decision</th>
            <th>Executed</th>
            <th>Rules</th>
          </tr>
        </thead>
        <tbody>
          {events.map((e) => (
            <tr key={`${e.event_id}-${e.tool}`}>
              <td className="mono">{e.event_id}</td>
              <td className="mono">{e.tool}</td>
              <td className="mono">{e.actor}</td>
              <td>
                <StatusPill status={DECISION_TO_PILL[e.decision] ?? STATUS_DISPROVED} />
              </td>
              <td>{String(e.executed)}</td>
              <td className="mono">{e.policy.rule_ids.join(', ') || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
