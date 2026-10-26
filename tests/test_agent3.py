"""Regression checks for the evidence agent; every AI client here is a local fake."""
import asyncio
import copy

import pytest

from agent3 import verify_company

PAGE_TEXT = "ترخيص صيانة. ينتهي الترخيص في 15 أكتوبر 2026"


def result_for(kind="ELIGIBILITY", ident="REQ-002", **changes):
    result = {"target_type": kind, "target_id": ident, "evidence_found": True,
              "document_id": "nile-license", "pdf_page": 1, "quote": PAGE_TEXT,
              "assessment": "SUPPORTS", "explanation": "الدليل يدعم المتطلب.",
              "expiry_date": "2026-10-15", "offered_quantity": None, "offered_unit": None}
    result.update(changes)
    return result


def no_evidence():
    return result_for(evidence_found=False, document_id=None, pdf_page=None, quote=None,
                      assessment="UNCERTAIN", expiry_date=None)


class FakeClient:
    def __init__(self, results):
        self.results, self.calls = results, 0

    async def generate(self, **kwargs):
        self.calls += 1
        return {"payload": {"results": copy.deepcopy(self.results)}, "provider": "fake",
                "model": "fake-1", "usage": None}


def inputs(completeness="COMPLETE", readability="READABLE", text=PAGE_TEXT):
    provenance = {"mode": "AI", "provider": "fake", "model": "fake-1", "prompt_version": "t"}
    eligibility = {"requirements": [{
        "requirement_id": "REQ-002", "text": "ترخيص صيانة ساري في تاريخ التقييم",
        "category": "LICENSE", "needs_review": False, "review_reasons": [], "sources": [],
    }], "provenance": provenance, "warnings": []}
    technical = {"boq_status": "NOT_FOUND", "boq_review_reasons": [], "boq_items": [],
                 "technical_requirements": [], "provenance": provenance, "warnings": []}
    docs = [{"document_id": "nile-license", "filename": "license.pdf", "role": "COMPANY",
             "completeness": completeness, "completeness_basis": "TEST_FIXTURE", "warnings": [],
             "pages": [{"pdf_page": 1, "text": text, "readability": readability,
                        "extraction_method": "NATIVE_TEXT", "tables": [], "warnings": []}]}]
    return eligibility, technical, docs


def run(results, *, mode="AI", **kwargs):
    eligibility, technical, docs = inputs(**kwargs)
    client = FakeClient(results)
    output = asyncio.run(verify_company(eligibility, technical, docs, reference_date="2026-11-01",
                                       client=client, mode=mode))
    return output["findings"][0], client


def test_expired_license_is_contradicted():
    finding, _ = run([result_for()])
    assert finding["status"] == "CONTRADICTED"
    assert finding["evidence"][0]["pdf_page"] == 1


def test_valid_license_is_satisfied():
    text = "ينتهي الترخيص في 1 يناير 2027"
    finding, _ = run([result_for(quote=text, expiry_date="2027-01-01")], text=text)
    assert finding["status"] == "SATISFIED"


def test_ungrounded_expiry_date_needs_review():
    finding, _ = run([result_for(expiry_date="2027-01-01")])
    assert finding["status"] == "NEEDS_REVIEW"


def test_fabricated_quote_needs_review():
    finding, _ = run([result_for(quote="جملة مش موجودة في الصفحة")])
    assert finding["status"] == "NEEDS_REVIEW"
    assert finding["evidence"] == []


def test_no_evidence_in_complete_docs_is_missing():
    assert run([no_evidence()])[0]["status"] == "MISSING_EVIDENCE"


@pytest.mark.parametrize("quality", ["UNREADABLE", "PARTIAL"])
def test_no_evidence_in_uncertain_docs_needs_review(quality):
    assert run([no_evidence()], readability=quality)[0]["status"] == "NEEDS_REVIEW"


def test_mock_never_calls_llm():
    finding, client = run([], mode="MOCK")
    assert client.calls == 0
    assert finding["status"] == "NEEDS_REVIEW"


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "unknown", "wrong-type"])
def test_invalid_result_coverage_is_rejected(mutation):
    results = [result_for()]
    if mutation == "missing":
        results = []
    elif mutation == "duplicate":
        results.append(result_for())
    elif mutation == "unknown":
        results[0]["target_id"] = "wrong"
    else:
        results[0]["target_type"] = "TECHNICAL"
    with pytest.raises(ValueError):
        run(results)


def run_boq(offered_quantity, offered_unit="طابعة", quote=None, target_review=False):
    eligibility, technical, docs = inputs()
    eligibility["requirements"] = []
    quote = quote or f"نقدم صيانة {offered_quantity or 'عدد غير محدد'} {offered_unit or ''} Xerox B7070"
    docs[0]["pages"][0]["text"] = quote
    technical["boq_items"] = [{
        "boq_item_id": "BOQ-1", "description": "صيانة طابعات Xerox B7070",
        "quantity": {"raw_text": "20", "decimal_value": "20", "sources": []},
        "unit": "طابعة", "unit_normalized": None, "table_id": None,
        "needs_review": target_review, "review_reasons": ["table uncertainty"] if target_review else [],
        "sources": [],
    }]
    result = result_for("BOQ", "BOQ-1", quote=quote, expiry_date=None,
                        offered_quantity=offered_quantity, offered_unit=offered_unit)
    output = asyncio.run(verify_company(eligibility, technical, docs, reference_date="2026-11-01",
                                       client=FakeClient([result]), mode="AI"))
    return output["findings"][0]


def test_boq_quantity_too_low_is_contradicted():
    assert run_boq("15")["status"] == "CONTRADICTED"


def test_boq_quantity_enough_is_satisfied():
    assert run_boq("20")["status"] == "SATISFIED"


def test_boq_unit_mismatch_needs_review():
    assert run_boq("20", offered_unit="جهاز")["status"] == "NEEDS_REVIEW"


def test_boq_missing_quantity_needs_review():
    assert run_boq(None)["status"] == "NEEDS_REVIEW"


@pytest.mark.parametrize("quantity", ["NaN", "Infinity", "-1", "999"])
def test_boq_ungrounded_and_invalid_quantities_need_review(quantity):
    assert run_boq(quantity, quote="نقدم صيانة 20 طابعة Xerox B7070")["status"] == "NEEDS_REVIEW"


def test_boq_model_number_does_not_prove_quantity():
    assert run_boq("7070", quote="نقدم صيانة طابعة Xerox B7070")["status"] == "NEEDS_REVIEW"


def test_uncertain_target_cannot_be_satisfied():
    assert run_boq("20", target_review=True)["status"] == "NEEDS_REVIEW"


def test_completeness_without_basis_cannot_prove_missing():
    eligibility, technical, docs = inputs()
    docs[0]["completeness_basis"] = "UNKNOWN"
    output = asyncio.run(verify_company(eligibility, technical, docs, reference_date="2026-11-01",
                                       client=FakeClient([no_evidence()]), mode="AI"))
    assert output["findings"][0]["status"] == "NEEDS_REVIEW"


def test_partial_evidence_page_cannot_prove_compliance():
    assert run([result_for()], readability="PARTIAL")[0]["status"] == "NEEDS_REVIEW"


def test_arabic_indic_expiry_is_compared_in_python():
    quote = "ينتهي الترخيص في ١٥ أكتوبر ٢٠٢٦"
    assert run([result_for(quote=quote)], text=quote)[0]["status"] == "CONTRADICTED"
