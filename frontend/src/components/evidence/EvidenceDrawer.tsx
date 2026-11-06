import { Link } from 'react-router-dom';
import type { EvidenceRecord } from '../../api/types';

// EvidenceDrawer (FE-10): side panel opened from a path reason / replay event
// evidence reference — full hash, prev_hash, and trace links.
export function EvidenceDrawer({
  record,
  onClose,
}: {
  record: EvidenceRecord | null;
  onClose: () => void;
}) {
  if (!record) return null;
  return (
    <aside className="evidence-drawer" data-testid="evidence-drawer" aria-label="Evidence detail">
      <button type="button" className="drawer-close" onClick={onClose} aria-label="Close evidence drawer">
        ✕
      </button>
      <h2 className="mono">{record.evidence_id}</h2>
      <p>
        kind: {record.kind} · source: <code className="mono">{record.source_id}</code>
      </p>
      <p>{record.summary}</p>
      <p>
        captured at <code className="mono">{record.captured_at}</code>
      </p>
      <p>
        hash: <code className="mono hash-full" data-testid="drawer-hash">{record.hash}</code>
      </p>
      <p>
        prev_hash: <code className="mono">{record.prev_hash ?? 'null'}</code>
      </p>
      <h3>Trace</h3>
      <ul>
        {record.trace.path_ids.map((p) => (
          <li key={p}>
            path <Link to="/graph" className="mono">{p}</Link>
          </li>
        ))}
        {record.trace.event_ids.map((e) => (
          <li key={e}>
            event <code className="mono">{e}</code>
          </li>
        ))}
      </ul>
    </aside>
  );
}
