// ScenarioOverview (FE-03): scenario facts asserted + displayed (exactly 4
// tools, 2 identities, 3 rules, one seeded untrusted document, one sensitive
// sink), seeded document card with trust badge, and the run control.

import type { ApiClient } from '../api/client';
import { apiClient } from '../api/selectClient';
import { useScenario } from '../api/useDemoData';
import { RunControl } from '../components/RunControl';
import { ErrorState } from '../components/ErrorState';
import { Skeleton } from '../components/Skeleton';
import { StatusPill } from '../components/StatusPill';
import { STATUS_BLOCKED } from '../api/types';

export const EXPECTED = { tools: 4, identities: 2, rules: 3, documents: 1, sinks: 1 };

export function ScenarioOverview({ client = apiClient }: { client?: ApiClient }) {
  const scenario = useScenario();

  if (scenario.isLoading) return <Skeleton label="Loading scenario…" />;
  if (scenario.error || !scenario.data) {
    return (
      <ErrorState
        code="SCENARIO_UNAVAILABLE"
        message={scenario.error instanceof Error ? scenario.error.message : 'unknown error'}
      />
    );
  }

  const s = scenario.data;
  const scopeOk =
    s.manifest.tools.length === EXPECTED.tools &&
    s.identities.length === EXPECTED.identities &&
    s.policy.rules.length === EXPECTED.rules &&
    s.sensitive_sinks.length === EXPECTED.sinks;
  if (!scopeOk) {
    return (
      <ErrorState
        code="SCOPE_FREEZE_VIOLATION"
        message="scenario no longer matches the frozen scope (4 tools / 2 identities / 3 rules / 1 sink)"
      />
    );
  }

  const doc = s.document;
  const sink = s.sensitive_sinks[0];

  return (
    <div>
      <div className="panel" data-testid="scenario-facts">
        <h2>{s.name}</h2>
        <p className="mono">scenario: {s.scenario_id}</p>
        <div className="counts">
          <span>
            <span className="count">{s.manifest.tools.length}</span> tools
          </span>
          <span>
            <span className="count">{s.identities.length}</span> identities
          </span>
          <span>
            <span className="count">{s.policy.rules.length}</span> rules (
            {s.policy.rules.map((r) => r.id).join(', ')})
          </span>
          <span>
            <span className="count">{EXPECTED.documents}</span> seeded document
          </span>
          <span>
            <span className="count">{s.sensitive_sinks.length}</span> sensitive sink:{' '}
            <StatusPill status={STATUS_BLOCKED} /> <code className="mono">{sink}</code>
          </span>
        </div>
      </div>

      <div className="panel" data-testid="seeded-document">
        <h2>Seeded document</h2>
        <p>
          <strong>{doc.title}</strong>{' '}
          <span className="chip fixture">trust: {doc.trust_level}</span>{' '}
          <span className="chip offline">content_is_data: {String(doc.content_is_data)}</span>
        </p>
        <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem' }}>
          Document content is data only — never instructions, never rendered as HTML.
        </p>
      </div>

      <RunControl client={client} />
    </div>
  );
}
