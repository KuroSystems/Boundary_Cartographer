import { ReactFlow, Background, Controls, type NodeProps } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import type { Edge, Node } from '@xyflow/react';
import type { FlowNodeData } from '../../lib/layout';

// Custom node types (FE-04). Every node is focusable and carries an aria-label
// with its kind and label (keyboard + screen-reader accessible).

function BaseNode({ data, kindLabel }: { data: FlowNodeData; kindLabel: string }) {
  return (
    <div
      className={`flow-node flow-node-${data.kind}${data.highlighted ? ' highlighted' : ''}`}
      tabIndex={0}
      role="button"
      aria-label={`node kind ${data.kind} label ${data.label}`}
      title={`${kindLabel}: ${data.label}`}
    >
      <span className="flow-node-kind">{kindLabel}</span>
      <span className="flow-node-label mono">{data.label}</span>
      {data.risk && <span className="flow-node-risk">{data.risk}</span>}
    </div>
  );
}

export function SourceNode(props: NodeProps<Node<FlowNodeData>>) {
  return <BaseNode data={props.data} kindLabel="source" />;
}
export function IdentityNode(props: NodeProps<Node<FlowNodeData>>) {
  return <BaseNode data={props.data} kindLabel="identity" />;
}
export function ToolNode(props: NodeProps<Node<FlowNodeData>>) {
  return <BaseNode data={props.data} kindLabel="tool" />;
}
export function ScopeNode(props: NodeProps<Node<FlowNodeData>>) {
  return <BaseNode data={props.data} kindLabel="data scope" />;
}
export function OutputNode(props: NodeProps<Node<FlowNodeData>>) {
  return <BaseNode data={props.data} kindLabel="output" />;
}

const nodeTypes = {
  source: SourceNode,
  identity: IdentityNode,
  tool: ToolNode,
  scope: ScopeNode,
  output: OutputNode,
};

// PathGraph (FE-04): React Flow canvas over the deterministic layout. The
// selected path's hops are highlighted (edge style + node ring).
export function PathGraph({
  nodes,
  edges,
}: {
  nodes: Node<FlowNodeData>[];
  edges: Edge[];
}) {
  return (
    <div className="graph-canvas" data-testid="path-graph" style={{ width: '100%', height: '62vh' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable
        proOptions={{ hideAttribution: true }}
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}
