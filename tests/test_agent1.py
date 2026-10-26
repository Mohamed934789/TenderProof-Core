import pytest
from agent1 import extract_eligibility
from models import DocumentPages

@pytest.fixture
def sample_tender() -> DocumentPages:
    return {
        "document_id": "tender-acceptance-001",
        "filename": "acceptance_tender.pdf",
        "role": "TENDER",
        "completeness": "COMPLETE",
        "completeness_basis": "TEST_FIXTURE",
        "pages": [
            {
                "pdf_page": 1,
                "text": "يجب تقديم سجل تجاري ساري المفعول. كما يجب تقديم رخصة صيانة سارية. (ملاحظة: تُقدم شهادة الضمان المالي بعد ترسية العقد نهائياً).",
                "readability": "READABLE",
                "extraction_method": "NATIVE_TEXT",
                "tables": [],
                "warnings": []
            }
        ],
        "warnings": []
    }

@pytest.mark.asyncio
async def test_extract_eligibility_mock_and_rules(sample_tender):
    result = await extract_eligibility(sample_tender, client=None, mode="MOCK")

    assert "requirements" in result
    assert "provenance" in result
    assert "warnings" in result
    
    requirements = result["requirements"]
    assert len(requirements) > 0

    for req in requirements:
        assert "requirement_id" in req
        assert "text" in req
        assert "category" in req
        assert "sources" in req
        
        sources = req["sources"]
        assert len(sources) > 0
        for citation in sources:
            assert citation["document_id"] == sample_tender["document_id"]
            assert citation["pdf_page"] == 1
            assert len(citation["quote"]) > 0

@pytest.mark.asyncio
async def test_provenance_and_mode(sample_tender):
    result = await extract_eligibility(sample_tender, client=None, mode="MOCK")
    provenance = result["provenance"]
    
    assert provenance["mode"] == "MOCK"
    assert provenance["provider"] == "local"
    assert "model" in provenance
    assert "prompt_version" in provenance