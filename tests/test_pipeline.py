"""Real PDFs through all agents and validators, using only free fake LLMs."""
import copy
import json
import logging
from pathlib import Path
from unittest.mock import patch

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from agent3 import verification_output_schema
from orchestrator import analyze
from pdf_reader import read_pdf
from validation import validate_report, validate_shape
from models import Report

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def saved_scenarios():
    """Optional private-local replay; keep original paid responses/PDFs untouched."""
    root = Path(__file__).resolve().parents[1]
    old, recent = root / "output/ar_scenarios_api_audit.json", root / "output/ar_retest_d89396a_api_audit.json"
    if not old.is_file() or not recent.is_file():
        pytest.skip("Saved real API responses are optional local regression inputs.")
    runs = {r["scenario"]: r for r in json.loads(old.read_text(encoding="utf-8"))["runs"]}
    runs.update({r["scenario"]: r for r in json.loads(recent.read_text(encoding="utf-8"))["runs"]})
    return {case: runs[case] for case in ("case_101", "case_202", "case_303")}


@pytest.mark.asyncio
@pytest.mark.parametrize("case,expected", [
    ("case_101", {"SATISFIED": 11, "CONTRADICTED": 0, "MISSING_EVIDENCE": 0, "NEEDS_REVIEW": 3}),
    ("case_202", {"SATISFIED": 2, "CONTRADICTED": 8, "MISSING_EVIDENCE": 0, "NEEDS_REVIEW": 3}),
    ("case_303", {"SATISFIED": 3, "CONTRADICTED": 0, "MISSING_EVIDENCE": 0, "NEEDS_REVIEW": 10}),
])
async def test_saved_real_scenario_regressions_without_api(saved_scenarios, case, expected):
    run = saved_scenarios[case]
    clients = [FakeClient(call["payload"]) for call in run["calls"]]
    assert len(clients) == 3
    old_level = logging.root.manager.disable
    logging.disable(logging.WARNING)
    try:
        with patch("openai_adapter.OpenAIAdapter.generate", side_effect=AssertionError("Paid API forbidden")):
            report = await analyze(Path(run["tender"]), [Path(p) for p in run["company_files"]],
                                   reference_date="2026-10-31", mode="AI", synthetic_test=True,
                                   eligibility_client=clients[0], technical_client=clients[1],
                                   verification_client=clients[2])
    finally:
        logging.disable(old_level)
    assert [client.calls for client in clients] == [1, 1, 1]
    assert {status: sum(f["status"] == status for f in report["findings"]) for status in expected} == expected
    assert [i["quantity"]["decimal_value"] for i in report["technical"]["boq_items"]] == ["12", "8", "2"]
    findings = {(f["target_type"], f["target_id"]): f for f in report["findings"]}
    if case == "case_101":
        # The original dates, absence of arrears, both completed contracts and
        # both authorized brands support these outcomes within the simulation.
        for ident in ("R02", "R03", "R04", "R05", "R09"):
            assert findings[("ELIGIBILITY", ident)]["status"] == "SATISFIED"
    if case == "case_303":
        assert findings[("ELIGIBILITY", "R05")]["status"] == "NEEDS_REVIEW"
        assert findings[("TECHNICAL", "TECH-001")]["status"] == "NEEDS_REVIEW"
    report["warnings"].append("INFO: LOCAL REGRESSION using recorded responses; no new OpenAI API request.")
    output = Path(__file__).resolve().parents[1] / "output" / f"ar_{case}_local_regression.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


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
            "sources": [], "assessment": "UNCERTAIN",
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
        "sources": [{"line_id": "P001-L0001"}],
    }], "warnings": []}
    technical = technical_payload(tender, 1, [("B7030", "104")])
    results = [no_evidence_result("ELIGIBILITY", "REQ-1"), no_evidence_result("BOQ", "BOQ-1")]
    for line_number, result in enumerate(results, 1):
        result.update(evidence_found=True, sources=[{"line_id": f"D001-P001-L{line_number:04d}"}],
                      assessment="SUPPORTS", explanation="مدعوم بالمستند المرفق.")
    clients = [FakeClient(eligibility), FakeClient(technical), FakeClient({"results": results})]
    report = await analyze(tender_path, [company_path], reference_date="2026-10-26", mode="AI",
                           eligibility_client=clients[0], technical_client=clients[1], verification_client=clients[2])
    documents = [tender, read_pdf(company_path, document_id="company-001", role="COMPANY")]
    validate_report(report, documents)
    assert [client.calls for client in clients] == [1, 1, 1]
    assert len(report["findings"]) == 2
    assert [finding["status"] for finding in report["findings"]] == ["SATISFIED", "NEEDS_REVIEW"]
    assert all(finding["evidence"] for finding in report["findings"])
    assert report["technical"]["boq_items"][0]["quantity"]["decimal_value"] == "104"
    # Rechecking a report must reject a tampered, unsupported result.
    bad = copy.deepcopy(report)
    bad["findings"][1]["status"] = "SATISFIED"
    bad["findings"][1]["review_required"] = False
    bad["findings"][1]["uncertainty_reasons"] = []
    with pytest.raises(ValueError):
        validate_report(bad, documents)


