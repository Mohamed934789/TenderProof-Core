"""Real PDFs through all agents and validators, using only free fake LLMs."""
import copy
import json
from pathlib import Path

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from agent3 import verification_output_schema
from orchestrator import analyze
from pdf_reader import read_pdf
from validation import validate_report, validate_shape
from models import Report

FIXTURES = Path(__file__).parent / "fixtures"


class FakeClient:
    def __init__(self, payload):
        self.payload, self.calls = payload, 0

    async def generate(self, *, instructions, input_data, output_schema):
        self.calls += 1
        return {"payload": copy.deepcopy(self.payload), "provider": "fake", "model": "offline",
                "usage": None}


def write_pdf(path, lines):
    writer = PdfWriter()
    page = writer.add_blank_page(width=595, height=842)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                             NameObject("/Subtype"): NameObject("/Type1"),
                             NameObject("/BaseFont"): NameObject("/Helvetica")})
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({
        NameObject("/F1"): writer._add_object(font)})})
    stream = DecodedStreamObject()
    stream.set_data(("BT /F1 12 Tf 40 760 Td " + " ".join(
        f"({line}) Tj 0 -20 Td" for line in lines) + " ET").encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    writer.write(path)


def technical_payload(tender, page_number, descriptions_and_quantities):
    page = next(p for p in tender["pages"] if p["pdf_page"] == page_number)
    items = []
    for ident, (model, quantity) in enumerate(descriptions_and_quantities, 1):
        line_number, text = next((i, line) for i, line in enumerate(page["text"].splitlines(), 1)
                                 if model.lower() in line.lower())
        reference = {"line_id": f"P{page_number:03d}-L{line_number:04d}"}
        items.append({"boq_item_id": f"BOQ-{ident}", "description": model,
                      "quantity": {"raw_text": quantity, "decimal_value": quantity, "sources": [reference]},
                      "unit": None, "unit_normalized": None, "table_id": None,
                      "needs_review": False, "review_reasons": [], "sources": [reference]})
    return {"boq_status": "FOUND", "boq_review_reasons": [], "boq_items": items,
            "technical_requirements": []}


def no_evidence_result(kind, ident):
    return {"target_type": kind, "target_id": ident, "evidence_found": False,
            "document_id": None, "pdf_page": None, "quote": None, "assessment": "UNCERTAIN",
            "explanation": "المستندات لا تثبت استيفاء المتطلب.", "expiry_date": None,
            "offered_quantity": None, "offered_unit": None}


@pytest.mark.asyncio
async def test_mock_all_real_public_documents_without_client():
    report = await analyze(FIXTURES / "arabic_table.pdf",
                           [FIXTURES / "01_company_profile.pdf", FIXTURES / "04_previous_work.pdf"],
                           reference_date="2026-10-26")
    validate_shape(report, Report)
    assert len(report["documents"]) == 3
    assert report["mode"] == "MOCK"
    assert report["technical"]["boq_status"] == "NEEDS_REVIEW"
    assert not report["coverage_confirmed"]
    assert any("page 2:" in warning for warning in report["warnings"])


@pytest.mark.asyncio
async def test_fake_ai_full_pipeline_on_generated_pdf(tmp_path):
    tender_path, company_path = tmp_path / "tender.pdf", tmp_path / "company.pdf"
    write_pdf(tender_path, ["Commercial registration required.", "104 Xerox B7030 printer"])
    write_pdf(company_path, ["Commercial registration certificate.", "We offer 104 printer Xerox B7030."])
    tender = read_pdf(tender_path, document_id="tender-001", role="TENDER")
    eligibility = {"requirements": [{
        "requirement_id": "REQ-1", "text": "Commercial registration required.",
        "category": "REGISTRATION", "needs_review": False, "review_reasons": [],
        "sources": [{"document_id": "tender-001", "pdf_page": 1, "quote": "Commercial registration required."}],
    }], "warnings": []}
    technical = technical_payload(tender, 1, [("B7030", "104")])
    results = [no_evidence_result("ELIGIBILITY", "REQ-1"), no_evidence_result("BOQ", "BOQ-1")]
    for result, quote in zip(results, ["Commercial registration certificate.", "We offer 104 printer Xerox B7030."]):
        result.update(evidence_found=True, document_id="company-001", pdf_page=1, quote=quote,
                      assessment="SUPPORTS", explanation="مدعوم بالمستند المرفق.")
    clients = [FakeClient(eligibility), FakeClient(technical), FakeClient({"results": results})]
    report = await analyze(tender_path, [company_path], reference_date="2026-10-26", mode="AI",
                           eligibility_client=clients[0], technical_client=clients[1], verification_client=clients[2])
    documents = [tender, read_pdf(company_path, document_id="company-001", role="COMPANY")]
    validate_report(report, documents)
    assert [client.calls for client in clients] == [1, 1, 1]
    assert len(report["findings"]) == 2
    assert all(finding["status"] == "NEEDS_REVIEW" for finding in report["findings"])
    assert all(finding["evidence"] for finding in report["findings"])
    assert report["technical"]["boq_items"][0]["quantity"]["decimal_value"] == "104"
    # Rechecking a report must reject a tampered, unsupported result.
    bad = copy.deepcopy(report)
    bad["findings"][0]["status"] = "SATISFIED"
    bad["findings"][0]["review_required"] = False
    bad["findings"][0]["uncertainty_reasons"] = []
    with pytest.raises(ValueError):
        validate_report(bad, documents)


@pytest.mark.asyncio
@pytest.mark.skipif(not (FIXTURES / "ida-335.pdf").is_file(), reason="Private local tender is optional.")
async def test_fake_ai_local_tender_end_to_end(tmp_path):
    tender_path = FIXTURES / "ida-335.pdf"
    company_paths = [FIXTURES / "01_company_profile.pdf", FIXTURES / "04_previous_work.pdf"]
    tender = read_pdf(tender_path, document_id="tender-001", role="TENDER")
    page4 = tender["pages"][3]
    quote = next(line for line in page4["text"].splitlines() if "السجل التجاري" in line)
    eligibility = {"requirements": [{
        "requirement_id": "REQ-1", "text": "صورة القيد في السجل التجاري سارية خلال العقد",
        "category": "REGISTRATION", "needs_review": False, "review_reasons": [],
        "sources": [{"document_id": "tender-001", "pdf_page": 4, "quote": quote}],
    }], "warnings": []}
    expected = [("B7030", "104"), ("C9070", "2"), ("Tx-4100", "1")]
    technical = technical_payload(tender, 6, expected)
    # Independent technical commitment, separate from item counts and prices.
    line_number, line = next((i, text) for i, text in enumerate(tender["pages"][5]["text"].splitlines(), 1)
                             if "تقديم الدعم الفني الكامل" in text)
    technical["technical_requirements"] = [{
        "technical_id": "TECH-1", "text": "تقديم الدعم الفني الكامل طوال مدة التعاقد",
        "category": "SPECIFICATION", "needs_review": False, "review_reasons": [],
        "sources": [{"line_id": f"P006-L{line_number:04d}"}],
    }]
    results = [no_evidence_result("ELIGIBILITY", "REQ-1"), no_evidence_result("TECHNICAL", "TECH-1")]
    results.extend(no_evidence_result("BOQ", f"BOQ-{index}") for index in range(1, 4))
    company = read_pdf(company_paths[0], document_id="company-001", role="COMPANY")
    company_quote = next(line for line in company["pages"][0]["text"].splitlines() if "الفني داخل مقار" in line)
    results[1].update(evidence_found=True, document_id="company-001", pdf_page=1, quote=company_quote,
                      assessment="UNCERTAIN", explanation="وصف النشاط وحده لا يثبت كل الالتزام الفني.")
    clients = [FakeClient(eligibility), FakeClient(technical), FakeClient({"results": results})]
    report = await analyze(tender_path, company_paths, reference_date="2026-10-26", mode="AI",
                           eligibility_client=clients[0], technical_client=clients[1], verification_client=clients[2])
    docs = [tender, company, read_pdf(company_paths[1], document_id="company-002", role="COMPANY")]
    validate_report(report, docs)
    assert len(tender["pages"]) == 18
    assert [client.calls for client in clients] == [1, 1, 1]
    assert [item["quantity"]["decimal_value"] for item in report["technical"]["boq_items"]] == ["104", "2", "1"]
    assert report["technical"]["boq_status"] == "NEEDS_REVIEW"
    assert all(item["needs_review"] for item in report["technical"]["boq_items"])
    assert all(source["pdf_page"] == 6 for item in report["technical"]["boq_items"] for source in item["sources"])
    assert len(report["findings"]) == 5
    assert all(finding["status"] == "NEEDS_REVIEW" for finding in report["findings"])
    assert report["findings"][1]["evidence"][0]["document_id"] == "company-001"
    assert not report["coverage_confirmed"]
    assert report["warnings"]
    # Private, ignored artifact for reviewing this run; never stored in Git.
    artifact = Path("output/integration-fake-ai-report.json")
    artifact.parent.mkdir(exist_ok=True)
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
