"""Taint tracking for the replay engine (BE-08).

Document-derived content marks everything it touches as tainted; outputs of
tools that consumed tainted input are `derived_untrusted`. Pure data structure,
no I/O.
"""


class TaintTracker:
    def __init__(self, labels: set[str] | None = None):
        self._labels: set[str] = set(labels or ())

    @classmethod
    def from_document(cls, document_id: str) -> "TaintTracker":
        """The seeded untrusted document starts the taint chain."""
        return cls({"untrusted_document"})

    def mark(self, label: str) -> None:
        self._labels.add(label)

    def mark_derived_untrusted(self) -> None:
        if self.is_tainted:
            self._labels.add("derived_untrusted")

    @property
    def labels(self) -> list[str]:
        return sorted(self._labels)

    @property
    def is_tainted(self) -> bool:
        return bool(self._labels)