@pytest.mark.asyncio
@pytest.mark.skipif(not (FIXTURES / "ida-335.pdf").is_file(), reason="Private local tender is optional.")
async def test_fake_ai_local_tender_end_to_end(tmp_path):
    tender_path = FIXTURES / "ida-335.pdf"
    company_paths = [FIXTURES / "01_company_profile.pdf", FIXTURES / "04_previous_work.pdf"]
    tender = read_pdf(tender_path, document_id="tender-001", role="TENDER")
    page4 = tender["pages"][3]
    registration_line = next(i for i, line in enumerate(page4["text"].splitlines(), 1)
                             if "السجل التجاري" in line)
    eligibility = {"requirements": [{
        "requirement_id": "REQ-1", "text": "صورة القيد في السجل التجاري سارية خلال العقد",
        "category": "REGISTRATION", "needs_review": False, "review_reasons": [],
        "sources": [{"line_id": f"P004-L{registration_line:04d}"}],
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
    company_line = next(i for i, line in enumerate(company["pages"][0]["text"].splitlines(), 1)
                        if "الفني داخل مقار" in line)
    results[1].update(evidence_found=True, sources=[{"line_id": f"D001-P001-L{company_line:04d}"}],
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


@pytest.mark.asyncio
async def test_changing_company_pdf_changes_all_four_findings(tmp_path):
    import re

    tender_path, company_path = tmp_path / "tender.pdf", tmp_path / "company.pdf"
    write_pdf(tender_path, ["Maintenance license must be valid."])
    eligibility = {"requirements": [{
        "requirement_id": "REQ-1", "text": "Maintenance license must be valid.",
        "category": "LICENSE", "needs_review": False, "review_reasons": [],
        "sources": [{"line_id": "P001-L0001"}],
    }], "warnings": []}
    technical = {"boq_status": "NEEDS_REVIEW", "boq_review_reasons": ["Tender completeness unknown."],
                 "boq_items": [], "technical_requirements": []}

    class CompanyEvidenceClient:
        # Always read the CURRENT company PDF lines. Python, not this fake,
        # determines whether a supported expiry is before the reference date.
        async def generate(self, *, instructions, input_data, output_schema):
            lines = input_data["documents"][0]["pages"][0]["lines"]
            line = next((line for line in lines if "Maintenance license" in line["text"]), None)
            result = no_evidence_result("ELIGIBILITY", "REQ-1")
            if line:
                expiry = re.search(r"\d{4}-\d{2}-\d{2}", line["text"])
                result.update(evidence_found=True, sources=[{"line_id": line["line_id"]}],
                              assessment="SUPPORTS" if expiry else "UNCERTAIN",
                              expiry_date=expiry.group() if expiry else None)
            return {"payload": {"results": [result]}, "provider": "fake", "model": "offline", "usage": None}

    findings = []
    for text, expected in [
        ("Maintenance license expires on 2027-01-01.", "SATISFIED"),
        ("Maintenance license expires on 2025-01-01.", "CONTRADICTED"),
        ("Company profile only; no supporting license.", "MISSING_EVIDENCE"),
        ("Maintenance license expiry is unclear.", "NEEDS_REVIEW"),
    ]:
        write_pdf(company_path, [text])
        report = await analyze(tender_path, [company_path], reference_date="2026-10-26", mode="AI",
                               eligibility_client=FakeClient(eligibility), technical_client=FakeClient(technical),
                               verification_client=CompanyEvidenceClient(), company_documents_complete=True)
        finding = report["findings"][0]
        assert finding["status"] == expected
        assert report["documents"][1]["completeness_basis"] == "USER_CONFIRMED"
        if finding["evidence"]:
            assert text == finding["evidence"][0]["quote"]
        findings.append(finding)
    assert len({finding["status"] for finding in findings}) == 4

    # The same missing document is not a proven absence without explicit confirmation.
    write_pdf(company_path, ["Company profile only; no supporting license."])
    report = await analyze(tender_path, [company_path], reference_date="2026-10-26", mode="AI",
                           eligibility_client=FakeClient(eligibility), technical_client=FakeClient(technical),
                           verification_client=CompanyEvidenceClient())
    assert report["findings"][0]["status"] == "NEEDS_REVIEW"
    assert report["documents"][1]["completeness"] == "UNKNOWN"


@pytest.mark.asyncio
@pytest.mark.skipif(not (FIXTURES / "ida-335.pdf").is_file(), reason="Private local tender is optional.")
async def test_real_company_quarterly_service_contradicts_tender_monthly_requirement():
    from agent2 import extract_technical
    from agent3 import verify_company

    tender = read_pdf(FIXTURES / "ida-335.pdf", document_id="tender-001", role="TENDER")
    company = read_pdf(FIXTURES / "01_company_profile.pdf", document_id="company-001", role="COMPANY")
    line_number = next(i for i, line in enumerate(tender["pages"][6]["text"].splitlines(), 1)
                       if "الصيانة الدورية مرة كل شهر" in line)
    payload = {"boq_status": "NEEDS_REVIEW", "boq_review_reasons": ["Tender coverage unknown."],
               "boq_items": [], "technical_requirements": [{
                   "technical_id": "TECH-MONTHLY", "text": "الصيانة الدورية مرة كل شهر",
                   "category": "SPECIFICATION", "needs_review": False, "review_reasons": [],
                   "sources": [{"line_id": f"P007-L{line_number:04d}"}],
               }]}
    technical = await extract_technical(tender, client=FakeClient(payload), mode="AI")
    assert not technical["technical_requirements"][0]["needs_review"]
    company_line = next(i for i, line in enumerate(company["pages"][0]["text"].splitlines(), 1)
                        if "ربع سنوية" in line)
    result = no_evidence_result("TECHNICAL", "TECH-MONTHLY")
    result.update(evidence_found=True, sources=[{"line_id": f"D001-P001-L{company_line:04d}"}],
                  assessment="CONTRADICTS", explanation="المطلوب شهري، بينما مستند الشركة ينص على صيانة ربع سنوية.")
    output = await verify_company({"requirements": []}, technical, [company], reference_date="2026-10-26",
                                  client=FakeClient({"results": [result]}), mode="AI")
    assert output["findings"][0]["status"] == "CONTRADICTED"
    assert "ربع سنوية" in output["findings"][0]["evidence"][0]["quote"]
