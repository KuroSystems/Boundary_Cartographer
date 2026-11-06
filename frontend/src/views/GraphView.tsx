import { useMemo, useState } from 'react';
import { useDemoRun } from '../api/useDemoData';
import { buildFlowElements } from '../lib/layout';
import { PathGraph } from '../components/graph/PathGraph';
import { PathRail } from '../components/graph/PathRail';
import { PathDetailPanel } from '../components/graph/PathDetailPanel';
import { StatusLegend } from '../components/graph/StatusLegend';
import { Skeleton } from '../components/Skeleton';
import { ErrorState } from '../components/ErrorState';

// GraphView (FE-04): the /graph route — path rail + React Flow canvas +
// detail panel + legend. Selecting a path highlights its hops.
export function GraphView() {
  const run = useDemoRun();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const selected = useMemo(
    () => run.data?.paths.find((p) => p.path_id === selectedId) ?? null,
    [run.data, selectedId],
  );
  const { nodes, edges } = useMemo(
    () => buildFlowElements(run.data?.graph ?? { nodes: [], edges: [] }, selected),
    [run.data, selected],
  );

  if (run.isLoading) return <Skeleton label="Loading run…" />;
  if (run.error || !run.data) {
    return (
      <ErrorState
        code="RUN_UNAVAILABLE"
        message={run.error instanceof Error ? run.error.message : 'unknown error'}
      />
    );
  }

  return (
    <div>
      <div className="panel">
        <h2>Attack-path graph</h2>
        <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem' }}>
          {run.data.graph.nodes.length} nodes · {run.data.graph.edges.length} edges ·{' '}
          {run.data.paths.length} paths
        </p>
      </div>
      <div className="graph-layout">
        <div className="graph-rail">
          <PathRail paths={run.data.paths} selected={selectedId} onSelect={setSelectedId} />
          <StatusLegend />
        </div>
        <div className="graph-main">
          <PathGraph nodes={nodes} edges={edges} />
          <PathDetailPanel path={selected} />
        </div>
      </div>
    </div>
  );
}
