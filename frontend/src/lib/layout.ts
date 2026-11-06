// Deterministic layered layout (FE-04): columns by node kind, rows sorted by
// id — identical input graph always yields identical positions (no randomness),
// which a unit test snapshots.

import type { Edge, Node } from '@xyflow/react';
import type { Graph, GraphNode, Path } from '../api/types';

export const COLUMN_X = 220;
export const ROW_Y = 90;

const LAYER_BY_KIND: Record<string, number> = {
  source: 0,
  identity: 1,
  tool: 2,
  data_scope: 3,
  output: 4,
};

export interface Positioned {
  x: number;
  y: number;
}

/** id -> position, computed deterministically from the graph alone. */
export function layoutGraph(graph: Graph): Map<string, Positioned> {
  const byLayer = new Map<number, GraphNode[]>();
  for (const n of graph.nodes) {
    const layer = LAYER_BY_KIND[n.kind] ?? 0;
    const list = byLayer.get(layer) ?? [];
    list.push(n);
    byLayer.set(layer, list);
  }
  const positions = new Map<string, Positioned>();
  for (const [layer, nodes] of byLayer) {
    const sorted = [...nodes].sort((a, b) => a.id.localeCompare(b.id));
    sorted.forEach((n, row) => {
      positions.set(n.id, { x: layer * COLUMN_X, y: row * ROW_Y });
    });
  }
  return positions;
}

/** React Flow node type for a contract node kind. */
export function nodeTypeOf(kind: string): string {
  switch (kind) {
    case 'source':
      return 'source';
    case 'identity':
      return 'identity';
    case 'tool':
      return 'tool';
    case 'data_scope':
      return 'scope';
    case 'output':
      return 'output';
    default:
      return 'tool';
  }
}

export interface FlowNodeData extends Record<string, unknown> {
  kind: string;
  label: string;
  risk?: string;
  highlighted: boolean;
}

/** Build React Flow nodes/edges from the run graph. */
export function buildFlowElements(
  graph: Graph,
  selectedPath: Path | null,
): { nodes: Node<FlowNodeData>[]; edges: Edge[] } {
  const positions = layoutGraph(graph);
  const highlightedNodes = new Set<string>();
  const highlightedEdges = new Set<string>();
  if (selectedPath) {
    for (const h of selectedPath.hops) {
      highlightedNodes.add(h.from);
      highlightedNodes.add(h.to);
    }
    for (const e of graph.edges) {
      if (selectedPath.hops.some((h) => h.from === e.from && h.to === e.to && h.kind === e.kind)) {
        highlightedEdges.add(e.id);
      }
    }
  }

  const nodes: Node<FlowNodeData>[] = graph.nodes.map((n) => ({
    id: n.id,
    type: nodeTypeOf(n.kind),
    position: positions.get(n.id) ?? { x: 0, y: 0 },
    data: {
      kind: n.kind,
      label: n.label,
      risk: n.risk,
      highlighted: highlightedNodes.has(n.id),
    },
  }));

  const edges: Edge[] = graph.edges.map((e) => ({
    id: e.id,
    source: e.from,
    target: e.to,
    label: e.kind,
    animated: highlightedEdges.has(e.id),
    style: highlightedEdges.has(e.id)
      ? { stroke: 'var(--accent)', strokeWidth: 3 }
      : { stroke: 'var(--border)', strokeDasharray: e.kind === 'flows_to' || e.kind === 'derived_from' ? '6 4' : undefined },
  }));

  return { nodes, edges };
}

/** Primary reason of a path (first reason) for rail/detail display. */
export function primaryReason(path: Path): { code: string; rule_id: string } | null {
  return path.reasons.length > 0 ? { code: path.reasons[0].code, rule_id: path.reasons[0].rule_id } : null;
}
