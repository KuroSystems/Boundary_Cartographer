import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import runFixture from '../../../contract/fixtures/run.demo.json';
import { ApiError, type ApiClient } from '../api/client';
import { parseRunResponse } from '../api/parse';
import { createQueryClient } from '../api/queryClient';
import type { RunResponse } from '../api/types';
import { RunControl } from './RunControl';
import { ScenarioOverview } from '../views/ScenarioOverview';

const parsedRun = parseRunResponse(runFixture) as RunResponse;

function stubClient(overrides: Partial<ApiClient>): ApiClient {
  return {
    getHealth: async () => ({ status: 'ok', offline: true, policy_engine: 'local-rule-engine@1.0.0' }),
    getScenario: async () => {
      const { parseScenarioResponse } = await import('../api/parse');
      const scenarioFixture = (await import('../../../contract/fixtures/demo_scenario.json')).default;
      return parseScenarioResponse(scenarioFixture);
    },
    createRun: async () => parsedRun,
    startRun: async () => parsedRun,
    getRun: async () => parsedRun,
    decideApproval: async () => parsedRun.approval,
    ...overrides,
  };
}

function renderWithProviders(ui: React.ReactElement, route = '/') {
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('RunControl states (FE-03)', () => {
  it('idle: shows the empty state with the Run CTA', () => {
    renderWithProviders(<RunControl client={stubClient({})} />);
    expect(screen.getByTestId('empty-state')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /run analysis/i })).toBeInTheDocument();
  });

  it('loading: clicking Run analysis shows the skeleton, then resolves', async () => {
    let resolveRun!: (r: RunResponse) => void;
    const client = stubClient({
      startRun: () => new Promise<RunResponse>((res) => (resolveRun = res)),
    });
    renderWithProviders(<RunControl client={client} />);
    fireEvent.click(screen.getByRole('button', { name: /run analysis/i }));
    expect(await screen.findByTestId('skeleton')).toBeInTheDocument();
    resolveRun(parsedRun);
    expect(await screen.findByTestId('run-summary')).toBeInTheDocument();
  });

  it('success: shows the run summary with verdict counts', async () => {
    renderWithProviders(<RunControl client={stubClient({})} />);
    fireEvent.click(screen.getByRole('button', { name: /run analysis/i }));
    const summary = await screen.findByTestId('run-summary');
    expect(summary).toHaveTextContent(/blocked/i);
    expect(summary).toHaveTextContent(parsedRun.run_id);
  });

  it('error: adapter rejects with a code shown in a retryable ErrorState', async () => {
    let calls = 0;
    const client = stubClient({
      startRun: async () => {
        calls += 1;
        if (calls === 1) throw new ApiError(400, 'SCENARIO_NOT_FOUND', "scenario 'demo-v9' not found");
        return parsedRun;
      },
    });
    renderWithProviders(<RunControl client={client} />);
    fireEvent.click(screen.getByRole('button', { name: /run analysis/i }));
    const err = await screen.findByTestId('error-state');
    expect(err).toHaveTextContent('SCENARIO_NOT_FOUND');
    // retry succeeds
    fireEvent.click(screen.getByRole('button', { name: /retry/i }));
    expect(await screen.findByTestId('run-summary')).toBeInTheDocument();
  });

  it('empty: after a successful run, Clear returns to the empty state', async () => {
    renderWithProviders(<RunControl client={stubClient({})} />);
    fireEvent.click(screen.getByRole('button', { name: /run analysis/i }));
    await screen.findByTestId('run-summary');
    fireEvent.click(screen.getByRole('button', { name: /clear/i }));
    await waitFor(() => expect(screen.getByTestId('empty-state')).toBeInTheDocument());
  });
});

describe('ScenarioOverview (FE-03)', () => {
  it('displays the frozen scope: 4 tools, 2 identities, 3 rules, 1 doc, 1 sink', async () => {
    renderWithProviders(<ScenarioOverview client={stubClient({})} />);
    const facts = await screen.findByTestId('scenario-facts');
    expect(facts).toHaveTextContent('4 tools');
    expect(facts).toHaveTextContent('2 identities');
    expect(facts).toHaveTextContent('3 rules');
    expect(facts).toHaveTextContent('1 seeded document');
    expect(facts).toHaveTextContent('1 sensitive sink');
    expect(facts).toHaveTextContent('finance.export');
  });

  it('shows the seeded document card with its trust badge', async () => {
    renderWithProviders(<ScenarioOverview client={stubClient({})} />);
    const doc = await screen.findByTestId('seeded-document');
    expect(doc).toHaveTextContent(/trust: untrusted/);
    expect(doc).toHaveTextContent(/content_is_data: true/);
  });
});
