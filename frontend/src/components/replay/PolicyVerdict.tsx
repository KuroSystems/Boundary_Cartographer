import type { ReplayPolicyVerdict } from '../../api/types';
import { reasonCopy } from '../../lib/pathCopy';

// PolicyVerdict (FE-06): the verifier's verdict — rule IDs + reason codes with
// operator copy. Verifier-derived codes only; no LLM/typed prose is rendered.
export function PolicyVerdict({ verdict }: { verdict: ReplayPolicyVerdict }) {
  return (
    <div className="policy-verdict" data-testid="policy-verdict">
      <span className={`verdict-chip verdict-${verdict.decision}`}>
        policy: {verdict.decision}
      </span>
      {verdict.rule_ids.length > 0 && (
        <span className="mono">rules: {verdict.rule_ids.join(', ')}</span>
      )}
      {verdict.reasons.length > 0 && (
        <ul className="verdict-reasons">
          {verdict.reasons.map((r, i) => (
            <li key={i}>
              <code className="mono">{r.code}</code> — {reasonCopy(r.code)}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
