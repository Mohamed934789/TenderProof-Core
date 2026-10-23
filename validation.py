"""Member 5: Python-only validation exercises, not a fourth AI agent.
All guards are intentionally UNIMPLEMENTED; type hints do not enforce safety.
Invalid structure/source -> ValueError. Uncertain interpretation -> explicit review
in a structurally valid result; never silently manufacture evidence.
"""
from models import (
    Citation, DocumentPages, EligibilityOutput, Report, TechnicalOutput,
    VerificationOutput,
)

def validate_document(document: DocumentPages) -> None:
    """Check fields, page order, table/cell coordinates, reading and completeness."""
    raise NotImplementedError("Member 5 with Member 1: document validation")

def validate_citation(citation: Citation, documents: list[DocumentPages]) -> None:
    """Check allowed document/page and literal quote; no fuzzy matching/RTL repair."""
    raise NotImplementedError("Member 5: literal-source validation")

def validate_extractions(
    eligibility: EligibilityOutput, technical: TechnicalOutput, tender: DocumentPages
) -> None:
    """Gate Agent 3 on both valid outputs, citations, BOQ state and quantity values."""
    raise NotImplementedError("Member 5 with Members 2/3: extraction validation")

def validate_verification(
    verification: VerificationOutput, eligibility: EligibilityOutput,
    technical: TechnicalOutput, company_documents: list[DocumentPages], *,
    reference_date: str,
) -> None:
    """Check target coverage, evidence, dates/numbers and conservative decisions."""
    raise NotImplementedError("Member 5 with Member 4: finding validation")

def validate_report(report: Report, documents: list[DocumentPages]) -> None:
    """Cross-check sources, target IDs, context, provenance and coverage warnings."""
    raise NotImplementedError("Member 5: final report validation")
