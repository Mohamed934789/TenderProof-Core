import asyncio

from agent3 import verify_company

PAGE_TEXT = "ترخيص صيانة. ينتهي الترخيص في 15 أكتوبر 2026"


def _run(results, completeness="COMPLETE", readability="READABLE"):
    class C:
        async def generate(self, *, instructions, input_data, output_schema):
            return {"payload": {"results": results}, "provider": "fake",
                    "model": "fake-1", "usage": None}

    prov = {"mode": "MOCK", "provider": "fake",
            "model": "fake-1", "prompt_version": "t"}
    eligibility = {
        "requirements": [{
            "requirement_id": "REQ-002",
            "text": "ترخيص صيانة ساري في تاريخ التقييم",
            "category": "LICENSE", "needs_review": False,
            "review_reasons": [], "sources": [],
        }],
        "provenance": prov, "warnings": [],
    }
    technical = {
        "boq_status": "NOT_FOUND", "boq_review_reasons": [],
        "boq_items": [], "technical_requirements": [],
        "provenance": prov, "warnings": [],
    }
    docs = [{
        "document_id": "nile-license", "filename": "license.pdf",
        "role": "COMPANY", "completeness": completeness,
        "completeness_basis": "TEST_FIXTURE", "warnings": [],
        "pages": [{
            "pdf_page": 1, "text": PAGE_TEXT, "readability": readability,
            "extraction_method": "NATIVE_TEXT", "tables": [], "warnings": [],
        }],
    }]
    out = asyncio.run(verify_company(
        eligibility, technical, docs,
        reference_date="2026-11-01", client=C(), mode="MOCK"))
    return out["findings"][0]


def test_expired_license_is_contradicted():
    f = _run([{"target_id": "REQ-002", "evidence_found": True,
               "document_id": "nile-license", "pdf_page": 1,
               "quote": "ينتهي الترخيص في 15 أكتوبر 2026",
               "expiry_date": "2026-10-15"}])
    assert f["target_id"] == "REQ-002"
    assert f["status"] == "CONTRADICTED"
    assert f["evidence"][0]["pdf_page"] == 1


def test_valid_license_is_satisfied():
    f = _run([{"target_id": "REQ-002", "evidence_found": True,
               "document_id": "nile-license", "pdf_page": 1,
               "quote": "ينتهي الترخيص في 15 أكتوبر 2026",
               "expiry_date": "2027-01-01"}])
    assert f["status"] == "SATISFIED"


def test_fabricated_quote_needs_review():
    f = _run([{"target_id": "REQ-002", "evidence_found": True,
               "document_id": "nile-license", "pdf_page": 1,
               "quote": "جملة مش موجودة في الصفحة",
               "expiry_date": None}])
    assert f["status"] == "NEEDS_REVIEW"


def test_no_evidence_in_complete_docs_is_missing():
    f = _run([{"target_id": "REQ-002", "evidence_found": False}])
    assert f["status"] == "MISSING_EVIDENCE"


def test_no_evidence_in_unreadable_docs_needs_review():
    f = _run([{"target_id": "REQ-002", "evidence_found": False}],
             readability="UNREADABLE")
    assert f["status"] == "NEEDS_REVIEW"


def _run_boq(offered_quantity, offered_unit="طابعة"):
    class C:
        async def generate(self, *, instructions, input_data, output_schema):
            return {"payload": {"results": [{
                "target_id": "BOQ-1", "evidence_found": True,
                "document_id": "nile-offer", "pdf_page": 1,
                "quote": "نقدم صيانة طابعات Xerox B7070",
                "offered_quantity": offered_quantity,
                "offered_unit": offered_unit,
            }]}, "provider": "fake", "model": "fake-1", "usage": None}

    prov = {"mode": "MOCK", "provider": "fake",
            "model": "fake-1", "prompt_version": "t"}
    eligibility = {"requirements": [], "provenance": prov, "warnings": []}
    technical = {
        "boq_status": "FOUND", "boq_review_reasons": [],
        "technical_requirements": [],
        "boq_items": [{
            "boq_item_id": "BOQ-1",
            "description": "صيانة طابعات Xerox B7070",
            "quantity": {"raw_text": "20", "decimal_value": "20",
                         "sources": []},
            "unit": "طابعة", "unit_normalized": None, "table_id": None,
            "needs_review": False, "review_reasons": [], "sources": [],
        }],
        "provenance": prov, "warnings": [],
    }
    docs = [{
        "document_id": "nile-offer", "filename": "offer.pdf",
        "role": "COMPANY", "completeness": "COMPLETE",
        "completeness_basis": "TEST_FIXTURE", "warnings": [],
        "pages": [{
            "pdf_page": 1, "text": "نقدم صيانة طابعات Xerox B7070",
            "readability": "READABLE", "extraction_method": "NATIVE_TEXT",
            "tables": [], "warnings": [],
        }],
    }]
    out = asyncio.run(verify_company(
        eligibility, technical, docs,
        reference_date="2026-11-01", client=C(), mode="MOCK"))
    return out["findings"][0]


def test_boq_quantity_too_low_is_contradicted():
    assert _run_boq("15")["status"] == "CONTRADICTED"


def test_boq_quantity_enough_is_satisfied():
    assert _run_boq("20")["status"] == "SATISFIED"


def test_boq_unit_mismatch_needs_review():
    assert _run_boq("20", offered_unit="جهاز")["status"] == "NEEDS_REVIEW"


def test_boq_missing_quantity_needs_review():
    assert _run_boq(None)["status"] == "NEEDS_REVIEW"