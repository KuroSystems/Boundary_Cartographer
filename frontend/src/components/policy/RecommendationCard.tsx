import { Link } from 'react-router-dom';
import type { Recommendation } from '../../api/types';

// RecommendationCard (FE-07): REC-1 with its C1–C3 changes, rule refs,
// expected_effect (linked to the graph) and risk_if_unchanged.
export function RecommendationCard({ rec }: { rec: Recommendation }) {
  return (
    <div className="panel" data-testid="recommendation-card">
      <h2>
        Recommendation <span className="mono">{rec.recommendation_id}</span>
      </h2>
      <p>{rec.title}</p>
      <p className="mono" style={{ color: 'var(--text-dim)' }}>
        generated from: {rec.generated_from.join(', ')}
      </p>
      <table className="data">
        <thead>
          <tr>
            <th scope="col">Change</th>
            <th scope="col">Op</th>
            <th scope="col">Target</th>
            <th scope="col">Rule refs</th>
          </tr>
        </thead>
        <tbody>
          {rec.changes.map((c) => (
            <tr key={c.change_id}>
              <td className="mono">{c.change_id}</td>
              <td>
                <span className={`op-badge op-${c.op}`}>{c.op}</span>
              </td>
              <td className="mono">
                <Link to="/graph">{c.target}</Link>
              </td>
              <td className="mono">{c.rule_refs.join(', ')}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <h3>Expected effect</h3>
      <ul>
        {Object.entries(rec.expected_effect).map(([pathId, status]) => (
          <li key={pathId}>
            <Link to="/graph" className="mono">
              {pathId}
            </Link>{' '}
            → {status}
          </li>
        ))}
      </ul>
      <p className="risk-if-unchanged">
        <strong>Risk if unchanged:</strong> {rec.risk_if_unchanged}
      </p>
    </div>
  );
}
