import type { ScenarioResponse } from '../../api/types';

// RuleList (FE-07): R1–R3 with name, summary, and the verifier reason codes
// each rule can emit.
export function RuleList({ scenario }: { scenario: ScenarioResponse }) {
  return (
    <div className="panel" data-testid="rule-list">
      <h2>Policy rules ({scenario.policy.rules.length})</h2>
      <table className="data">
        <thead>
          <tr>
            <th scope="col">Rule</th>
            <th scope="col">Name</th>
            <th scope="col">Summary</th>
            <th scope="col">Reason codes</th>
          </tr>
        </thead>
        <tbody>
          {scenario.policy.rules.map((r) => (
            <tr key={r.id}>
              <td className="mono">{r.id}</td>
              <td>{r.name}</td>
              <td>{r.summary}</td>
              <td className="mono">{(r.reason_codes ?? []).join(', ') || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
