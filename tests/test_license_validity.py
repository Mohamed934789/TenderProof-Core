"""Full-agent regressions: incorrect model support must not bypass temporal facts."""
import asyncio
import copy
import pytest
from agent3 import verify_company


@pytest.mark.parametrize("text,expiry,expected", [
    ("License valid from 2027-01-01 until 2028-01-01.", "2028-01-01", "CONTRADICTED"),
    ("ترخيص. تاريخ بدء السريان: ١ يناير ٢٠٢٧\nينتهي: ١ يناير ٢٠٢٨", "2028-01-01", "CONTRADICTED"),
    ("License valid from 2026-11-01 until 2028-01-01.", "2028-01-01", "SATISFIED"),
    ("License valid from 2026-01-01 until 2028-01-01.", "2028-01-01", "SATISFIED"),
    ("License valid from 2027-02-30 until 2028-01-01.", "2028-01-01", "NEEDS_REVIEW"),
    ("License valid from 2025-01-01.\nLicense valid from 2027-01-01.\nExpires 2028-01-01.", "2028-01-01", "NEEDS_REVIEW"),
    ("License valid from 2026-01-01 until 2025-01-01.", "2025-01-01", "NEEDS_REVIEW"),
])
def test_temporal_evidence_overrides_incorrect_model_support(text, expiry, expected):
    provenance = dict(mode="AI", provider="fake", model="offline", prompt_version="test")
    eligibility = dict(requirements=[dict(requirement_id="R1", text="A valid activity license is required.",
        category="LICENSE", needs_review=False, review_reasons=[], sources=[])], provenance=provenance, warnings=[])
    technical = dict(boq_status="NOT_FOUND", boq_review_reasons=[], boq_items=[], technical_requirements=[], provenance=provenance, warnings=[])
    document = dict(document_id="company", filename="fictional.pdf", role="COMPANY", completeness="COMPLETE",
        completeness_basis="TEST_FIXTURE", warnings=[], pages=[dict(pdf_page=1, text=text, readability="READABLE",
        extraction_method="NATIVE_TEXT", tables=[], warnings=[])])
    result = dict(target_type="ELIGIBILITY", target_id="R1", evidence_found=True,
        sources=[{"line_id": f"D001-P001-L{i:04d}"} for i in range(1, len(text.splitlines()) + 1)],
        assessment="SUPPORTS", explanation="Deliberately incorrect model support where dates conflict.",
        expiry_date=expiry, offered_quantity=None, offered_unit=None)
    class Fake:
        async def generate(self, **kwargs):
            return dict(payload={"results": [copy.deepcopy(result)]}, provider="fake", model="offline")
    report = asyncio.run(verify_company(eligibility, technical, [document], reference_date="2026-11-01", client=Fake(), mode="AI"))
    assert report["findings"][0]["status"] == expected

