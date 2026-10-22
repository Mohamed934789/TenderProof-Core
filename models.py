"""Draft learning contract. TypedDict describes shape, not runtime validation.
Member 1 must review completeness/uncertainty with everyone before implementation.
This is NOT the original public v1 API schema.
"""
from typing import Literal, TypedDict

Status = Literal["SATISFIED", "CONTRADICTED", "MISSING_EVIDENCE", "NEEDS_REVIEW"]
class Page(TypedDict):
    pdf_page: int
    text: str
    readability: Literal["READABLE", "PARTIAL", "UNREADABLE"]
class DocumentPages(TypedDict):
    document_id: str
    filename: str
    role: Literal["TENDER", "COMPANY"]
    pages: list[Page]
class Citation(TypedDict):
    document_id: str
    pdf_page: int
    quote: str
class Requirement(TypedDict):
    requirement_id: str
    text: str
    needs_review: bool
    sources: list[Citation]
class Finding(TypedDict):
    requirement_id: str
    status: Status
    explanation: str
    evidence: list[Citation]
class Report(TypedDict):
    mode: Literal["MOCK", "AI"]
    reference_date: str
    coverage_confirmed: bool
    requirements: list[Requirement]
    findings: list[Finding]
    warnings: list[str]
