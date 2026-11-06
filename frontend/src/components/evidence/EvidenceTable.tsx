import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import type { EvidenceRecord } from '../../api/types';
import { EVIDENCE_KINDS } from '../../api/types';
import { chainIsContinuous } from '../../lib/trace';

// EvidenceTable (FE-10): filterable evidence table — id, kind, source_id, hash
// prefix (full value in tooltip), captured_at, trace links, and the
// prev_hash -> hash chain column.
export function EvidenceTable({
  records,
  selectedId,
  onSelect,
}: {
  records: EvidenceRecord[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const [kindFilter, setKindFilter] = useState<string | null>(null);

  const filtered = useMemo(
    () => (kindFilter ? records.filter((r) => r.kind === kindFilter) : records),
    [records, kindFilter],
  );

  return (
    <div className="panel" data-testid="evidence-table">
      <h2>Evidence ({records.length} records)</h2>
      <div className="filter-chips" role="group" aria-label="Filter evidence by kind">
        <button
          type="button"
          className={`chip filter${kindFilter === null ? ' selected' : ''}`}
          aria-pressed={kindFilter === null}
          onClick={() => setKindFilter(null)}
        >
          all ({records.length})
        </button>
        {EVIDENCE_KINDS.map((k) => {
          const n = records.filter((r) => r.kind === k).length;
          if (n === 0) return null;
          return (
            <button
              key={k}
              type="button"
              className={`chip filter${kindFilter === k ? ' selected' : ''}`}
              aria-pressed={kindFilter === k}
              onClick={() => setKindFilter(k)}
            >
              {k} ({n})
            </button>
          );
        })}
      </div>
      {filtered.length === 0 ? (
        <p data-testid="evidence-empty">No evidence records match the selected filter.</p>
      ) : (
        <table className="data">
          <thead>
            <tr>
              <th scope="col">Evidence ID</th>
              <th scope="col">Kind</th>
              <th scope="col">Source</th>
              <th scope="col">Chain (prev → hash)</th>
              <th scope="col">Captured at</th>
              <th scope="col">Trace</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((r, idx) => (
              <tr key={`${r.evidence_id}-${idx}`}>
                <td>
                  <button
                    type="button"
                    className={`evidence-id mono${selectedId === r.evidence_id ? ' selected' : ''}`}
                    onClick={() => onSelect(r.evidence_id)}
                  >
                    {r.evidence_id}
                  </button>
                </td>
                <td>{r.kind}</td>
                <td className="mono">{r.source_id}</td>
                <td className="mono hash-chain" title={`${r.prev_hash ?? 'null'} → ${r.hash}`}>
                  {(r.prev_hash ?? 'null').slice(0, 15)}… → {r.hash.slice(0, 15)}…
                </td>
                <td className="mono">{r.captured_at}</td>
                <td className="mono">
                  {r.trace.path_ids.map((p) => (
                    <Link key={p} to="/graph" className="source-id-link">
                      {p}
                    </Link>
                  ))}
                  {r.trace.event_ids.map((e) => (
                    <span key={e} className="mono event-ref">
                      {e}
                    </span>
                  ))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p className="mono" style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
        hash chain continuous: {String(chainIsContinuous(records))}
      </p>
    </div>
  );
}
