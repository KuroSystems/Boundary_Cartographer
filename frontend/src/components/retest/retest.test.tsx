import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import runFixture from '../../../../contract/fixtures/run.demo.json';
import { parseRunResponse } from '../../api/parse';
import type { Retest, RunResponse } from '../../api/types';
import { RetestCallout } from './RetestCallout';
import { RetestTable } from './RetestTable';

const run = parseRunResponse(runFixture) as RunResponse;

function renderWithRouter(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe('RetestTable (FE-08)', () => {
  it('marks pass per retest; RT-2 shows expected=allowed, actual=allowed', () => {
    renderWithRouter(<RetestTable retests={run.retests} />);
    const rt2 = screen.getByTestId('retest-row-RT-2');
    const cells = within(rt2).getAllByRole('cell');
    expect(cells[2]).toHaveTextContent('allowed'); // expected
    expect(cells[3]).toHaveTextContent('allowed'); // actual
    expect(rt2).toHaveTextContent('PASS');
    for (const r of run.retests) {
      expect(screen.getByTestId(`retest-row-${r.retest_id}`)).toHaveTextContent('PASS');
    }
  });

  it('evidence refs link to the evidence view', () => {
    renderWithRouter(<RetestTable retests={run.retests} />);
    const rt1 = screen.getByTestId('retest-row-RT-1');
    const links = within(rt1).getAllByRole('link');
    expect(links.length).toBeGreaterThan(0);
    for (const link of links) {
      expect(link.getAttribute('href')).toMatch(/^\/evidence#/);
    }
  });

  it('a failing retest (mutated fixture) renders a red, unmistakable FAIL', () => {
    const mutated: Retest[] = run.retests.map((r) =>
      r.retest_id === 'RT-2' ? { ...r, actual: 'blocked', passed: false } : r,
    );
    renderWithRouter(<RetestTable retests={mutated} />);
    const rt2 = screen.getByTestId('retest-row-RT-2');
    const fail = within(rt2).getByRole('alert');
    expect(fail).toHaveTextContent(/FAIL/);
    expect(fail.className).toContain('retest-fail');
    // the other retests still show PASS
    expect(screen.getByTestId('retest-row-RT-1')).toHaveTextContent('PASS');
  });
});

describe('RetestCallout (FE-08)', () => {
  it('shows the green callout linking to the RT-2 evidence record and path P3', () => {
    renderWithRouter(<RetestCallout retests={run.retests} />);
    const callout = screen.getByTestId('retest-callout');
    expect(callout).toHaveTextContent('Legitimate document summarization still allowed');
    expect(callout.className).toContain('retest-callout');
    const links = within(callout).getAllByRole('link');
    const hrefs = links.map((l) => l.getAttribute('href'));
    expect(hrefs.some((h) => h?.startsWith('/evidence#'))).toBe(true);
    expect(hrefs).toContain('/graph');
    expect(callout).toHaveTextContent('path P3');
  });
});
