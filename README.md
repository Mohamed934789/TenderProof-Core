# TenderProof-Core - هيكل 3 AI Components
العقود اتعمدت يوم 24 أكتوبر 2026. تنفيذ المنطق والـPrompts مسؤولية الفريق.
كل دوال PDF/Agents/Validation/Orchestrator ترفع NotImplementedError عمدًا.
مفيش Mock شغال أو مزوّد متصل أو UI أو Backend أو RAG. ما تقدمش الهيكل كمنتج يعمل.

## فتح المشروع
افتح TenderProof-Team.code-workspace من VS Code.
Core مستودع مستقل؛ Reference v0.6.0 للقراءة فقط كتوجيه للفريق، مش حماية كتابة تقنية.
الإخفاء يخص Explorer للـDependencies والكاش وRuntime فقط؛ المصدر والاختبارات والعقود ظاهرة.
لم تتغير إعدادات أو ملفات D:\TenderProof-AI.

## رحلة البيانات
Document Processing → Agent 1 + Agent 2 → validate_extractions → Agent 3
→ validate_verification / validate_report → Report.
A1 وA2 ممكن بالتوازي؛ A3 لازم يستنى المخرجين وفحص مصادرهما.
NOT_FOUND للـBOQ نتيجة صالحة؛ فشل API أو بنية/اقتباس غلط يمنع تقريرًا مكتملًا.
Validation برمجي مش Agent. الأسماء لا تعني Autonomous Agents.

| المكوّن | المسؤول | Input | Output |
|---|---|---|---|
| pdf_reader.read_pdf | 1 | Path + identity/role + completeness المعلن | DocumentPages |
| agent1.extract_eligibility | 2 | صفحات الكراسة + LLMClient + mode | EligibilityOutput |
| agent2.extract_technical | 3 | صفحات الكراسة + LLMClient + mode | TechnicalOutput |
| agent3.verify_company | 4 | مخرجا A1/A2 + مستندات الشركة + تاريخ + client | VerificationOutput |
| validation | 5 بالتعاون مع الجميع | مستندات/مصادر/مخرجات | None أو ValueError بعد التنفيذ |
| orchestrator.analyze | 5 | مسارات + تاريخ + client مستقل لكل Agent + mode | Report |
| llm_client.LLMClient | Interface مشترك | instructions + input_data + output_schema | LLMResponse |

الـAgents async لأن واجهة الاتصال async؛ ده مجرد signature وليس تشغيلًا متوازيًا منفذًا.
كل عضو يكتب Prompt وschema الخاص بمكوّنه. Protocol لا يفرض OpenAI أو Gemini،
ولا يقرأ مفتاحًا أو يتصل بمزوّد. FakeClient للاختبارات لاحقًا، لا يسمى AI حقيقيًا.

## models.py: عقود واضحة وليست Runtime Validation
TypedDict من مكتبة Python القياسية؛ كل الحقول مطلوبة، والمجهول nullable حيث مذكور.
schema_version يظل core-draft-0.2 كاسم عقد Core الموافق عليه، وليس API v1 للمرجع.
- الصفحات والأعمدة/الصفوف تبدأ من 1؛ العربية والاقتباسات تبقى كما في المصدر.
- Page.tables=[] معناها لا جدول استُعيد، لا دليل على عدم وجود BOQ.
- TableRegion يسجل structure_quality؛ الخلية تحمل مصادرها.
- ExtractionMethod يصف مصدر النص الفعلي؛ ذكر OCR/MIXED في النوع لا يعني تنفيذ OCR.
- completeness وcompleteness_basis يصفان اكتمال المواد المرفوعة وفق تصريح معروف،
  لا أصالة الأوراق أو اكتمال ملف التقديم كله. الافتراضي UNKNOWN.
- EL-* للأهلية، TECH-* للفني، BOQ-* للبنود؛ Finding يستخدم target_type وtarget_id.
- Quantity يحفظ raw_text وdecimal_value كنص عشري أو null، مع مصادر القيمة.
  لا تخمين تحويل وحدة أو مساواة كمية بلا شرط مقارنة مسند.
