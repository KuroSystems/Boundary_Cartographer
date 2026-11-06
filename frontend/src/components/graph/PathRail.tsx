import { primaryReason } from '../../lib/layout';
import type { Path } from '../../api/types';
import { StatusPill } from '../StatusPill';

// PathRail (FE-04): keyboard-reachable list of paths P1–P5 with status pill +
// primary reason code. Each entry is a real <button> (Tab + Enter/Space).
export function PathRail({
  paths,
  selected,
  onSelect,
}: {
  paths: Path[];
  selected: string | null;
  onSelect: (pathId: string) => void;
}) {
  return (
    <div className="panel" data-testid="path-rail">
      <h2>Paths</h2>
      <ul className="path-rail-list">
        {paths.map((p) => {
          const reason = primaryReason(p);
          return (
            <li key={p.path_id}>
              <button
                type="button"
                className={`path-rail-item${selected === p.path_id ? ' selected' : ''}`}
                aria-pressed={selected === p.path_id}
                onClick={() => onSelect(p.path_id)}
              >
                <span className="mono">{p.path_id}</span>
                <StatusPill status={p.status} />
                <span className="mono reason-code">{reason ? reason.code : '—'}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
