"""Member 1: document-processing exercise. No implementation copied."""
from pathlib import Path
from models import Completeness, CompletenessBasis, DocumentPages, DocumentRole

def read_pdf(
    path: Path, *, document_id: str, role: DocumentRole,
    completeness: Completeness = "UNKNOWN",
    completeness_basis: CompletenessBasis = "UNKNOWN",
) -> DocumentPages:
    """Preserve PDF pages and source text; disclose page/table reading quality.
    tables=[] means no recovered table, not proof that the PDF contains no BOQ.
    OCR is not implemented or implied by ExtractionMethod annotations.
    """
    raise NotImplementedError("Member 1: document processing")
