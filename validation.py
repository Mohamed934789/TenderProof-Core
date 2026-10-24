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
    """Basic document validation."""

    if not document["pages"]:
        raise ValueError("Document has no pages.")

    has_text = any(
        page["text"].strip()
        for page in document["pages"]
    )

    if not has_text:
        raise ValueError("Document has no extractable text.")

    for expected_number, page in enumerate(
        document["pages"], start=1
    ):
        if page["pdf_page"] != expected_number:
            raise ValueError(
                f"Invalid page numbering: "
                f"expected {expected_number}, "
                f"got {page['pdf_page']}."
            )


def validate_citation(
        
    citation: Citation,
    documents: list[DocumentPages],
) -> None:

    matched_document = next(
        (
            document
            for document in documents
            if document["document_id"] == citation["document_id"]
        ),
        None,
    )

    if matched_document is None:
        raise ValueError(
            f"Unknown document ID: {citation['document_id']}"
        )

    page_numbers = [
        page["pdf_page"]
        for page in matched_document["pages"]
    ]

    if citation["pdf_page"] not in page_numbers:
        raise ValueError(
            f"Invalid page number: {citation['pdf_page']}"
        )

    matched_page = next(
      page
    for page in matched_document["pages"]
    if page["pdf_page"] == citation["pdf_page"]  )

    quote = citation["quote"]

    if not isinstance(quote, str) or not quote.strip():
        raise ValueError("Citation quote is empty or invalid.")

    if quote not in matched_page["text"]:
        raise ValueError(
            "Citation quote was not found in the referenced page."
        )

def validate_extractions(
    eligibility: EligibilityOutput,
    technical: TechnicalOutput,
    tender: DocumentPages,
) -> None:
    """Initial validation for Agent 1 and Agent 2 outputs."""

    if not isinstance(eligibility.get("requirements"), list):
        raise ValueError(
            "Agent 1 must return a requirements list."
        )

    if not isinstance(technical.get("technical_requirements"), list):
        raise ValueError(
            "Agent 2 must return a technical_requirements list."
        )

    allowed_boq_statuses = {
        "FOUND",
        "NOT_FOUND",
        "NEEDS_REVIEW",
    }

    if technical.get("boq_status") not in allowed_boq_statuses:
        raise ValueError("Invalid BOQ status.")


    for requirement in eligibility["requirements"]:

        sources = requirement.get("sources")

        if not isinstance(sources, list) or not sources:
            raise ValueError(
                "Eligibility requirement must have sources."
            )

        for citation in sources:
            validate_citation(citation, [tender])


    for requirement in technical["technical_requirements"]:
        sources = requirement.get("sources")

        if not isinstance(sources, list) or not sources:
            raise ValueError(
                "Technical requirement must have sources."
            )

        for citation in sources:
            validate_citation(citation, [tender])

    
    boq_items = technical.get("boq_items")

    if not isinstance(boq_items, list):
        raise ValueError("BOQ items must be a list.")

    boq_status = technical["boq_status"]

    if boq_status == "NOT_FOUND" and boq_items:
        raise ValueError(
            "BOQ cannot contain items when status is NOT_FOUND."
        )

    if boq_status == "FOUND" and not boq_items:
        raise ValueError(
            "BOQ status is FOUND but no items were returned."
        )

    for item in boq_items:
        if not isinstance(item, dict):
            raise ValueError("BOQ item must be an object.")

        sources = item.get("sources")

        if not isinstance(sources, list) or not sources:
            raise ValueError("BOQ item must have sources.")

        for citation in sources:
            validate_citation(citation, [tender])

        quantity = item.get("quantity")

        if not isinstance(quantity, dict):
            raise ValueError("BOQ item must contain a quantity object.")

        raw_text = quantity.get("raw_text")

        if not isinstance(raw_text, str) or not raw_text.strip():
            raise ValueError("BOQ quantity must have raw_text.")

        quantity_sources = quantity.get("sources")

        if not isinstance(quantity_sources, list) or not quantity_sources:
            raise ValueError("BOQ quantity must have sources.")

        for citation in quantity_sources:
            validate_citation(citation, [tender])

        decimal_value = quantity.get("decimal_value")

        if decimal_value is not None:
            from decimal import Decimal, InvalidOperation

            if not isinstance(decimal_value, str):
                raise ValueError("Normalized quantity must be a string.")

            try:
                number = Decimal(decimal_value)
            except InvalidOperation:
                raise ValueError("Invalid normalized BOQ quantity.")

            if not number.is_finite() or number <= 0:
                raise ValueError("BOQ quantity must be positive and finite.")




