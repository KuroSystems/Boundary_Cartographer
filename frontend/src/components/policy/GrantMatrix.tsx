import type { ScenarioResponse } from '../../api/types';

// GrantMatrix (FE-07): read-only identity × tool matrix from the scenario.
// Cells flagged via `flagged` (e.g. the vestigial over-grant the
// recommendation revokes) are highlighted — the app never edits this matrix.
export function GrantMatrix({
  scenario,
  flagged = [],
}: {
  scenario: ScenarioResponse;
  flagged?: string[];
}) {
  const tools = scenario.manifest.tools.map((t) => t.name);
  const identities = scenario.identities.map((i) => i.id);
  const cell = new Map<string, string[]>();
  for (const g of scenario.grants) {
    const key = `${g.identity}::${g.tool}`;
    cell.set(key, [...(cell.get(key) ?? []), ...g.scopes]);
  }

  return (
    <div className="panel" data-testid="grant-matrix">
      <h2>Grant matrix (read-only)</h2>
      <table className="data">
        <thead>
          <tr>
            <th scope="col">Identity \ Tool</th>
            {tools.map((t) => (
              <th scope="col" key={t} className="mono">
                {t}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {identities.map((id) => (
            <tr key={id}>
              <th scope="row" className="mono">
                {id}
              </th>
              {tools.map((t) => {
                const scopes = cell.get(`${id}::${t}`);
                const isFlagged = flagged.includes(`${id}:${t}`);
                return (
                  <td
                    key={t}
                    className={`mono grant-cell${scopes ? '' : ' grant-none'}${isFlagged ? ' grant-flagged' : ''}`}
                    title={isFlagged ? 'over-grant — flagged by the recommendation' : undefined}
                  >
                    {scopes ? scopes.join(', ') : '—'}
                    {isFlagged && <span className="grant-flag"> over-grant</span>}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
