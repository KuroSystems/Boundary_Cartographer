"""Candidate path search with candidate/disproved labelling (BE-06).

- Bounded `nx.all_simple_paths` (max 5 hops), deterministic sort by node-id tuple.
- Hops must be grant-supported (an existing edge of a supported kind); otherwise
  the path is `disproved` with a structural reason — never `allowed`/`blocked`
  (classification is BE-07's job; this module never imports the policy engine).
- The five golden paths P1–P5 are synthesized via explicit hop templates below,
  each validated against the graph before emission.
- Output is `Path(status="candidate", basis="graph_reachability")` with
  `history[0] = {status: "candidate", at_step: "path_finder"}`.
"""

from dataclasses import dataclass

import networkx as nx

from app.contracts import (
    Basis,
    EdgeKind,
    Path,
    PathHop,
    PathReason,
    PathStatus,
    Purpose,
    RuleId,
)
from app.fixtures import LoadedFixtures

MAX_HOPS = 5

SUPPORTED_HOP_KINDS = {
    EdgeKind.FLOWS_TO,
    EdgeKind.MAY_INVOKE,
    EdgeKind.DELEGATES_TO,
    EdgeKind.PRODUCES,
    EdgeKind.READS,
    EdgeKind.DERIVED_FROM,
}

SINK_EXPORT = "tool:finance.export"
ORIGIN_DOC = "source:doc-untrusted-001"


@dataclass(frozen=True)
class _HopSpec:
    from_: str
    to: str
    actor: str
    purpose: Purpose


@dataclass(frozen=True)
class _Template:
    """One explicit golden path template (tasks.md §2.6) as a hop list."""

    path_id: str
    hops: tuple[_HopSpec, ...]


def _templates() -> list[_Template]:
    doc = ORIGIN_DOC
    da = "identity:document_assistant"
    fa = "identity:finance_analyst"
    read = "tool:document.read"
    summ = "tool:document.summarize"
    lookup = "tool:finance.lookup"
    export = SINK_EXPORT
    ds = Purpose.DOCUMENT_SUMMARIZATION
    fr = Purpose.FINANCE_REPORTING
    return [
        _Template("P1", (
            _HopSpec(doc, read, "document_assistant", ds),
            _HopSpec(read, summ, "document_assistant", ds),
            _HopSpec(da, fa, "document_assistant", ds),
            _HopSpec(fa, lookup, "finance_analyst", ds),
            _HopSpec(fa, export, "finance_analyst", ds),
        )),
        _Template("P2", (
            _HopSpec(doc, read, "document_assistant", ds),
            _HopSpec(read, summ, "document_assistant", ds),
            _HopSpec(da, fa, "document_assistant", ds),
            _HopSpec(fa, export, "finance_analyst", ds),
        )),
        _Template("P3", (
            _HopSpec(doc, read, "document_assistant", ds),
            _HopSpec(read, summ, "document_assistant", ds),
            _HopSpec(summ, "output:summary", "document_assistant", ds),
        )),
        _Template("P4", (
            _HopSpec(da, export, "document_assistant", ds),
        )),
        _Template("P5", (
            _HopSpec(fa, lookup, "finance_analyst", fr),
            _HopSpec(fa, export, "finance_analyst", fr),
        )),
    ]


def _hop_supported(g: nx.DiGraph, u: str, v: str) -> bool:
    return g.has_edge(u, v) and g.edges[u, v]["kind"] in SUPPORTED_HOP_KINDS


def _hops_supported(g: nx.DiGraph, hops: tuple[_HopSpec, ...]) -> bool:
    return all(_hop_supported(g, h.from_, h.to) for h in hops)


def _structural_reason(u: str, v: str) -> PathReason:
    return PathReason(
        code="R3_WRONG_IDENTITY",
        rule_id=RuleId.R3,
        message=f"no may_invoke edge from {u} to {v}",
        evidence_ids=["src:grant-matrix"],
    )