def validate_verification(
    verification: VerificationOutput,
    eligibility: EligibilityOutput,
    technical: TechnicalOutput,
    company_documents: list[DocumentPages],
    *,
    reference_date: str,
) -> None:
    """Initial finding coverage validation."""

    findings = verification.get("findings")

    if not isinstance(findings, list):
        raise ValueError("Findings must be a list.")

    expected_targets = {
        ("ELIGIBILITY", req["requirement_id"])
        for req in eligibility["requirements"]
    }

    expected_targets.update(
        ("TECHNICAL", req["technical_id"])
        for req in technical["technical_requirements"]
    )

    expected_targets.update(
        ("BOQ", item["boq_item_id"])
        for item in technical["boq_items"]
    )

    actual_targets = [
        (finding["target_type"], finding["target_id"])
        for finding in findings
    ]

    if len(actual_targets) != len(set(actual_targets)):
        raise ValueError("Duplicate findings detected.")

    if set(actual_targets) != expected_targets:
        raise ValueError(
            "Findings do not match extracted requirements."
        )

    allowed_statuses = {
        "SATISFIED",
        "CONTRADICTED",
        "MISSING_EVIDENCE",
        "NEEDS_REVIEW",
    }

    for finding in findings:
        if finding["status"] not in allowed_statuses:
            raise ValueError(
                f"Invalid finding status: {finding['status']}"
            )

    for finding in findings:
        status = finding["status"]
        evidence = finding.get("evidence")

        if not isinstance(evidence, list):
            raise ValueError("Finding evidence must be a list.")

        if status in {"SATISFIED", "CONTRADICTED"}:
            if not evidence:
                raise ValueError(
                    f"{status} finding requires evidence."
                )

        for citation in evidence:
            validate_citation(citation, company_documents)

    for finding in findings:
        if finding["status"] == "MISSING_EVIDENCE":

            completeness_confirmed = (
                bool(company_documents)
                and all(
                    doc.get("completeness") == "COMPLETE"
                    and doc.get("completeness_basis")
                    in {"USER_CONFIRMED", "TEST_FIXTURE"}
                    for doc in company_documents
                )
            )

            if not completeness_confirmed:
                raise ValueError(
                    "MISSING_EVIDENCE requires confirmed document completeness."
                )

def validate_report(
    report: Report,
    documents: list[DocumentPages],
) -> None:
    """Basic final report validation."""

    if report.get("schema_version") != "core-draft-0.2":
        raise ValueError("Invalid report schema version.")

    mode = report.get("mode")

    if mode not in {"MOCK", "AI"}:
        raise ValueError("Invalid report mode.")

    for output in (
        report["eligibility"],
        report["technical"],
    ):
        provenance = output.get("provenance")

        if not isinstance(provenance, dict):
            raise ValueError("Missing extraction provenance.")

        if provenance.get("mode") != mode:
            raise ValueError("Extraction mode mismatch.")

    verification_provenance = report.get(
        "verification_provenance"
    )

    if not isinstance(verification_provenance, dict):
        raise ValueError("Missing verification provenance.")

    if verification_provenance.get("mode") != mode:
        raise ValueError("Verification mode mismatch.")
