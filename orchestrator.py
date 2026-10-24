"""Member 5: fixed-order integration exercise; no backend or execution yet."""
from pathlib import Path
from llm_client import LLMClient
from models import Mode, Report
from pdf_reader import read_pdf
from validation import validate_document
from agent1 import extract_eligibility
from agent2 import extract_technical
from validation import validate_extractions
from agent3 import verify_company
from validation import validate_verification
from validation import validate_report

async def analyze(
    tender_path: Path, company_paths: list[Path], *,
    reference_date: str,
    eligibility_client: LLMClient,
    technical_client: LLMClient,
    verification_client: LLMClient,
    mode: Mode = "MOCK",
) -> Report:
    """Read documents -> A1 + A2 -> validate_extractions -> A3 -> validate -> report.
    A1/A2 may run concurrently; A3 must await BOTH valid outputs.
    Valid NOT_FOUND is not an Agent 2 failure. Failed stages must not publish success.
    Completeness stays UNKNOWN unless explicitly established by a documented input.
    """
    tender = read_pdf(
        tender_path,
        document_id="tender-001",
        role="TENDER",
    )

    validate_document(tender)

    print("Tender document validated successfully.")
    company_documents = []

    for index, company_path in enumerate(company_paths, start=1):
        company = read_pdf(
            company_path,
            document_id=f"company-{index:03d}",
            role="COMPANY",
        )

        validate_document(company)
        company_documents.append(company)

    print(f"Company documents validated: {len(company_documents)}")

    eligibility = await extract_eligibility(
        tender,
        client=eligibility_client,
        mode=mode,
    )

    technical = await extract_technical(
        tender,
        client=technical_client,
        mode=mode,
    )

    validate_extractions(eligibility, technical, tender)

    print("Agent 1 and Agent 2 outputs validated.")

    verification = await verify_company(
        eligibility,
        technical,
        company_documents,
        reference_date=reference_date,
        client=verification_client,
        mode=mode,
    )

    validate_verification(
        verification,
        eligibility,
        technical,
        company_documents,
        reference_date=reference_date,
    )

    print("Verification stage completed.")

    all_documents = [tender, *company_documents]

    report: Report = {
        "schema_version": "core-draft-0.2",
        "mode": mode,
        "reference_date": reference_date,
        "documents": [
            {
                "document_id": doc["document_id"],
                "filename": doc["filename"],
                "role": doc["role"],
                "completeness": doc["completeness"],
                "completeness_basis": doc["completeness_basis"],
                "warnings": doc["warnings"],
            }
            for doc in all_documents
        ],
        "eligibility": eligibility,
        "technical": technical,
        "findings": verification["findings"],
        "verification_provenance": verification["provenance"],
        "coverage_confirmed": False,
        "warnings": [
            "Validation is incomplete; report requires review."
        ],
    }

    validate_report(report, all_documents)
    
    return report
  


   
