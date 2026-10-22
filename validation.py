"""Student-owned source validation. Literal validity is not semantic proof."""
from models import Citation, DocumentPages, Report

def validate_citation(citation: Citation, documents: list[DocumentPages]) -> None:
    """Raise ValueError for unknown document/page or absent quotation."""
    raise NotImplementedError("Members 2 and 3: literal-source validation")

def validate_report(report: Report, documents: list[DocumentPages]) -> None:
    """Check coverage, sources and conservative status semantics."""
    raise NotImplementedError("Members 1 and 5: agree acceptance checks")