def _build_path(g: nx.DiGraph, template: _Template, status: PathStatus,
                reasons: list[PathReason]) -> Path:
    hops = []
    for step, spec in enumerate(template.hops, start=1):
        kind = g.edges[spec.from_, spec.to]["kind"] if g.has_edge(spec.from_, spec.to) \
            else EdgeKind.MAY_INVOKE
        hops.append(PathHop(
            step=step,
            **{"from": spec.from_, "to": spec.to},
            kind=kind,
            actor=spec.actor,
            purpose=spec.purpose,
        ))
    history = [{"status": PathStatus.CANDIDATE, "at_step": "path_finder"}]
    if status != PathStatus.CANDIDATE:
        history.append({"status": status, "at_step": "path_finder"})
    origin = template.hops[0].from_
    return Path(
        path_id=template.path_id,
        status=status,
        basis=Basis.GRAPH_REACHABILITY,
        origin=origin,
        sink=template.hops[-1].to,
        stated_purpose=template.hops[0].purpose,
        tainted=status == PathStatus.CANDIDATE and origin == ORIGIN_DOC,
        hops=hops,
        rule_refs=sorted({r.rule_id for r in reasons}, key=lambda r: r.value),
        reasons=reasons,
        history=history,
    )


def find_simple_paths(g: nx.DiGraph, origin: str, sink: str,
                      max_hops: int = MAX_HOPS) -> list[list[str]]:
    """Bounded simple paths, deterministically sorted by node-id tuple."""
    paths = list(nx.all_simple_paths(g, origin, sink, cutoff=max_hops))
    return sorted(paths, key=tuple)


def search_candidates(g: nx.DiGraph, origin: str, sinks: list[str],
                      max_hops: int = MAX_HOPS) -> list[Path]:
    """Generic bounded search: grant-supported paths to each sink labelled
    `candidate`; structurally impossible ones come back `disproved`."""
    out: list[Path] = []
    for sink in sinks:
        for nodes in find_simple_paths(g, origin, sink, max_hops):
            hops = tuple(
                _HopSpec(
                    u, v,
                    u.removeprefix("identity:") if u.startswith("identity:")
                    else "document_assistant",
                    Purpose.DOCUMENT_SUMMARIZATION,
                )
                for u, v in zip(nodes, nodes[1:])
            )
            template = _Template(path_id="", hops=hops)
            if _hops_supported(g, hops):
                path = _build_path(g, template, PathStatus.CANDIDATE, [])
                out.append(path.model_copy(update={"path_id": f"C{len(out) + 1}"}))
            else:
                bad = next(h for h in hops if not _hop_supported(g, h.from_, h.to))
                path = _build_path(g, template, PathStatus.DISPROVED,
                                   [_structural_reason(bad.from_, bad.to)])
                out.append(path.model_copy(update={"path_id": f"D{len(out) + 1}"}))
    return out


def find_paths(g: nx.DiGraph, fixtures: LoadedFixtures) -> list[Path]:
    """The five golden paths P1–P5, synthesized from explicit templates and
    validated against the graph. P1/P2/P3/P5 are emitted as `candidate` only if
    every hop is grant-supported in the current graph (e.g. without the
    delegates_to edge, P1/P2 drop out of the candidate set); P4 is `disproved`
    when the direct may_invoke edge is absent — a structural fact, not a policy
    denial.
    """
    out: list[Path] = []
    for template in _templates():
        if template.path_id == "P4":
            direct = _hop_supported(g, template.hops[0].from_, template.hops[0].to) and \
                g.edges[template.hops[0].from_, template.hops[0].to]["kind"] == EdgeKind.MAY_INVOKE
            if direct:
                out.append(_build_path(g, template, PathStatus.CANDIDATE, []))
            else:
                h = template.hops[0]
                out.append(_build_path(
                    g, template, PathStatus.DISPROVED, [_structural_reason(h.from_, h.to)],
                ))
            continue
        if _hops_supported(g, template.hops):
            out.append(_build_path(g, template, PathStatus.CANDIDATE, []))
        # unsupported template hops => path not emitted (no fallback to confirmed)
    return out
