"""Approved Core learning contracts (2026-10-24), separate from reference API v1.
TypedDict documents shapes ONLY. Python validators remain student exercises.
Required nullable fields must be explicit None, never guessed or silently omitted.
"""
from typing import Literal, TypedDict

SCHEMA_VERSION = "core-draft-0.2"
Mode = Literal["MOCK", "AI"]
Status = Literal["SATISFIED", "CONTRADICTED", "MISSING_EVIDENCE", "NEEDS_REVIEW"]
Readability = Literal["READABLE", "PARTIAL", "UNREADABLE"]
DocumentRole = Literal["TENDER", "COMPANY"]
Completeness = Literal["UNKNOWN", "COMPLETE", "INCOMPLETE"]
CompletenessBasis = Literal["UNKNOWN", "USER_CONFIRMED", "TEST_FIXTURE"]
ExtractionMethod = Literal["NATIVE_TEXT", "OCR", "MIXED", "NONE"]
BOQStatus = Literal["FOUND", "NOT_FOUND", "NEEDS_REVIEW"]
TargetType = Literal["ELIGIBILITY", "TECHNICAL", "BOQ"]

class Citation(TypedDict):
    document_id: str
    pdf_page: int
    quote: str

class TableCell(TypedDict):
    row: int
    column: int
    text: str
    sources: list[Citation]

class TableRegion(TypedDict):
    table_id: str
    pdf_page: int
    structure_quality: Literal["RECOVERED", "PARTIAL", "UNREADABLE"]
    cells: list[TableCell]
    warnings: list[str]

class Page(TypedDict):
    pdf_page: int
    text: str
    readability: Readability
    extraction_method: ExtractionMethod
    tables: list[TableRegion]
    warnings: list[str]

class DocumentPages(TypedDict):
    document_id: str
    filename: str
    role: DocumentRole
    completeness: Completeness
    completeness_basis: CompletenessBasis
    pages: list[Page]
    warnings: list[str]

class DocumentManifest(TypedDict):
    document_id: str
    filename: str
    role: DocumentRole
    completeness: Completeness
    completeness_basis: CompletenessBasis
    warnings: list[str]

class ExtractionProvenance(TypedDict):
    mode: Mode
    provider: str
    model: str
    prompt_version: str

class Requirement(TypedDict):
    requirement_id: str
    text: str
    category: Literal["REGISTRATION", "LICENSE", "EXPERIENCE",
                      "ADMINISTRATIVE", "FINANCIAL", "OTHER"]
    needs_review: bool
    review_reasons: list[str]
    sources: list[Citation]

class TechnicalRequirement(TypedDict):
    technical_id: str
    text: str
    category: Literal["SPECIFICATION", "MODEL", "EXECUTION_DEADLINE", "OTHER"]
    needs_review: bool
    review_reasons: list[str]
    sources: list[Citation]

class Quantity(TypedDict):
    raw_text: str
    decimal_value: str | None
    sources: list[Citation]

class BOQItem(TypedDict):
    boq_item_id: str
    description: str
    quantity: Quantity
    unit: str | None
    unit_normalized: str | None
    table_id: str | None
    needs_review: bool
    review_reasons: list[str]
    sources: list[Citation]

class EligibilityOutput(TypedDict):
    requirements: list[Requirement]
    provenance: ExtractionProvenance
    warnings: list[str]

class TechnicalOutput(TypedDict):
    boq_status: BOQStatus
    boq_review_reasons: list[str]
    boq_items: list[BOQItem]
    technical_requirements: list[TechnicalRequirement]
    provenance: ExtractionProvenance
    warnings: list[str]

class Finding(TypedDict):
    target_type: TargetType
    target_id: str
    status: Status
    explanation: str
    evidence: list[Citation]
    review_required: bool
    uncertainty_reasons: list[str]

class VerificationOutput(TypedDict):
    findings: list[Finding]
    provenance: ExtractionProvenance
    warnings: list[str]

class Report(TypedDict):
    schema_version: Literal["core-draft-0.2"]
    mode: Mode
    reference_date: str
    documents: list[DocumentManifest]
    eligibility: EligibilityOutput
    technical: TechnicalOutput
    findings: list[Finding]
    verification_provenance: ExtractionProvenance
    coverage_confirmed: bool
    warnings: list[str]
