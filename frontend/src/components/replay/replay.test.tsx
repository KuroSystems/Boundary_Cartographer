import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import runFixture from '../../../../contract/fixtures/run.demo.json';
import { parseRunResponse } from '../../api/parse';
import type { ReplayEvent, RunResponse } from '../../api/types';
import { EventTimeline } from './EventTimeline';
import { UntrustedDocument } from './UntrustedDocument';

const run = parseRunResponse(runFixture) as RunResponse;

function renderWithRouter(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe('UntrustedDocument (FE-06) — safe text rendering', () => {
  it('renders injected markup as escaped text: no script/img elements, no innerHTML', () => {
    const evil = '<script>alert(1)</script><img src=x onerror=alert(2)>INJECTION';
    const { container } = renderWithRouter(
      <UntrustedDocument title="evil doc" content={evil} trustLevel="untrusted" />,
    );
    expect(container.querySelector('script')).toBeNull();
    expect(container.querySelector('img')).toBeNull();
    const pre = screen.getByTestId('untrusted-pre');
    expect(pre.tagName).toBe('PRE');
    // the raw string is present as a text node, not parsed as markup
    expect(pre.textContent).toBe(evil);
    expect(pre.innerHTML).not.toContain('<script>');
    expect(screen.getByRole('note')).toHaveTextContent('UNTRUSTED DATA — NOT INSTRUCTIONS');
  });

  it('the seeded fixture document renders only inside the <pre>', () => {
    const doc = JSON.parse(
      readFileSync(join(__dirname, '../../../../contract/fixtures/demo_scenario.json'), 'utf-8'),
    );
    const { container } = renderWithRouter(
      <UntrustedDocument title={doc.document.title} content={doc.document.content} trustLevel="untrusted" />,
    );
    const pres = container.querySelectorAll('pre');
    expect(pres).toHaveLength(1);
    expect(pres[0].textContent).toBe(doc.document.content);
  });
});

describe('EventTimeline (FE-06)', () => {
  it('blocked styling: "not run — blocked by policy" with rule ids, unmistakable', () => {
    renderWithRouter(<EventTimeline events={run.replay_events} />);
    const timeline = screen.getByTestId('event-timeline');
    const notes = within(timeline).getAllByRole('note');
    const blockedNote = notes.find((n) => /not run — blocked by policy/.test(n.textContent ?? ''));
    expect(blockedNote).toBeDefined();
    expect(blockedNote!.textContent).toMatch(/R\d/);
  });

  it('allowed event renders as allowed; finance.export with a mock result shows SIMULATED', () => {
    const exportAllowed: ReplayEvent = {
      ...run.replay_events.find((e) => e.tool === 'finance.export' && e.decision === 'allowed')!,
      tool_result: { content: [{ type: 'text', text: 'mock' }] },
    };
    renderWithRouter(<EventTimeline events={[exportAllowed]} />);
    expect(screen.getByText('SIMULATED')).toBeInTheDocument();
    expect(screen.getByRole('note')).toHaveTextContent(/allowed by policy/);
  });

  it('events render in seq order', () => {
    const shuffled = [...run.replay_events].reverse();
    renderWithRouter(<EventTimeline events={shuffled} />);
    const items = screen.getAllByRole('listitem');
    const seqs = items.map((li) => Number(li.querySelector('.mono')?.textContent?.replace('#', '')));
    expect(seqs).toEqual([...seqs].sort((a, b) => a - b));
  });

  it('empty timeline renders an explicit empty state', () => {
    renderWithRouter(<EventTimeline events={[]} />);
    expect(screen.getByTestId('event-timeline')).toHaveTextContent('No replay events.');
  });
});

describe('repo-wide no-danger guard (FE-06)', () => {
  it('zero dangerouslySetInnerHTML uses in src', () => {
    const SRC = join(__dirname, '..', '..');
    function* walk(dir: string): Generator<string> {
      for (const entry of readdirSync(dir)) {
        const full = join(dir, entry);
        if (statSync(full).isDirectory()) yield* walk(full);
        else if (/\.tsx?$/.test(entry) && !/\.test\.tsx?$/.test(entry)) yield full;
      }
    }
    const offenders: string[] = [];
    for (const file of walk(SRC)) {
      if (readFileSync(file, 'utf-8').includes('dangerouslySetInnerHTML')) {
        offenders.push(relative(SRC, file));
      }
    }
    expect(offenders).toEqual([]);
  });
});
