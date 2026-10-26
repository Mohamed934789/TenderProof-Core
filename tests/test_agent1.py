import copy

import pytest

from agent1 import extract_eligibility
from validation import validate_eligibility


@pytest.fixture
def sample_tender():
    return {
        "document_id": "tender-acceptance-001", "filename": "acceptance_tender.pdf",
        "role": "TENDER", "completeness": "COMPLETE", "completeness_basis": "TEST_FIXTURE",
        "pages": [{"pdf_page": 1,
                   "text": "يجب تقديم سجل تجاري ساري المفعول. يجب تقديم رخصة صيانة سارية.",
                   "readability": "READABLE", "extraction_method": "NATIVE_TEXT",
                   "tables": [], "warnings": []}], "warnings": [],
    }


def payload_for(tender):
    return {"requirements": [{
        "requirement_id": "REQ-001", "text": "يجب تقديم سجل تجاري ساري المفعول",
        "category": "REGISTRATION", "needs_review": False, "review_reasons": [],
        "sources": [{"document_id": tender["document_id"], "pdf_page": 1,
                     "quote": "يجب تقديم سجل تجاري ساري المفعول"}],
    }], "warnings": []}


class FakeClient:
    def __init__(self, payload):
        self.payload, self.calls = payload, 0

    async def generate(self, **kwargs):
        self.calls += 1
        self.schema = kwargs["output_schema"]
        return {"payload": copy.deepcopy(self.payload), "provider": "fake", "model": "test", "usage": None}


@pytest.mark.asyncio
async def test_extract_eligibility_mock_and_rules(sample_tender):
    client = FakeClient(payload_for(sample_tender))
    result = await extract_eligibility(sample_tender, client=client, mode="MOCK")
    assert result["requirements"] == []
    assert result["warnings"]
    assert client.calls == 0
    validate_eligibility(result, sample_tender)


@pytest.mark.asyncio
async def test_provenance_and_mode(sample_tender):
    result = await extract_eligibility(sample_tender, mode="MOCK")
    assert result["provenance"]["mode"] == "MOCK"
    assert result["provenance"]["provider"] == "mock"


@pytest.mark.asyncio
async def test_ai_extracts_eligibility_and_preserves_citation(sample_tender):
    client = FakeClient(payload_for(sample_tender))
    result = await extract_eligibility(sample_tender, client=client, mode="AI")
    validate_eligibility(result, sample_tender)
    assert result["requirements"][0]["sources"][0]["pdf_page"] == 1
    assert result["provenance"]["provider"] == "fake"
    assert client.calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [("quote", "ترخيص غير موجود"), ("pdf_page", 2),
                                       ("document_id", "wrong-document")])
async def test_ai_rejects_fabricated_citations(sample_tender, field, value):
    payload = payload_for(sample_tender)
    payload["requirements"][0]["sources"][0][field] = value
    with pytest.raises(ValueError):
        await extract_eligibility(sample_tender, client=FakeClient(payload), mode="AI")


@pytest.mark.asyncio
async def test_partial_page_requires_review(sample_tender):
    sample_tender["pages"][0]["readability"] = "PARTIAL"
    result = await extract_eligibility(sample_tender, client=FakeClient(payload_for(sample_tender)), mode="AI")
    assert result["requirements"][0]["needs_review"]
    assert result["requirements"][0]["review_reasons"]
    assert result["warnings"]


@pytest.mark.asyncio
@pytest.mark.parametrize("malformation", ["missing", "duplicate", "category", "sources", "bool"])
async def test_ai_rejects_invalid_contract(sample_tender, malformation):
    payload = payload_for(sample_tender)
    req = payload["requirements"][0]
    if malformation == "missing":
        del req["review_reasons"]
    elif malformation == "duplicate":
        payload["requirements"].append(copy.deepcopy(req))
    elif malformation == "category":
        req["category"] = "MADE_UP"
    elif malformation == "sources":
        req["sources"] = []
    else:
        req["needs_review"] = "false"
    with pytest.raises(ValueError):
        await extract_eligibility(sample_tender, client=FakeClient(payload), mode="AI")


@pytest.mark.asyncio
async def test_invalid_mode_and_missing_client(sample_tender):
    with pytest.raises(ValueError):
        await extract_eligibility(sample_tender, mode="wrong")
    with pytest.raises(ValueError):
        await extract_eligibility(sample_tender, mode="AI")
