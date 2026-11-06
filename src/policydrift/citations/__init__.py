"""Citation validation: markers point at shown passages, and figures appear in cited sources."""

from policydrift.citations.validate import (
    CitationReport,
    NumberCheck,
    cited_ids,
    normalise_markers,
    validate,
)

__all__ = ["CitationReport", "NumberCheck", "cited_ids", "normalise_markers", "validate"]
