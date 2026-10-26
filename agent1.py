from llm_client import LLMClient
from models import DocumentPages, EligibilityOutput, Mode, Requirement

async def extract_eligibility(
    tender: DocumentPages, *, client: LLMClient, mode: Mode = "MOCK"
) -> EligibilityOutput:
    """Extract qualification documents/criteria with original tender citations.
    Cover eligibility-related administrative/financial requirements, not every cost.
    Client injection is not permission for paid calls. No mock implementation yet.
    """
    if mode == "MOCK":
        mock_requirements: list[Requirement] = [
            {
                "requirement_id": "req-001",
                "text": "يجب تقديم سجل تجاري ساري المفعول",
                "category": "REGISTRATION",
                "needs_review": False,
                "review_reasons": [],
                "sources": [
                    {
                        "document_id": tender.get("document_id", "tender-001"),
                        "pdf_page": 1,
                        "quote": "يجب تقديم سجل تجاري ساري المفعول"
                    }
                ]
            },
            {
                "requirement_id": "req-002",
                "text": "ترخيص صيانة يغطي النشاط المطلوب",
                "category": "LICENSE",
                "needs_review": False,
                "review_reasons": [],
                "sources": [
                    {
                        "document_id": tender.get("document_id", "tender-001"),
                        "pdf_page": 1,
                        "quote": "ترخيص صيانة يغطي النشاط المطلوب"
                    }
                ]
            }
        ]
        return {
            "requirements": mock_requirements,
            "provenance": {
                "mode": "MOCK",
                "provider": "local",
                "model": "mock-model",
                "prompt_version": "v1.0"
            },
            "warnings": []
        }

    system_prompt = (
        "أنت مساعد ذكاء اصطناعي محترف متخصص في تحليل كراسات المناقصات واستخراج شروط التأهيل.\n"
        "مهمتك هي استخراج: السجل التجاري، التراخيص، الخبرات السابقة، والمستندات الإلزامية، والمتطلبات الإدارية والمالية للتأهيل.\n"
        "الشروط الصارمة:\n"
        "1. لا تختلق أي شروط غير موجودة في النص الأصلي نهائياً.\n"
        "2. يجب إرفاق اقتباس حرفي دقيق (quote) ورقم الصفحة (pdf_page) لكل شرط مستخرج.\n"
        "3. تصنيف الفئة (category) يجب أن يكون واحداً من: REGISTRATION, LICENSE, EXPERIENCE, ADMINISTRATIVE, FINANCIAL, OTHER."
    )

    input_content = {
        "document_id": tender["document_id"],
        "pages": [{"pdf_page": p["pdf_page"], "text": p["text"]} for p in tender["pages"]]
    }

    response = await client.generate(
        instructions=system_prompt,
        input_data=input_content,
        output_schema={"type": "object"}
    )
    payload = response["payload"]

    return {
        "requirements": payload.get("requirements", []),
        "provenance": {
            "mode": "AI",
            "provider": response["provider"],
            "model": response["model"],
            "prompt_version": "v1.0"
        },
        "warnings": payload.get("warnings", [])
    }
