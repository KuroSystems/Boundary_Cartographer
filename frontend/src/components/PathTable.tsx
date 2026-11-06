import { useMemo, useState } from 'react';
import type { Path, SummaryCounts } from '../api/types';
import {
  STATUS_ALLOWED,
  STATUS_BLOCKED,
  STATUS_CANDIDATE,
  STATUS_DISPROVED,
  type PathStatus,
} from '../api/types';
import { primaryReason } from '../lib/layout';
import { DISPROVED_COPY, reasonCopy } from '../lib/pathCopy';
import { StatusPill } from './StatusPill';

// PathTable (FE-05): filterable, keyboard-accessible path table.
// Filter chips are combinable (multi-toggle); "all" resets. Counts on the
// chips come from summary.counts.

const FILTER_ORDER: PathStatus[] = [
  STATUS_BLOCKED,
  STATUS_ALLOWED,
  STATUS_DISPROVED,
  STATUS_CANDIDATE,
];

const COUNT_KEY: Record<PathStatus, keyof SummaryCounts> = {
  candidate: 'candidate_paths',
  allowed: 'allowed_paths',
  blocked: 'blocked_paths',
  disproved: 'disproved_paths',
};

export function PathTable({
  paths,
  counts,
  selected,
  onSelect,
}: {
  paths: Path[];
  counts: SummaryCounts;
  selected: string | null;
  onSelect: (pathId: string) => void;
}) {
  const [active, setActive] = useState<Set<PathStatus>>(new Set());

  const filtered = useMemo(
    () => (active.size === 0 ? paths : paths.filter((p) => active.has(p.status))),
    [paths, active],
  );

  const toggle = (s: PathStatus) => {
    setActive((prev) => {
      const next = new Set(prev);
      if (next.has(s)) next.delete(s);
      else next.add(s);
      return next;
    });
  };

  const countFor = (s: PathStatus) => counts[COUNT_KEY[s]];

  return (
    <div className="panel" data-testid="path-table">
      <h2>Paths</h2>
      <div className="filter-chips" role="group" aria-label="Filter paths by status">
        <button
          type="button"
          className={`chip filter${active.size === 0 ? ' selected' : ''}`}
          aria-pressed={active.size === 0}
          onClick={() => setActive(new Set())}
        >
          all ({paths.length})
        </button>
        {FILTER_ORDER.map((s) => (
          <button
            key={s}
            type="button"
            className={`chip filter status-${s}${active.has(s) ? ' selected' : ''}`}
            aria-pressed={active.has(s)}
            onClick={() => toggle(s)}
          >
            <StatusPill status={s} /> {countFor(s)}
          </button>
        ))}
      </div>
      <table className="data">
        <thead>
          <tr>
            <th scope="col">Path</th>
            <th scope="col">Origin → sink</th>
            <th scope="col">Stated purpose</th>
            <th scope="col">Taint</th>
            <th scope="col">Status</th>
            <th scope="col">Verification</th>
            <th scope="col">Primary reason</th>
            <th scope="col">Rules</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((p) => {
            const reason = primaryReason(p);
            const isCandidate = p.status === STATUS_CANDIDATE;
            const isDisproved = p.status === STATUS_DISPROVED;
            return (
              <tr
                key={p.path_id}
                tabIndex={0}
                aria-selected={selected === p.path_id}
                className={selected === p.path_id ? 'selected' : ''}
                onClick={() => onSelect(p.path_id)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onSelect(p.path_id);
                  }
                }}
              >
                <td className="mono">{p.path_id}</td>
                <td className="mono">
                  {p.origin} → {p.sink}
                </td>
                <td>{p.stated_purpose ?? '—'}</td>
                <td>{p.tainted ? 'tainted' : 'clean'}</td>
                <td>
                  <StatusPill status={p.status} />
                </td>
                <td>{isCandidate ? 'candidate — not verified' : 'verified by policy'}</td>
                <td className="mono">
                  {isDisproved
                    ? DISPROVED_COPY
                    : reason
                      ? `${reason.code} — ${reasonCopy(reason.code)}`
                      : '—'}
                </td>
                <td className="mono">{p.rule_refs.join(', ') || '—'}</td>
              </tr>
            );
          })}
          {filtered.length === 0 && (
            <tr>
              <td colSpan={8}>No paths match the selected filters.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
