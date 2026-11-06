import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import runFixture from '../../../../contract/fixtures/run.demo.json';
import { ApiError, type ApiClient } from '../../api/client';
import { parseRunResponse } from '../../api/parse';
import { createQueryClient } from '../../api/queryClient';
import type { RunResponse } from '../../api/types';
import { ApprovalsInner } from '../../views/ApprovalsView';

const run = parseRunResponse(runFixture) as RunResponse;

function stubClient(overrides: Partial<ApiClient>): ApiClient & { calls: string[] } {
  const calls: string[] = [];
  const base: ApiClient = {
    getHealth: async () => ({ status: 'ok', offline: true, policy_engine: 'local-rule-engine@1.0.0' }),
    getScenario: async () => {
      throw new Error('not used');
    },
    createRun: async () => run,
    startRun: async () => run,
    getRun: async () => {
      calls.push('getRun');
      return run;
    },
    decideApproval: async (_runId, req) => {
      calls.push(`decide:${req.decision}`);
      return {
        status: req.decision === 'approve' ? 'approved' : 'rejected',
        items: run.approval.items.map((i) => ({
          ...i,
          status: req.decision === 'approve' ? 'approved' : 'rejected',
          decided_by: req.decided_by ?? null,
          decided_at: '2026-11-06T12:00:00Z',
          note: req.note ?? null,
        })),
      } as never;
    },
  };
  return { ...base, ...overrides, calls };
}

function renderView(client: ApiClient) {
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <MemoryRouter>
        <ApprovalsInner run={run} client={client} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('ApprovalsView (FE-09)', () => {
  it('pending: shows decision buttons, applied:false, and the consequences note', () => {
    renderView(stubClient({}));
    const card = screen.getByTestId('approval-ap-1');
    expect(within(card).getByRole('button', { name: 'Approve' })).toBeInTheDocument();
    expect(within(card).getByRole('button', { name: 'Reject' })).toBeInTheDocument();
    expect(card).toHaveTextContent('applied: false');
    expect(screen.getByTestId('approval-consequences')).toHaveTextContent(
      'No policy was applied and no export was performed',
    );
  });

  it('approve: requires a confirmation step stating nothing executes, then records the decision', async () => {
    const client = stubClient({});
    renderView(client);
    fireEvent.click(screen.getByRole('button', { name: 'Approve' }));
    // confirmation step exists and states nothing executes
    const confirm = await screen.findByTestId('confirm-step');
    expect(confirm).toHaveTextContent(/executes nothing/);
    fireEvent.click(within(confirm).getByRole('button', { name: /confirm/i }));
    const card = await screen.findByTestId('approval-ap-1');
    await waitFor(() => expect(card).toHaveTextContent('approved'));
    expect(card).toHaveTextContent('demo-reviewer');
    expect(card).toHaveTextContent('applied: false');
    expect(card).toHaveTextContent('not applied');
    // the run was NOT refetched as if policy had changed
    expect(client.calls).not.toContain('getRun');
    // paths still shown unchanged
    expect(screen.getByTestId('paths-unchanged')).toHaveTextContent('P1=blocked');
  });

  it('reject: records a rejection through the adapter', async () => {
    const client = stubClient({});
    renderView(client);
    fireEvent.click(screen.getByRole('button', { name: 'Reject' }));
    const card = screen.getByTestId('approval-ap-1');
    await waitFor(() => expect(card).toHaveTextContent('rejected'));
    expect(client.calls).toContain('decide:reject');
    expect(card).toHaveTextContent('applied: false');
  });

  it('conflict: a 409 shows "already decided" and refreshes from source', async () => {
    const approvedRun: RunResponse = {
      ...run,
      approval: {
        status: 'approved',
        items: run.approval.items.map((i) => ({
          ...i,
          status: 'approved' as const,
          decided_by: 'someone-else',
          decided_at: '2026-11-06T11:00:00Z',
        })),
      },
    };
    const client = stubClient({
      decideApproval: async () => {
        throw new ApiError(409, 'APPROVAL_ALREADY_DECIDED', 'approval ap-1 already decided');
      },
      getRun: async () => approvedRun,
    });
    renderView(client);
    fireEvent.click(screen.getByRole('button', { name: 'Reject' }));
    expect(await screen.findByTestId('conflict-note')).toHaveTextContent(/already decided/);
    await waitFor(() =>
      expect(screen.getByTestId('approval-ap-1')).toHaveTextContent('someone-else'),
    );
  });

  it('error: a failed decision is rolled back to pending and shows the error', async () => {
    const client = stubClient({
      decideApproval: async () => {
        throw new ApiError(500, 'UNKNOWN', 'backend exploded');
      },
    });
    renderView(client);
    fireEvent.click(screen.getByRole('button', { name: 'Reject' }));
    expect(await screen.findByTestId('approval-error')).toHaveTextContent('backend exploded');
    // rolled back: still pending with buttons available
    const card = screen.getByTestId('approval-ap-1');
    await waitFor(() =>
      expect(within(card).getByRole('button', { name: 'Reject' })).toBeEnabled(),
    );
    expect(card).toHaveTextContent('pending');
  });
});