- Report.documents manifest بدون تكرار نص الصفحات، ويحفظ completeness_basis.
- Report.verification_provenance يحفظ هوية تشغيل Agent 3؛ A1 وA2 يحفظان provenance داخلهما.
  لا تفقد نوع التشغيل عند تسطيح findings داخل التقرير.

## مثال JSON صغير - نتيجة توضيحية وليست استدعاء منفذًا
هذا TechnicalOutput كامل: يمكن تسليمه لـA3 مع مخرج A1 بعد اجتياز validation.
```json
{
  "boq_status": "NOT_FOUND",
  "boq_review_reasons": [],
  "boq_items": [],
  "technical_requirements": [],
  "provenance": {
    "mode": "MOCK",
    "provider": "mock",
    "model": "student-mock",
    "prompt_version": "example-only"
  },
  "warnings": ["No BOQ identified in supplied scope; coverage remains unconfirmed."]
}
```
لو القراءة/النطاق يمنع البحث الموثوق، استخدم NEEDS_REVIEW وأسبابًا صريحة.
وجود مواصفات فنية لا يعتمد على وجود BOQ. لا نخترع Finding لبند وهمي اسمه «لا BOQ».

## قواعد القبول التي سيكتبها الفريق
مصادر A1/A2 من TENDER، وأدلة A3 من COMPANY. كل اقتباس من صفحة فعلية.
فحص المرجع لا يثبت كفاية المعنى. كل target له Finding واحدة.
SATISFIED/CONTRADICTED تحتاج دليلًا كافيًا وواضحًا، وreview_required=true في البداية.
MISSING_EVIDENCE لا يخرج من مواد غير مكتملة أو غير مقروءة أو شرط غير واضح.
الغموض NEEDS_REVIEW مع uncertainty_reasons. غياب الدليل مش عدم أهلية.
مقارنات التواريخ وDecimal والتحويلات المدعومة في Python، لا حساب LLM حر.
coverage_confirmed تبقى false أول نسخة؛ اكتمال التنفيذ ليس recall.
mode وprovenance لكل مكوّن متسقان؛ لا نخلط Fake أو Mock بنتائج Real AI.

## نبدأ إزاي؟
راجع TEAM_TASKS.md وtests/README.md، واختار Python فعليًا، يفضل 3.12.
لم تنشأ .venv ولم تُثبت مكتبات جديدة. استخدم unittest القياسي أولًا.
الخطة: عقود/مدخلات صغيرة → PDF → اختبارات A1/A2/A3 محلية → Validation/ربط.
التجارب الحقيقية مع LLM لاحقًا شرط اكتمال الـAgents، بعد عدد طلبات وتكلفة وموافقة جديدة.
Dataset: كراسة الهيئة + مستندات نايل لخدمات تكنولوجيا المكاتب / Nile Office Technology
Services صناعية ومتسقة وبعلامة Synthetic؛ لم تُنشأ dataset كاملة هنا.
Dataset ثانية بجدول واضح عند الحاجة؛ لا نضيف بنودًا للكراسة الأولى من عندنا.
راجع ARCHITECTURE_PROPOSAL.md لقرارات التصميم، وREFERENCE.md للرجوع للأصل.

## فحوص التجهيز الفعلية - 24 أكتوبر 2026
- 8 ملفات Python اتفحص syntax/imports بتاعتها.
- 16 TypedDict في models.py اتحلت type hints بتاعتها.
- 10 دوال تنفيذية تأكدنا إنها ترفع NotImplementedError، و4 مداخل async توقفت قبل أي شغل.
- 4 أمثلة JSON في README وسجل Architecture اتفحص شكلها ومفاتيح العقود المستخدمة.
- صفر اختبارات سلوك للمشروع وصفر استدعاءات مدفوعة؛ ده قبول للهيكل فقط، لا تشغيل AI أو Validation.
