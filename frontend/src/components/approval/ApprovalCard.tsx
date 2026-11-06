import { useState } from 'react';
import type { ApprovalItem, ApprovalDecisionRequest } from '../../api/types';
import { STATUS_ALLOWED, STATUS_BLOCKED, STATUS_CANDIDATE } from '../../api/types';
import { StatusPill } from '../StatusPill';

// ApprovalCard (FE-09): one queue item — subject, requested_at, note field,
// decision buttons with an approve confirmation step, and the decided state.
// Double-submit is prevented while a decision is in flight.
export function ApprovalCard({
  item,
  deciding,
  onDecide,
}: {
  item: ApprovalItem;
  deciding: boolean;
  onDecide: (req: ApprovalDecisionRequest) => void;
}) {
  const [note, setNote] = useState('');
  const [confirming, setConfirming] = useState(false);
  const decided = item.status !== 'pending';

  const submit = (decision: 'approve' | 'reject') => {
    if (deciding) return; // double-submit guard
    onDecide({ approval_id: item.approval_id, decision, decided_by: 'demo-reviewer', note: note || null });
    setConfirming(false);
  };

  return (
    <div className={`panel approval-card${decided ? ' decided' : ''}`} data-testid={`approval-${item.approval_id}`}>
      <h2>
        <span className="mono">{item.approval_id}</span>{' '}
        <StatusPill
          status={
            item.status === 'approved'
              ? STATUS_ALLOWED
              : item.status === 'rejected'
                ? STATUS_BLOCKED
                : STATUS_CANDIDATE
          }
        />{' '}
        <span className="mono approval-status">{item.status}</span>
      </h2>
      <p>
        Subject: <code className="mono">{item.subject.type}:{item.subject.id}</code> · requested at{' '}
        <code className="mono">{item.requested_at}</code>
      </p>
      <p>
        applied: <code className="mono">{String(item.applied)}</code> · simulated:{' '}
        <code className="mono">{String(item.simulated)}</code>
      </p>

      {decided ? (
        <div className="decided-state">
          <p>
            decided by <code className="mono">{item.decided_by ?? '—'}</code> at{' '}
            <code className="mono">{item.decided_at ?? '—'}</code>
          </p>
          {item.note && <p>note: {item.note}</p>}
          <p className="not-applied">REC-1 is recorded as decided — not applied. Paths and policy are unchanged.</p>
        </div>
      ) : confirming ? (
        <div className="confirm-step" role="alertdialog" aria-label="Confirm approval" data-testid="confirm-step">
          <p>
            Confirm <strong>approve</strong> for {item.approval_id}? Recording this decision executes
            nothing — no policy change, no tool call, no export.
          </p>
          <button type="button" onClick={() => submit('approve')} disabled={deciding}>
            Confirm — record approve
          </button>{' '}
          <button type="button" onClick={() => setConfirming(false)} disabled={deciding}>
            Cancel
          </button>
        </div>
      ) : (
        <div className="pending-actions">
          <label>
            Note (optional):{' '}
            <input
              type="text"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              disabled={deciding}
              placeholder="narrowing looks correct"
            />
          </label>
          <div className="decision-buttons">
            <button type="button" onClick={() => setConfirming(true)} disabled={deciding}>
              Approve
            </button>{' '}
            <button type="button" onClick={() => submit('reject')} disabled={deciding}>
              Reject
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
