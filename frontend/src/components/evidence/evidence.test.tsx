import { fireEvent, render, screen, within } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import runFixture from '../../../../contract/fixtures/run.demo.json';
import { parseRunResponse } from '../../api/parse';
import { createQueryClient } from '../../api/queryClient';
import type { RunResponse } from '../../api/types';
import { chainIsContinuous, unresolvedEvidenceRefs } from '../../lib/trace';
import { EvidenceTable } from './EvidenceTable';
import { EvidenceView } from '../../views/EvidenceView';

const run = parseRunResponse(runFixture) as RunResponse;

function renderWithProviders(ui: React.ReactElement, route = '/evidence') {
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('EvidenceView (FE-10)', () => {
  it('opens the drawer when the URL hash references an evidence id (e.g. from a path reason)', async () => {
    renderWithProviders(<EvidenceView />, '/evidence#src:doc-untrusted-001');
    const drawer = await screen.findByTestId('evidence-drawer');
    expect(within(drawer).getByRole('heading', { name: 'src:doc-untrusted-001' })).toBeInTheDocument();
    const hash = within(drawer).getByTestId('drawer-hash');
    expect(hash.textContent).toMatch(/^sha256:[0-9a-f]{64}$/);
    // trace links present
    expect(within(drawer).getAllByRole('link').length).toBeGreaterThan(0);
  });

  it('clicking an evidence id in the table opens the drawer with full hash', async () => {
    renderWithProviders(<EvidenceView />);
    const table = await screen.findByTestId('evidence-table');
    const btn = within(table).getByRole('button', { name: 'src:manifest' });
    fireEvent.click(btn);
    const drawer = await screen.findByTestId('evidence-drawer');
    expect(drawer).toHaveTextContent('src:manifest');
    expect(within(drawer).getByTestId('drawer-hash').textContent).toMatch(/^sha256:/);
  });

  it('filters by kind accurately and shows an empty state when nothing matches', async () => {
    renderWithProviders(<EvidenceView />);
    const table = await screen.findByTestId('evidence-table');
    fireEvent.click(within(table).getByRole('button', { name: /^event \(/ }));
    const rows = within(table).getAllByRole('row').slice(1);
    expect(rows.length).toBeGreaterThan(0);
    for (const row of rows) expect(row).toHaveTextContent('event');
    // empty state: no records at all
    render(<EvidenceTable records={[]} selectedId={null} onSelect={() => {}} />);
    expect(screen.getByTestId('evidence-empty')).toBeInTheDocument();
  });

  it('shows hash-chain continuity (prev_hash -> hash) over the fixture', async () => {
    renderWithProviders(<EvidenceView />);
    const table = await screen.findByTestId('evidence-table');
    expect(table).toHaveTextContent('hash chain continuous: true');
    expect(chainIsContinuous(run.evidence)).toBe(true);
    expect(run.evidence[0].prev_hash).toBeNull();
    for (let i = 1; i < run.evidence.length; i++) {
      expect(run.evidence[i].prev_hash).toBe(run.evidence[i - 1].hash);
    }
  });
});

describe('traceability (FE-10)', () => {
  it('every evidence_id referenced in paths[].reasons[] and replay_events[] resolves', () => {
    expect(unresolvedEvidenceRefs(run)).toEqual([]);
  });
});
