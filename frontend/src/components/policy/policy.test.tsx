import { render, screen, within } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import runFixture from '../../../../contract/fixtures/run.demo.json';
import scenarioFixture from '../../../../contract/fixtures/demo_scenario.json';
import { parseRunResponse, parseScenarioResponse } from '../../api/parse';
import { createQueryClient } from '../../api/queryClient';
import type { RunResponse, ScenarioResponse } from '../../api/types';
import { PolicyDiff } from './PolicyDiff';
import { RecommendationCard } from './RecommendationCard';
import { GrantMatrix } from './GrantMatrix';
import { RetestTable } from '../retest/RetestTable';
import { PolicyView } from '../../views/PolicyView';

const run = parseRunResponse(runFixture) as RunResponse;
const scenario = parseScenarioResponse(scenarioFixture) as ScenarioResponse;

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('PolicyDiff (FE-07)', () => {
  it('renders before/after rule ids and grants with op badges', () => {
    renderWithProviders(<PolicyDiff diff={run.policy_diff} />);
    const before = screen.getByTestId('diff-before');
    const after = screen.getByTestId('diff-after');
    expect(before).toHaveTextContent('demo-policy-v1');
    expect(after).toHaveTextContent('demo-policy-v2-simulated');
    for (const rid of ['R1', 'R2', 'R3']) {
      expect(before).toHaveTextContent(rid);
      expect(after).toHaveTextContent(rid);
    }
    // grants side by side; the revoked over-grant is marked changed in before
    expect(before).toHaveTextContent('document_assistant:finance.lookup');
    expect(after).not.toHaveTextContent('document_assistant:finance.lookup');
    for (const op of ['revoke_grant', 'add_guard', 'drop_inheritance']) {
      expect(screen.getAllByText(op).length).toBeGreaterThan(0);
    }
  });

  it('simulated:true renders a persistent, non-dismissible SIMULATED banner', () => {
    renderWithProviders(<PolicyDiff diff={run.policy_diff} />);
    const banner = screen.getByTestId('simulated-banner');
    expect(banner).toHaveTextContent('SIMULATED — not applied');
    // persistent + non-dismissible: no button inside or nearby
    expect(within(banner).queryByRole('button')).toBeNull();
    expect(within(banner.parentElement as HTMLElement).queryByRole('button', { name: /dismiss/i })).toBeNull();
  });
});

describe('RecommendationCard (FE-07)', () => {
  it('lists C1–C3 with rule refs, expected effect, and risk_if_unchanged', () => {
    renderWithProviders(<RecommendationCard rec={run.recommendation} />);
    const card = screen.getByTestId('recommendation-card');
    for (const cid of ['C1', 'C2', 'C3']) {
      expect(within(card).getByText(cid)).toBeInTheDocument();
    }
    expect(card).toHaveTextContent(run.recommendation.risk_if_unchanged);
    expect(card).toHaveTextContent('R1');
    // expected_effect entries link to the graph view
    const links = within(card).getAllByRole('link');
    expect(links.some((l) => l.getAttribute('href') === '/graph')).toBe(true);
  });
});

describe('RetestTable (FE-07/FE-08)', () => {
  it('proves RT-1 blocked and RT-2 allowed side by side', () => {
    renderWithProviders(<RetestTable retests={run.retests} />);
    const rt1 = screen.getByTestId('retest-row-RT-1');
    const rt2 = screen.getByTestId('retest-row-RT-2');
    expect(rt1).toHaveTextContent('blocked');
    expect(rt2).toHaveTextContent('allowed');
    expect(rt1).toHaveTextContent('PASS');
    expect(rt2).toHaveTextContent('PASS');
  });
});

describe('GrantMatrix (FE-07)', () => {
  it('flags the over-grant cell the recommendation revokes', () => {
    renderWithProviders(
      <GrantMatrix scenario={scenario} flagged={['document_assistant:finance.lookup']} />,
    );
    const matrix = screen.getByTestId('grant-matrix');
    expect(matrix).toHaveTextContent('over-grant');
    expect(matrix).toHaveTextContent('finance:lookup_public');
  });
});

describe('PolicyView (FE-07) — no apply affordance', () => {
  it('renders the full view and contains no apply button anywhere', async () => {
    renderWithProviders(<PolicyView />);
    expect(await screen.findByTestId('policy-diff')).toBeInTheDocument();
    expect(screen.getByTestId('recommendation-card')).toBeInTheDocument();
    expect(screen.getByTestId('retest-table')).toBeInTheDocument();
    expect(screen.getByTestId('retest-callout')).toBeInTheDocument();
    expect(screen.getByTestId('rule-list')).toBeInTheDocument();
    expect(screen.getByTestId('grant-matrix')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /apply/i })).toBeNull();
    expect(screen.queryByText(/^apply$/i)).toBeNull();
  });
});
