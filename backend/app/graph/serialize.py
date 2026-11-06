"""Serialize a built NetworkX graph into the contract `Graph` model (BE-05).

Deterministic: nodes/edges are emitted in insertion order with stable IDs, so
the same fixtures always produce identical serialized JSON.
"""

import networkx as nx

from app.contracts import Edge as ContractEdge
from app.contracts import Graph
from app.contracts import Node as ContractNode


def serialize_graph(g: nx.DiGraph) -> Graph:
    nodes = [
        ContractNode(
            id=node_id,
            kind=data["kind"],
            label=data["label"],
            risk=data.get("risk"),
            scopes=list(data.get("scopes", [])),
            source_ids=list(data["source_ids"]),
        )
        for node_id, data in g.nodes(data=True)
    ]
    edges = [
        ContractEdge(
            id=data["edge_id"],
            **{
                "from": u,
                "to": v,
                "kind": data["kind"],
                "purposes": list(data.get("purposes", [])),
                "scopes": list(data.get("scopes", [])),
                "trust": data.get("trust"),
                "source_ids": list(data["source_ids"]),
            },
        )
        for u, v, data in g.edges(data=True)
    ]
    return Graph(nodes=nodes, edges=edges)


def serialize_graph_json(g: nx.DiGraph) -> dict:
    """Contract-shaped JSON (snake_case, aliases resolved) — stable for snapshots."""
    return serialize_graph(g).model_dump(by_alias=True, mode="json")
