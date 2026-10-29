
"""Real tender PDF -> PDF Reader -> Agent 2 -> OpenAI."""

import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from agent2 import extract_technical
from openai_adapter import OpenAIAdapter
from pdf_reader import read_pdf


PDF_PATH = (
    PROJECT_ROOT / "tests" / "fixtures" / "ida-335.pdf"
)

TEST_PAGES = {5, 6}

EXPECTED_BOQ = {
    "B7030": "104",
    "C9070": "2",
    "TX-4100": "1",
}

INSURANCE_AMOUNTS = {"14000", "1200", "600"}


def compare_boq(items):
    print("\n====== BOQ COMPARISON ======")

    passed = True

    for model_code, expected in EXPECTED_BOQ.items():
        matches = [
            item
            for item in items
            if model_code.lower() in item["description"].lower()
        ]

        if len(matches) != 1:
            print(
                f"FAIL: {model_code} — "
                f"expected 1 item, got {len(matches)}"
            )
            passed = False
            continue

        item = matches[0]
        actual = item["quantity"]["decimal_value"]

        if actual == expected:
            print(
                f"PASS: {model_code} | "
                f"Expected {expected} | Actual {actual}"
            )
        else:
            print(
                f"FAIL: {model_code} | "
                f"Expected {expected} | Actual {actual}"
            )
            passed = False

        if actual is not None:
            quantity_quotes = [
                source["quote"]
                for source in item["quantity"]["sources"]
            ]

            print("Quantity evidence:", quantity_quotes)

    for item in items:
        quantity = item["quantity"]["decimal_value"]

        if quantity in INSURANCE_AMOUNTS:
            print(
                "FAIL: Insurance amount detected as BOQ quantity:",
                item["description"],
                quantity,
            )
            passed = False

    print("\nBOQ COMPARISON PASSED:", passed)
    print(
        "Numeric matching alone does not prove "
        "correct interpretation or full coverage."
    )

    return passed


def verify_exact_citations(result, document):
    pages = {
        page["pdf_page"]: page["text"]
        for page in document["pages"]
    }

    citations = []

    for item in result["boq_items"]:
        citations.extend(item["sources"])
        citations.extend(item["quantity"]["sources"])

    for requirement in result["technical_requirements"]:
        citations.extend(requirement["sources"])

    if not citations:
        return False

    for citation in citations:
        page_text = pages.get(citation["pdf_page"], "")

        if (
            citation["document_id"] != document["document_id"]
            or not citation["quote"].strip()
            or citation["quote"] not in page_text
        ):
            return False

    return True


async def main():
    print("====== 1. READING PDF ======")
    print("PDF:", PDF_PATH)

    if not PDF_PATH.is_file():
        raise FileNotFoundError(PDF_PATH)

    document = read_pdf(
        PDF_PATH,
        document_id="real-tender-001",
        role="TENDER",
    )

    selected_pages = [
        page
        for page in document["pages"]
        if page["pdf_page"] in TEST_PAGES
    ]

    if {p["pdf_page"] for p in selected_pages} != TEST_PAGES:
        raise ValueError("Could not find pages 5 and 6.")

    tender = {
        **document,
        "pages": selected_pages,
        "completeness": "INCOMPLETE",
        "completeness_basis": "UNKNOWN",
        "warnings": [
            *document["warnings"],
            "Only physical PDF pages 5 and 6 were analyzed.",
        ],
    }

    print("\n====== 2. PDF READER SUMMARY ======")

    for page in selected_pages:
        print(f"\nPAGE {page['pdf_page']}")
        print("Readability:", page["readability"])
        print("Recovered tables:", len(page["tables"]))
        print("Warnings:", page["warnings"])

        for line in page["text"].splitlines():
            if any(
                code.lower() in line.lower()
                for code in EXPECTED_BOQ
            ):
                print("MODEL LINE:", repr(line))

    if not any(page["text"].strip() for page in selected_pages):
        raise ValueError("No readable text found.")

    print("\n====== 3. RUN AGENT 2 ======")

    client = OpenAIAdapter()

    result = await extract_technical(
        tender,
        client=client,
        mode="AI",
    )

    print("Model:", result["provenance"]["model"])
    print("BOQ Status:", result["boq_status"])
    print("BOQ Review Reasons:", result["boq_review_reasons"])

    print("\n====== 4. BOQ ITEMS ======")

    for item in result["boq_items"]:
        print("\nID:", item["boq_item_id"])
        print("Description:", item["description"])
        print("Quantity:", item["quantity"]["decimal_value"])
        print("Needs Review:", item["needs_review"])
        print("Review Reasons:", item["review_reasons"])
        print("Sources:", item["sources"])
        print("Quantity Sources:", item["quantity"]["sources"])

    print("\n====== 5. TECHNICAL REQUIREMENTS ======")

    for requirement in result["technical_requirements"]:
        print("\nID:", requirement["technical_id"])
        print("Text:", requirement["text"])
        print("Category:", requirement["category"])
        print("Needs Review:", requirement["needs_review"])
        print("Sources:", requirement["sources"])

    comparison_passed = compare_boq(result["boq_items"])

    citations_valid = verify_exact_citations(
        result,
        document,
    )

    print("\n====== 6. CITATION VALIDATION ======")
    print("ALL CITATIONS VALID:", citations_valid)

    print("\n====== 7. WARNINGS ======")

    for warning in result["warnings"]:
        print("-", warning)

    output_path = (
        PROJECT_ROOT / "agent2_integration_result.json"
    )

    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n====== FINAL RESULT ======")
    print("BOQ numeric comparison:", comparison_passed)
    print("Exact citation validation:", citations_valid)
    print("JSON saved to:", output_path)
    print(
        "Results require review against the original PDF, "
        "especially table column relationships."
    )


if __name__ == "__main__":
    asyncio.run(main())
