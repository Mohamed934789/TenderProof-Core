
"""Agent 2: technical and BOQ extraction with exact line citations."""

from decimal import Decimal, InvalidOperation

from agent2_schema import agent2_output_schema
from llm_client import LLMClient
from models import DocumentPages, Mode, TechnicalOutput
from validation import (
    build_line_index, resolve_sources, documents_complete, validate_shape, validate_technical,
)


PROMPT_VERSION = "agent2-line-references-v2"

AGENT2_PROMPT = """
أنت Agent 2 في مشروع TenderProof AI.

مهمتك استخراج المتطلبات الفنية وجداول الكميات
من كراسات المناقصات المصرية.

ستستقبل سطورًا مستخرجة من PDF.
كل سطر له line_id ثابت مثل P006-L0034.

استخرج:
1. BOQ Items: الأصناف والكميات ووحدات القياس.
2. Technical Requirements: المواصفات والموديلات
   والالتزامات الفنية ومواعيد التنفيذ.

قواعد أساسية:
- لا تخترع كميات أو مواصفات أو مراجع.
- استخدم line_id الموجود في الإدخال فقط.
- sources تحتوي على كائنات بالشكل:
  {"line_id": "P006-L0034"}
- لا تكتب اقتباسات quote بنفسك.
- استشهد بالسطر الذي يدعم كل معلومة فعلًا.
- استشهد بمصدر مستقل للكمية داخل quantity.sources.
- يمكن استخدام أكثر من سطر لدعم متطلب واحد.
- لا تكرر بند توريد عادي كمتطلب فني مستقل.
- لا تعتبر اسم العلامة التجارية وحده شرطًا فنيًا.
- إذا لم تجد شرطًا فنيًا مستقلًا أرجع قائمة فارغة.

قواعد الجداول:
- ميّز بين جدول التأمين المؤقت وجدول الأصناف والكميات.
- مبالغ التأمين والضرائب والأسعار ليست كميات أجهزة.
- لا تخلط أرقام البنود بالكميات.
- لا تخلط بيانات جدول في صفحة بجدول في صفحة أخرى.
- استخرج الكمية فقط إذا كانت علاقتها بالصنف واضحة.
- إذا كانت الكمية غير مؤكدة استخدم decimal_value=null.
- إذا كان ترتيب الجدول غير واضح استخدم NEEDS_REVIEW.
- لا تخترع table_id: استخدم null لو لم يتم
  استخراج جدول منظم ومعرّف من المصدر.

قواعد المراجعة:
- needs_review=true عند غياب كمية أو عدم اليقين.
- اذكر أسباب المراجعة بصورة واضحة.
- لا تستخدم NOT_FOUND إلا عند وجود تغطية كافية
  لمستند كامل ومقروء.
- المستند الجزئي أو الصفحات غير المؤكدة تستلزم مراجعة.
- لا تخترع دليلًا لتجاوز المراجعة.

أرجع JSON مطابقًا للـSchema المطلوب.
قواعد تفسير كميات الجداول:

- ميّز بين استخراج قيمة ظاهرة وبين تأكيد صحة بنية الجدول.
- عندما يكون عنوان الجدول "الكمية البيان البند"،
  وتظهر الصفوف بنفس ترتيب الأعمدة،
  يمكن استخراج قيمة الكمية الظاهرة مع وضع
  needs_review=true إذا كانت البنية غير مؤكدة.
- لا تجعل decimal_value=null لمجرد أن الصفحة
  مصنفة PARTIAL؛ استخدم null عندما لا يمكن
  تحديد الكمية وعلاقتها بالصنف بدليل كافٍ.
- لا تعتمد على وجود رقم بجوار اسم جهاز وحده.
- لا تستخرج مبالغ التأمين أو الأسعار ككميات.
- احتفظ بمراجع السطور الأصلية، ولا تُنشئ اقتباسات.
"""


def _mock_output() -> TechnicalOutput:
    return {
        "boq_status": "NEEDS_REVIEW",
        "boq_review_reasons": [
            "MOCK mode does not perform extraction."
        ],
        "boq_items": [],
        "technical_requirements": [],
        "provenance": {
            "mode": "MOCK",
            "provider": "mock",
            "model": "none",
            "prompt_version": PROMPT_VERSION,
        },
        "warnings": [
            "MOCK results are not evidence of tender eligibility."
        ],
    }


def _validate_quantity(item):
    quantity = item["quantity"]
    value = quantity["decimal_value"]

    if value is None:
        if not item["needs_review"]:
            raise ValueError(
                "Unknown quantity must require review."
            )
        if not item["review_reasons"]:
            raise ValueError(
                "Unknown quantity needs a review reason."
            )
        return

    if not isinstance(value, str):
        raise ValueError(
            "Quantity decimal_value must be a string or null."
        )

    try:
        parsed = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"Invalid quantity: {value}")

    if not parsed.is_finite() or parsed < 0:
        raise ValueError(f"Invalid quantity: {value}")


