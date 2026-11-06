"""NetworkX graph construction (BE-05).

Builds a deterministic directed graph from the loaded fixtures (BE-02):
nodes for the seeded source, both identities, the four tools, the five data
scopes, and the two outputs; edges for flows_to, may_invoke (from the grant
matrix, annotated with purposes/scopes), reads, produces, derived_from, and
delegates_to. Node/edge IDs are stable (`tool:finance.export`, `edge:05`) and
insertion order is fixed, so the same fixtures always produce identical
serialized JSON.
"""

import networkx as nx

from app.fixtures import LoadedFixtures

SOURCE_MANIFEST = "src:manifest"
SOURCE_GRANTS = "src:grant-matrix"


def _source_node_id(document_id: str) -> str:
    # src:doc-untrusted-001 -> source:doc-untrusted-001
    return "source:" + document_id.removeprefix("src:")


def build_graph(fixtures: LoadedFixtures) -> nx.DiGraph:
    """Build the graph. Pure function of the fixtures."""
    g = nx.DiGraph()
    doc_id = fixtures.document["id"]
    src = _source_node_id(doc_id)

    # ---- nodes (fixed order) ----
    g.add_node(src, kind="source", label=fixtures.document["title"],
               source_ids=[doc_id])
    for identity in fixtures.identities:
        g.add_node(f"identity:{identity['id']}", kind="identity", label=identity["id"],
                   source_ids=[SOURCE_MANIFEST])
    for tool in fixtures.manifest["tools"]:
        g.add_node(
            f"tool:{tool['name']}", kind="tool", label=tool["name"],
            risk="critical" if tool["sensitive"] else None,
            scopes=list(tool["required_scopes"]), source_ids=[SOURCE_MANIFEST],
        )
    scopes = sorted({s for t in fixtures.manifest["tools"] for s in t["required_scopes"]})
    for scope in scopes:
        g.add_node(f"data_scope:{scope}", kind="data_scope", label=scope,
                   source_ids=[SOURCE_MANIFEST])
    g.add_node("output:summary", kind="output", label="Summary artifact",
               source_ids=[SOURCE_MANIFEST])
    g.add_node("output:export_report", kind="output", label="Exported report artifact",
               risk="critical", source_ids=[SOURCE_MANIFEST])

    edges: list[tuple] = []  # (from, to, attrs) in fixed order

    # flows_to: untrusted source reaches the tools/actor that consume it
    edges.append((src, "tool:document.read",
                  {"kind": "flows_to", "trust": "untrusted", "source_ids": [doc_id]}))
    edges.append((src, "tool:document.summarize",
                  {"kind": "flows_to", "trust": "untrusted", "source_ids": [doc_id]}))

    # may_invoke: from the grant matrix, annotated with purposes + scopes
    for grant in fixtures.grants:
        edges.append((
            f"identity:{grant['identity']}", f"tool:{grant['tool']}",
            {"kind": "may_invoke", "purposes": list(grant["purposes"]),
             "scopes": list(grant["scopes"]), "trust": "trusted",
             "source_ids": [SOURCE_GRANTS]},
        ))

    # delegates_to
    for identity in fixtures.identities:
        for delegate in identity.get("may_delegate_to", []):
            edges.append((
                f"identity:{identity['id']}", f"identity:{delegate}",
                {"kind": "delegates_to", "trust": "trusted", "source_ids": [SOURCE_GRANTS]},
            ))

    # reads: tool -> each scope it reads (from manifest required_scopes)
    for tool in fixtures.manifest["tools"]:
        for scope in tool["required_scopes"]:
            edges.append((
                f"tool:{tool['name']}", f"data_scope:{scope}",
                {"kind": "reads", "trust": "trusted", "source_ids": [SOURCE_MANIFEST]},
            ))
    # summarizer also consumes the raw untrusted document scope
    edges.append(("tool:document.summarize", "data_scope:docs:read_untrusted",
                  {"kind": "reads", "trust": "trusted", "source_ids": [SOURCE_MANIFEST]}))

    # produces
    edges.append(("tool:document.summarize", "output:summary",
                  {"kind": "produces", "trust": "trusted", "source_ids": [SOURCE_MANIFEST]}))
    edges.append(("tool:finance.export", "output:export_report",
                  {"kind": "produces", "trust": "trusted", "source_ids": [SOURCE_MANIFEST]}))

    # derived_from: outputs derive (taint) from the untrusted source
    edges.append(("output:summary", src,
                  {"kind": "derived_from", "trust": "derived_untrusted", "source_ids": [doc_id]}))
    edges.append(("output:export_report", src,
                  {"kind": "derived_from", "trust": "derived_untrusted", "source_ids": [doc_id]}))

    # the actor receives the untrusted document; the summary flows back to the actor
    edges.append((src, "identity:document_assistant",
                  {"kind": "flows_to", "trust": "untrusted", "source_ids": [doc_id]}))
    edges.append(("output:summary", "identity:document_assistant",
                  {"kind": "flows_to", "trust": "derived_untrusted", "source_ids": [doc_id]}))
    # document content flows read -> summarize, and the summary is produced for the actor
    edges.append(("tool:document.read", "tool:document.summarize",
                  {"kind": "flows_to", "trust": "untrusted", "source_ids": [doc_id]}))
    edges.append(("tool:document.summarize", "identity:document_assistant",
                  {"kind": "flows_to", "trust": "derived_untrusted", "source_ids": [doc_id]}))

    for idx, (u, v, attrs) in enumerate(edges, start=1):
        g.add_edge(u, v, edge_id=f"edge:{idx:02d}", **attrs)

    return g
