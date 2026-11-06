import { useState } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import runFixture from '../../../../contract/fixtures/run.demo.json';
import { parseRunResponse } from '../../api/parse';
import { createQueryClient } from '../../api/queryClient';
import type { RunResponse } from '../../api/types';
import { buildFlowElements, layoutGraph, primaryReason } from '../../lib/layout';
import { PathRail } from './PathRail';
import { PathDetailPanel } from './PathDetailPanel';
import { ToolNode } from './PathGraph';
import { StatusLegend } from './StatusLegend';
import { GraphView } from '../../views/GraphView';

const run = parseRunResponse(runFixture) as RunResponse;
const paths = run.paths;

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('layout (FE-04)', () => {
  it('is deterministic: two calls produce identical positions', () => {
    const a = layoutGraph(run.graph);
    const b = layoutGraph(run.graph);
    expect(Object.fromEntries(a)).toEqual(Object.fromEntries(b));
  });

  it('matches a snapshot of node positions (stable across reloads)', () => {
    const positions = Object.fromEntries(layoutGraph(run.graph));
    expect(positions).toMatchInlineSnapshot(`
      {
        "data_scope:docs:read_untrusted": {
          "x": 660,
          "y": 0,
        },
        "data_scope:docs:summarize": {
          "x": 660,
          "y": 90,
        },
        "data_scope:finance:export": {
          "x": 660,
          "y": 180,
        },
        "data_scope:finance:lookup": {
          "x": 660,
          "y": 270,
        },
        "data_scope:finance:lookup_public": {
          "x": 660,
          "y": 360,
        },
        "identity:document_assistant": {
          "x": 220,
          "y": 0,
        },
        "identity:finance_analyst": {
          "x": 220,
          "y": 90,
        },
        "output:export_report": {
          "x": 880,
          "y": 0,
        },
        "output:summary": {
          "x": 880,
          "y": 90,
        },
        "source:doc-untrusted-001": {
          "x": 0,
          "y": 0,
        },
        "tool:document.read": {
          "x": 440,
          "y": 0,
        },
        "tool:document.summarize": {
          "x": 440,
          "y": 90,
        },
        "tool:finance.export": {
          "x": 440,
          "y": 180,
        },
        "tool:finance.lookup": {
          "x": 440,
          "y": 270,
        },
      }
    `);
  });
});

describe('buildFlowElements (FE-04)', () => {
  it('builds one flow node per graph node with a custom type and aria data', () => {
    const { nodes, edges } = buildFlowElements(run.graph, null);
    expect(nodes).toHaveLength(run.graph.nodes.length);
    expect(edges).toHaveLength(run.graph.edges.length);
    for (const n of nodes) {
      expect(['source', 'identity', 'tool', 'scope', 'output']).toContain(n.type);
      expect(n.data.kind).toBeTruthy();
      expect(n.data.label).toBeTruthy();
    }
  });

  it('highlights exactly the selected path hops', () => {
    const p1 = paths.find((p) => p.path_id === 'P1')!;
    const { nodes, edges } = buildFlowElements(run.graph, p1);
    const hlEdges = edges.filter((e) => e.animated);
    expect(hlEdges).toHaveLength(p1.hops.length);
    const hlNodes = nodes.filter((n) => n.data.highlighted).map((n) => n.id);
    for (const h of p1.hops) {
      expect(hlNodes).toContain(h.from);
      expect(hlNodes).toContain(h.to);
    }
  });
});

describe('PathRail + PathDetailPanel (FE-04)', () => {
  it('renders all five paths as keyboard-reachable buttons with pills and reason codes', () => {
    renderWithProviders(<PathRail paths={paths} selected={null} onSelect={() => {}} />);
    for (const p of paths) {
      const btn = screen.getByRole('button', { name: new RegExp(p.path_id) });
      expect(btn).toBeInTheDocument();
      expect(btn.textContent).toContain(p.status);
    }
    expect(screen.getAllByText('R2_CROSS_PURPOSE_FLOW').length).toBeGreaterThan(0);
  });

  it('never renders the string "confirmed" for any path', () => {
    renderWithProviders(<PathRail paths={paths} selected={null} onSelect={() => {}} />);
    renderWithProviders(<PathDetailPanel path={paths.find((p) => p.path_id === 'P4') ?? null} />);
    expect(screen.queryByText(/confirmed/i)).not.toBeInTheDocument();
  });

  it('selecting a path shows its primary reason code and rule id in the detail panel', () => {
    const p1 = paths.find((p) => p.path_id === 'P1')!;
    function Harness() {
      const [sel, setSel] = useState<string | null>(null);
      const path = paths.find((p) => p.path_id === sel) ?? null;
      return (
        <div>
          <PathRail paths={paths} selected={sel} onSelect={setSel} />
          <PathDetailPanel path={path} />
        </div>
      );
    }
    renderWithProviders(<Harness />);
    fireEvent.click(screen.getByRole('button', { name: /P1/ }));
    const detail = screen.getByTestId('path-detail');
    expect(detail).toHaveTextContent(primaryReason(p1)!.code);
    expect(detail).toHaveTextContent(primaryReason(p1)!.rule_id);
    expect(detail).toHaveTextContent('finance.export');
  });

  it('legend labels candidate as "candidate — not verified" (dashed, not color alone)', () => {
    renderWithProviders(<StatusLegend />);
    const legend = screen.getByTestId('status-legend');
    expect(legend).toHaveTextContent('candidate — not verified');
    expect(legend).toHaveTextContent('blocked — denied by policy');
  });
});

describe('custom nodes (FE-04)', () => {
  it('carry an aria-label with kind and label and are focusable', () => {
    const props = {
      id: 'tool:finance.export',
      data: { kind: 'tool', label: 'finance.export', risk: 'critical', highlighted: false },
    } as unknown as React.ComponentProps<typeof ToolNode>;
    render(<ToolNode {...props} />);
    const el = screen.getByRole('button', { name: /node kind tool label finance\.export/i });
    expect(el).toHaveAttribute('tabindex', '0');
  });
});

describe('GraphView (FE-04)', () => {
  it('renders the rail, canvas, legend, and detail panel from fixture data', async () => {
    renderWithProviders(<GraphView />);
    expect(await screen.findByTestId('path-rail')).toBeInTheDocument();
    expect(screen.getByTestId('path-graph')).toBeInTheDocument();
    expect(screen.getByTestId('status-legend')).toBeInTheDocument();
    expect(screen.getByTestId('path-detail')).toBeInTheDocument();
    expect(screen.queryByText(/confirmed/i)).not.toBeInTheDocument();
  });
});