def _resolve_extraction(payload, line_lookup):
    """Validate essential structure and resolve every citation."""

    if not isinstance(payload, dict):
        raise ValueError("LLM payload must be an object.")

    required = {
        "boq_status",
        "boq_review_reasons",
        "boq_items",
        "technical_requirements",
    }

    if set(payload) != required:
        raise ValueError("Unexpected Agent 2 payload fields.")

    if payload["boq_status"] not in {
        "FOUND", "NOT_FOUND", "NEEDS_REVIEW"
    }:
        raise ValueError("Invalid BOQ status.")

    if not isinstance(payload["boq_review_reasons"], list):
        raise ValueError("Invalid BOQ review reasons.")

    if not isinstance(payload["boq_items"], list):
        raise ValueError("Invalid BOQ items.")

    if not isinstance(payload["technical_requirements"], list):
        raise ValueError("Invalid technical requirements.")

    item_ids = set()
    technical_ids = set()

    for item in payload["boq_items"]:
        item_id = item["boq_item_id"]

        if not isinstance(item_id, str) or not item_id.strip():
            raise ValueError("Invalid BOQ item ID.")

        if item_id in item_ids:
            raise ValueError(f"Duplicate BOQ item ID: {item_id}")

        item_ids.add(item_id)

        item["sources"] = resolve_sources(
            item["sources"],
            line_lookup,
        )

        item["quantity"]["sources"] = resolve_sources(
            item["quantity"]["sources"],
            line_lookup,
        )

        _validate_quantity(item)

        if item["table_id"] is not None:
            raise ValueError(
                "No verified table IDs are available from this reader."
            )

    for requirement in payload["technical_requirements"]:
        requirement_id = requirement["technical_id"]

        if (
            not isinstance(requirement_id, str)
            or not requirement_id.strip()
        ):
            raise ValueError("Invalid technical requirement ID.")

        if requirement_id in technical_ids:
            raise ValueError(
                f"Duplicate technical ID: {requirement_id}"
            )

        technical_ids.add(requirement_id)

        requirement["sources"] = resolve_sources(
            requirement["sources"],
            line_lookup,
        )

    if payload["boq_status"] == "FOUND" and not item_ids:
        raise ValueError(
            "FOUND status requires at least one BOQ item."
        )

    if payload["boq_status"] == "NOT_FOUND" and item_ids:
        raise ValueError(
            "NOT_FOUND is inconsistent with extracted BOQ items."
        )

    return payload


def _mark_review(item, reason):
    item["needs_review"] = True

    if reason not in item["review_reasons"]:
        item["review_reasons"].append(reason)


async def extract_technical(
    tender: DocumentPages,
    *,
    client: LLMClient,
    mode: Mode = "MOCK",
) -> TechnicalOutput:
    """Extract technical requirements and BOQ from tender pages."""

    if mode == "MOCK":
        return _mock_output()

    if mode != "AI":
        raise ValueError(f"Unsupported mode: {mode}")

    if tender["role"] != "TENDER":
        raise ValueError("Agent 2 expects a TENDER document.")

    if not tender["pages"]:
        raise ValueError("Tender contains no pages.")

    if client is None:
        raise ValueError("AI mode requires an LLMClient.")

    page_numbers = [p["pdf_page"] for p in tender["pages"]]

    if len(page_numbers) != len(set(page_numbers)):
        raise ValueError("Duplicate PDF page numbers.")

    indexed_pages, line_lookup = build_line_index(tender)

    if not line_lookup:
        raise ValueError("No extractable text in tender.")

    warnings = list(tender["warnings"])

    uncertain_pages = {
        page["pdf_page"]
        for page in tender["pages"]
        if (
            page["readability"] != "READABLE"
            or page["warnings"]
            or any(
                table["structure_quality"] != "RECOVERED"
                for table in page["tables"]
            )
        )
    }

    if uncertain_pages:
        warnings.append(
            "PDF reading or table structure requires review "
            f"on pages: {sorted(uncertain_pages)}."
        )

    incomplete = not documents_complete([tender])

    if incomplete:
        warnings.append(
            "Tender completeness is not confirmed."
        )

    response = await client.generate(
        instructions=AGENT2_PROMPT,
        input_data={
            "document_id": tender["document_id"],
            "filename": tender["filename"],
            "completeness": tender["completeness"],
            "pages": indexed_pages,
            "warnings": warnings,
        },
        output_schema=agent2_output_schema(),
    )

    try:
        extraction = _resolve_extraction(response["payload"], line_lookup)
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError("Malformed Agent 2 payload.") from error

    extraction["provenance"] = {
        "mode": "AI", "provider": response["provider"], "model": response["model"],
        "prompt_version": PROMPT_VERSION,
    }
    extraction["warnings"] = warnings
    validate_shape(extraction, TechnicalOutput)

    for item in extraction["boq_items"]:
        source_pages = {
            citation["pdf_page"]
            for citation in (
                item["sources"]
                + item["quantity"]["sources"]
            )
        }

        if source_pages & uncertain_pages:
            _mark_review(
                item,
                "The cited PDF page has extraction uncertainty.",
            )

    for requirement in extraction["technical_requirements"]:
        source_pages = {
            citation["pdf_page"]
            for citation in requirement["sources"]
        }

        if source_pages & uncertain_pages:
            _mark_review(
                requirement,
                "The cited PDF page has extraction uncertainty.",
            )

    global_review_reasons = []

    if incomplete:
        global_review_reasons.append(
            "Full tender coverage has not been confirmed."
        )

    if uncertain_pages:
        global_review_reasons.append(
            "Some PDF pages or table structures require review."
        )

    if any(
        item["needs_review"]
        for item in extraction["boq_items"]
    ):
        global_review_reasons.append(
            "One or more BOQ items require review."
        )

    if global_review_reasons:
        extraction["boq_status"] = "NEEDS_REVIEW"

        for reason in global_review_reasons:
            if reason not in extraction["boq_review_reasons"]:
                extraction["boq_review_reasons"].append(reason)

    validate_technical(extraction, tender)
    return extraction
