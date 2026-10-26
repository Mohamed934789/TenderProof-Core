"""One fixed-order pipeline and command-line entry point for TenderProof AI."""
from datetime import date
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
    eligibility_client: LLMClient | None = None,
    technical_client: LLMClient | None = None,
    verification_client: LLMClient | None = None,
    mode: Mode = "MOCK",
) -> Report:
    """Read documents -> A1 + A2 -> validate_extractions -> A3 -> validate -> report.
    A1/A2 may run concurrently; A3 must await BOTH valid outputs.
    Valid NOT_FOUND is not an Agent 2 failure. Failed stages must not publish success.
    Completeness stays UNKNOWN unless explicitly established by a documented input.
    """
    date.fromisoformat(reference_date)
    if mode not in {"MOCK", "AI"}:
        raise ValueError(f"Unsupported mode: {mode}")
    if mode == "AI" and any(client is None for client in (
        eligibility_client, technical_client, verification_client
    )):
        raise ValueError("AI mode requires an LLMClient for every agent.")
    tender = read_pdf(
        tender_path,
        document_id="tender-001",
        role="TENDER",
    )

    validate_document(tender)

    company_documents = []

    for index, company_path in enumerate(company_paths, start=1):
        company = read_pdf(
            company_path,
            document_id=f"company-{index:03d}",
            role="COMPANY",
        )

        validate_document(company)
        company_documents.append(company)


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


    all_documents = [tender, *company_documents]
    warnings = []
    for document in all_documents:
        warnings.extend(document["warnings"])
        if document["completeness"] != "COMPLETE":
            warnings.append(f"{document['document_id']}: document completeness is not confirmed.")
        for page in document["pages"]:
            warnings.extend(f"{document['document_id']} page {page['pdf_page']}: {warning}"
                            for warning in page["warnings"])
    for output in (eligibility, technical, verification):
        warnings.extend(output["warnings"])
    if not company_documents:
        warnings.append("No company documents were supplied.")
    # The reader does not establish document completeness or visual table order.
    warnings.append("Full document coverage is not confirmed; review the source PDFs.")

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
        "warnings": list(dict.fromkeys(warnings)),
    }

    validate_report(report, all_documents)
    
    return report


def main():
    import argparse
    import asyncio
    import json

    parser = argparse.ArgumentParser(description="Analyze tender and company PDFs into a JSON report.")
    parser.add_argument("--tender", type=Path, required=True)
    parser.add_argument("--company", type=Path, nargs="*", default=[])
    parser.add_argument("--reference-date", required=True, help="Evaluation date: YYYY-MM-DD")
    parser.add_argument("--mode", choices=("MOCK", "AI"), default="MOCK")
    parser.add_argument("--output", type=Path, default=Path("output/report.json"))
    args = parser.parse_args()

    async def run():
        client = None
        if args.mode == "AI":
            from openai_adapter import OpenAIAdapter
            client = OpenAIAdapter()
        try:
            return await analyze(args.tender, args.company, reference_date=args.reference_date,
                                 eligibility_client=client, technical_client=client,
                                 verification_client=client, mode=args.mode)
        finally:
            if client is not None:
                await client.aclose()

    report = asyncio.run(run())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Report saved to {args.output} ({args.mode}, {len(report['findings'])} findings).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
