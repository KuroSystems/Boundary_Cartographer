"""Graph construction + path search package (BE-05, BE-06)."""

from .build import build_graph
from .paths import MAX_HOPS, find_paths, find_simple_paths, search_candidates
from .serialize import serialize_graph, serialize_graph_json

__all__ = [
    "MAX_HOPS",
    "build_graph",
    "find_paths",
    "find_simple_paths",
    "search_candidates",
    "serialize_graph",
    "serialize_graph_json",
]
