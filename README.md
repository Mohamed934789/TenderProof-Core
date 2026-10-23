# TenderProof-Core - هيكل 3 AI Components
العقود اتعمدت يوم 24 أكتوبر 2026. تنفيذ المنطق والـPrompts مسؤولية الفريق.
كل دوال PDF/Agents/Validation/Orchestrator ترفع NotImplementedError عمدًا.
مفيش Mock شغال أو مزوّد متصل أو UI أو Backend أو RAG. ما تقدمش الهيكل كمنتج يعمل.

## تجهيز المشروع على Windows
الـClone مستقل؛ مفيش احتياج لـTenderProof-AI على جهاز زميلك.
المتطلبات: Git وPython 3.12 أو أحدث. الـAgents لسه غير منفذة؛ ده تجهيز بيئة تطوير.

### 1. Clone
من GitHub > Code انسخ HTTPS URL الحقيقي واستبدل REPOSITORY_URL:
```powershell
git clone REPOSITORY_URL TenderProof-Core
cd TenderProof-Core
```
مفيش Remote مضبوط في النسخة المحلية وقت التجهيز؛ لم نرفع repo أو نخترع رابطًا.
إنشاء المستودع على GitHub وصلاحيات الفريق خطوة منفصلة. لو عندك الـCore محليًا تجاوز Clone.

### 2. إنشاء وتفعيل البيئة وتثبيت المتطلبات
```powershell
py -3.12 --version
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
python -m pip install -r requirements.txt
```
لو Python أو Git غير متاح، ثبّتهما قبل البدء. لا تنسخ .venv من زميلك أو تستخدم بيئة المرجع.
لو PowerShell منع Activate.ps1، اشتغل بالمفسر مباشرة بدون تغيير ExecutionPolicy:
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\check_environment.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

### 3. إعداد .env
```powershell
if (-not (Test-Path -LiteralPath .env)) {
    Copy-Item -LiteralPath .env.example -Destination .env
}
```
القالب تعليقات فقط: مفيش أسماء متغيرات متفق عليها وبيقرأها الكود حاليًا.
لا API Key مطلوب لفحوص البيئة. نسخ الملف لا يشغّل AI؛ مفيش .env loader بعد.
صاحب أول adapter يوثّق أسماء provider/model/key variables ويتفق عليها الفريق.
لا نضيف متغيرات غير مستخدمة أو مفاتيح وهمية؛ لا تبعت مفتاحك في Chat أو commit.

### 4. VS Code والاختبارات
افتح TenderProof-Team.code-workspace من File > Open Workspace from File.
بيفتح Core فقط بمسار نسبي، ويقترح .venv\Scripts\python.exe داخل نفس الـClone.
لو اختار مفسرًا قديمًا: Python: Select Interpreter، واختر مفسر البيئة المحلية.
Python extension اختيارية للتحرير؛ الأوامر لا تعتمد عليها.
```powershell
python scripts\check_environment.py
python -m pip check
python -m unittest discover -s tests -v
```
الفاحص لا يشغّل Agents ولا يقرأ قيم .env. unittest حاليًا هيقول Ran 0 tests:
ده مش نجاح منطق التطبيق؛ اختبارات السلوك مهمة الفريق، والدوال ما زالت NotImplementedError.
في البيئة المختبرة طلع NO TESTS RAN برمز خروج 1؛ لا تعالجه باختبار وهمي ولا تعتبره فشل Imports.
استخدم deactivate للخروج من البيئة المفعّلة.

### Dependencies اللي نحتاجها فعلًا
كل الـImports الحالية stdlib أو ملفات محلية؛ requirements.txt بدون حزم خارجية.
اختيار PDF parser وOCR/table extraction وHTTP/SDK و.env loader لسه ما اتحسمش.
لم نضف pypdf أو OpenAI/Gemini SDK أو pytest أو python-dotenv لمجرد الاحتمال.
أضف dependency عند اختيارها وكتابة استخدام فعلي، ووثّق النسخة واختبرها في بيئة جديدة.

### اختيار المزوّد لكل عضو بدون تغيير العقود
LLMClient.generate في llm_client.py واجهة فقط؛ صاحب الـAgent يكتب adapter يطابقها
ويمرره في client. اختيار provider/model والمفتاح يبقى في adapter/configuration،
خارج منطق الـAgent، بدون تغيير EligibilityOutput أو TechnicalOutput أو VerificationOutput.
orchestrator.analyze يستقبل eligibility_client وtechnical_client وverification_client؛
ممكن كل عضو يستخدم مزوّدًا مختلفًا أثناء التطوير. مفيش مزوّد أو SDK مفروض.
Adapter يرجع payload/provider/model/usage؛ Validation مستقل مهما كان المزوّد.
مفيش adapter أو تحميل .env تلقائي أو retries/fallback صامتة منفّذة.
Luna هدف الدمج النهائي بعد اختبار التوافق وموافقة تكلفة جديدة.

### Git والخصوصية
.gitignore يتجاهل .env ومشتقاته، .venv، الكاش، ملفات مفاتيح شائعة، وruntime.
.env.example وحده مسموح. لكن ignore يعتمد على الاسم/المسار، مش كاشف أسرار داخل كود أو fixture.
راجع git status وgit diff --cached قبل push. ملف متتبع من قبل لا يحميه ignore بأثر رجعي.
المرجع اختياري في نافذة منفصلة لمن يملكه؛ REFERENCE.md توثيق تاريخي لمسار صاحبه،
مش اعتماد تشغيل على جهاز زميلك. المصدر والاختبارات والعقود تفضل ظاهرة في Explorer.


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
كل جهاز ينشئ .venv الخاصة به وفق الخطوات أعلاه؛ البيئة لا تُحفظ في Git. استخدم unittest القياسي أولًا.
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

## نتائج تجهيز البيئة المشتركة - 24 أكتوبر 2026
- بيئة .venv مستقلة بـPython 3.12.7، واختبار تثبيت requirements offline باستخدام --no-index نجح؛ لا حزم خارجية مطلوبة.
- scripts/check_environment.py: 14 فحصًا ناجحًا، صفر فشل، يشمل 8 imports والعقود والمسارات النسبية.
- git check-ignore: 18 فحصًا ناجحًا لأسماء أسرار/كاش ومصدر/قوالب يجب أن تظهر.
- python -m pip check: No broken requirements found.
- unittest: Ran 0 tests / NO TESTS RAN، exit 1؛ لا توجد اختبارات سلوك مكتوبة، ولا ادعاء نجاح AI.
- Activate.ps1 اختُبر بنجاح دون تغيير ExecutionPolicy العامة.
- لم يُنشأ .env حقيقي، ولم تُقرأ أسرار أو تُنفذ Agents/Prompts/API calls.
- لم تتغير models.py أو signatures الخاصة بالـAgents/Orchestrator/Validation.
