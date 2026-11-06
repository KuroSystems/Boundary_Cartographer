import { fireEvent, render, screen, within } from '@testing-library/react';
import runFixture from '../../../contract/fixtures/run.demo.json';
import { parseRunResponse } from '../api/parse';
import type { RunResponse } from '../api/types';
import { DISPROVED_COPY, KNOWN_REASON_CODES, reasonCopy } from '../lib/pathCopy';
import { PathTable } from './PathTable';
import { ReasonList } from './ReasonList';

const run = parseRunResponse(runFixture) as RunResponse;
const { paths, summary } = run;

function renderTable(selected: string | null = null, onSelect: (id: string) => void = () => {}) {
  return render(
    <PathTable paths={paths} counts={summary.counts} selected={selected} onSelect={onSelect} />,
  );
}

function rowIds(): string[] {
  return screen
    .getAllByRole('row')
    .slice(1) // skip header
    .map((r) => within(r).getAllByRole('cell')[0]?.textContent ?? '');
}

describe('PathTable (FE-05)', () => {
  it('renders all five paths by default with accessible header cells', () => {
    renderTable();
    expect(rowIds()).toEqual(['P1', 'P2', 'P3', 'P4', 'P5']);
    for (const th of screen.getAllByRole('columnheader')) {
      expect(th).toHaveAttribute('scope', 'col');
    }
  });

  it('filter chip counts match summary.counts', () => {
    renderTable();
    const group = screen.getByRole('group', { name: /filter paths by status/i });
    expect(within(group).getByRole('button', { name: /all \(5\)/ })).toBeInTheDocument();
    expect(within(group).getByRole('button', { name: /blocked 2/ })).toBeInTheDocument();
    expect(within(group).getByRole('button', { name: /allowed 2/ })).toBeInTheDocument();
    expect(within(group).getByRole('button', { name: /disproved 1/ })).toBeInTheDocument();
    expect(summary.counts).toMatchObject({
      blocked_paths: 2,
      allowed_paths: 2,
      disproved_paths: 1,
    });
  });

  it('filters are accurate and combinable', () => {
    renderTable();
    fireEvent.click(screen.getByRole('button', { name: /blocked 2/ }));
    expect(rowIds()).toEqual(['P1', 'P2']);
    // combine with allowed
    fireEvent.click(screen.getByRole('button', { name: /allowed 2/ }));
    expect(rowIds().sort()).toEqual(['P1', 'P2', 'P3', 'P5']);
    // toggle blocked off -> only allowed remain
    fireEvent.click(screen.getByRole('button', { name: /blocked 2/ }));
    expect(rowIds().sort()).toEqual(['P3', 'P5']);
    // "all" resets
    fireEvent.click(screen.getByRole('button', { name: /all \(5\)/ }));
    expect(rowIds()).toEqual(['P1', 'P2', 'P3', 'P4', 'P5']);
  });

  it('disproved rows say "structurally impossible (no grant)" and never "blocked by policy"', () => {
    renderTable();
    fireEvent.click(screen.getByRole('button', { name: /disproved 1/ }));
    const row = screen.getAllByRole('row')[1];
    expect(row).toHaveTextContent(DISPROVED_COPY);
    expect(row).not.toHaveTextContent(/blocked by policy/i);
    expect(screen.queryByText(/blocked by policy/i)).not.toBeInTheDocument();
  });

  it('rows are selectable with Enter and click', () => {
    const selected: string[] = [];
    renderTable(null, (id) => selected.push(id));
    const row = screen.getAllByRole('row')[1]; // P1
    fireEvent.keyDown(row, { key: 'Enter' });
    fireEvent.click(screen.getAllByRole('row')[3]); // P3
    expect(selected).toEqual(['P1', 'P3']);
  });

  it('shows taint badge, purpose, and candidate-vs-verified semantics', () => {
    renderTable();
    const rows = screen.getAllByRole('row').slice(1);
    const p1 = rows[0];
    expect(p1).toHaveTextContent('tainted');
    expect(p1).toHaveTextContent('verified by policy');
    // no path in the demo run is still an unverified candidate
    expect(screen.queryByText('candidate — not verified')).not.toBeInTheDocument();
  });
});

describe('pathCopy (FE-05)', () => {
  it('every reason code in the fixture has operator copy (exhaustiveness)', () => {
    const fixtureCodes = new Set<string>();
    for (const p of run.paths) for (const r of p.reasons) fixtureCodes.add(r.code);
    for (const e of run.replay_events) for (const r of e.policy.reasons) fixtureCodes.add(r.code);
    expect(fixtureCodes.size).toBeGreaterThan(0);
    for (const code of fixtureCodes) {
      expect(KNOWN_REASON_CODES).toContain(code);
      expect(reasonCopy(code)).not.toMatch(/No operator copy/);
    }
  });

  it('covers all six documented reason codes', () => {
    expect(KNOWN_REASON_CODES.sort()).toEqual(
      [
        'R1_INSTRUCTION_NOT_AUTHORIZATION',
        'R2_CROSS_PURPOSE_FLOW',
        'R3_NO_VALID_APPROVAL',
        'R3_TAINTED_ARGS',
        'R3_WRONG_IDENTITY',
        'R3_WRONG_PURPOSE',
      ].sort(),
    );
  });
});

describe('ReasonList (FE-05)', () => {
  it('renders human-readable copy for each reason of the selected path', () => {
    const p1 = paths.find((p) => p.path_id === 'P1')!;
    render(<ReasonList path={p1} />);
    const list = screen.getByTestId('reason-list');
    for (const r of p1.reasons) {
      expect(list).toHaveTextContent(r.code);
      expect(list).toHaveTextContent(reasonCopy(r.code));
    }
  });
});
