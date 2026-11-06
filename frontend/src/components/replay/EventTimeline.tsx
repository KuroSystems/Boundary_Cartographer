import type { ReplayEvent } from '../../api/types';
import { DECISION_ALLOWED, DECISION_BLOCKED, DECISION_TO_PILL, STATUS_ALLOWED } from '../../api/types';
import { StatusPill } from '../StatusPill';
import { SourceIdLink } from '../SourceIdLink';
import { PolicyVerdict } from './PolicyVerdict';

// EventTimeline (FE-06): replay events in seq order. A blocked, unexecuted
// event is unmistakable ("not run — blocked by policy R2, R3"); finance.export
// with a mock result is badged SIMULATED (never actually run).
export function EventTimeline({ events }: { events: ReplayEvent[] }) {
  if (events.length === 0) {
    return (
      <div className="panel" data-testid="event-timeline">
        <h2>Replay events</h2>
        <p>No replay events.</p>
      </div>
    );
  }
  const sorted = [...events].sort((a, b) => a.seq - b.seq);
  return (
    <div className="panel" data-testid="event-timeline">
      <h2>Replay events ({events.length})</h2>
      <ol className="event-timeline-list">
        {sorted.map((e) => {
          const blockedNotRun = e.decision === DECISION_BLOCKED && e.executed === false;
          const simulated = e.tool === 'finance.export' && e.tool_result != null;
          return (
            <li key={`${e.event_id}-${e.seq}`} className={`event event-${DECISION_TO_PILL[e.decision] ?? STATUS_ALLOWED}`}>
              <div className="event-head">
                <span className="mono">#{e.seq}</span>
                <span className="mono event-tool">{e.tool}</span>
                <StatusPill status={DECISION_TO_PILL[e.decision] ?? STATUS_ALLOWED} />
                <span className="chip">trust: {e.trust_level}</span>
                <span className="mono event-actor">{e.actor}</span>
                <span className="mono event-purpose">{e.purpose}</span>
                {simulated && <span className="chip simulated">SIMULATED</span>}
              </div>
              {blockedNotRun && (
                <p className="event-blocked-note" role="note">
                  not run — blocked by policy {e.policy.rule_ids.join(', ') || '(no rule ids)'}
                </p>
              )}
              {e.decision === DECISION_ALLOWED && (
                <p className="event-allowed-note" role="note">
                  allowed by policy{e.executed ? '' : ' (simulated — not executed)'}
                </p>
              )}
              <p className="mono event-preview">{e.input_preview}</p>
              <PolicyVerdict verdict={e.policy} />
              <p className="event-sources">
                sources:{' '}
                {e.source_ids.map((s) => (
                  <SourceIdLink key={s} id={s} />
                ))}
              </p>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
