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
        "sources": [{"line_id": "P001-L0001"}],
    }], "warnings": []}


class FakeClient:
    def __init__(self, payload):
        self.payload, self.calls = payload, 0

    async def generate(self, **kwargs):
        self.calls += 1
        self.schema = kwargs["output_schema"]
        self.input_data = kwargs["input_data"]
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
    assert result["requirements"][0]["sources"] == [{
        "document_id": sample_tender["document_id"], "pdf_page": 1,
        "quote": sample_tender["pages"][0]["text"],
    }]
    assert client.input_data["pages"][0]["lines"][0]["line_id"] == "P001-L0001"
    assert result["provenance"]["provider"] == "fake"
    assert client.calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [("quote", "ترخيص غير موجود"), ("pdf_page", 2),
                                       ("document_id", "wrong-document")])
async def test_ai_rejects_model_supplied_citation_fields(sample_tender, field, value):
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


@pytest.mark.asyncio
async def test_all_requirements_and_multiple_sources_preserve_original_text(sample_tender):
    sample_tender["pages"][0]["text"] = "  يجب  تقديم سجل تجاري.\t\n\n رخصة صيانة مطلوبة. "
    second_page = copy.deepcopy(sample_tender["pages"][0])
    second_page.update(pdf_page=2, text="\nترخيص صيانة ساري.\n")
    sample_tender["pages"].append(second_page)
    payload = payload_for(sample_tender)
    payload["requirements"][0]["sources"] = [
        {"line_id": "P001-L0001"}, {"line_id": "P002-L0002"}, {"line_id": "P001-L0001"},
    ]
    second_requirement = copy.deepcopy(payload["requirements"][0])
    second_requirement.update(requirement_id="REQ-002", category="LICENSE",
                              sources=[{"line_id": "P001-L0003"}])
    payload["requirements"].append(second_requirement)
    result = await extract_eligibility(sample_tender, client=FakeClient(payload), mode="AI")
    validate_eligibility(result, sample_tender)
    assert result["requirements"][0]["sources"] == [
        {"document_id": sample_tender["document_id"], "pdf_page": 1,
         "quote": "  يجب  تقديم سجل تجاري.\t"},
        {"document_id": sample_tender["document_id"], "pdf_page": 2,
         "quote": "ترخيص صيانة ساري."},
    ]
    assert result["requirements"][1]["sources"][0]["quote"] == " رخصة صيانة مطلوبة. "


@pytest.mark.asyncio
@pytest.mark.parametrize("requirement_index,source_index", [(0, 0), (0, 1), (1, 1)])
async def test_nonexistent_line_rejected_in_every_requirement_and_source(sample_tender, requirement_index, source_index):
    payload = payload_for(sample_tender)
    payload["requirements"].append(copy.deepcopy(payload["requirements"][0]))
    payload["requirements"][1]["requirement_id"] = "REQ-002"
    for requirement in payload["requirements"]:
        requirement["sources"] = [{"line_id": "P001-L0001"}, {"line_id": "P001-L0001"}]
    payload["requirements"][requirement_index]["sources"][source_index] = {"line_id": "P001-L9999"}
    with pytest.raises(ValueError, match="Unknown source line"):
        await extract_eligibility(sample_tender, client=FakeClient(payload), mode="AI")


@pytest.mark.asyncio
async def test_approximate_quote_still_fails_validation(sample_tender):
    sample_tender["pages"][0]["text"] = "يجب  تقديم سجل تجاري.\nترخيص صيانة مطلوب."
    payload = payload_for(sample_tender)
    payload["requirements"][0]["sources"].append({"line_id": "P001-L0002"})
    result = await extract_eligibility(sample_tender, client=FakeClient(payload), mode="AI")
    validate_eligibility(result, sample_tender)
    result["requirements"][0]["sources"][1]["quote"] = "ترخيص صيانة غير موجود."
    with pytest.raises(ValueError, match="Citation quote was not found"):
        validate_eligibility(result, sample_tender)
    result["requirements"][0]["sources"][1]["quote"] = "ترخيص صيانة مطلوب."
    result["requirements"][0]["sources"][0]["quote"] = "يجب تقديم سجل تجاري."
    with pytest.raises(ValueError, match="Citation quote was not found"):
        validate_eligibility(result, sample_tender)
