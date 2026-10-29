# TenderProof AI — نسخة التسليم والعرض

## افتح التطبيق بدبل كليك

1. فك ضغط `TenderProof-Final.zip` بالكامل في مجلد قابل للكتابة، مثل `D:\TenderProof-Final`. لا تشغّل الملفات من داخل نافذة ZIP.
2. ثبّت Docker Desktop على Windows مع WSL2 وLinux containers. لا تحتاج Python أو المجلدات القديمة لتشغيل التطبيق. أول build يحتاج إنترنت لتنزيل Python والمكتبات؛ Image غير مرفقة في ZIP.
3. افتح `START_TENDERPROOF.bat` بدبل كليك. يشغّل Docker Desktop إذا لزم، ويبني التطبيق، ويفتح http://127.0.0.1:8503 تلقائيًا.
4. لإيقافه افتح `STOP_TENDERPROOF.bat`. يوقف مشروع Final فقط، ولا يحذف الملفات أو القفل ولا يغلق Docker Desktop.

نسخة Final مستقلة: Compose project باسم `tenderproof-final` وImage باسم `tenderproof-final:local`. UI على **8503** وAPI على **8002**؛ الأرقام مختلفة عن نسخة Web القديمة كي يشتغلا جنب بعض. كل البيانات mounted من مجلد Final نفسه. يمكن نقل المجلد لجهاز آخر؛ المسارات داخل ملفات BAT تعتمد على مكانها.

## عرض السيناريوهات بدون تكلفة

من **مصدر المستندات** اختار **Demo Mode — مستندات افتراضية**، ثم case_101 أو case_202 أو case_303، ثم **عرض التقرير المحفوظ**. لا يلزم رفع ملفات أو إدخال مفتاح. انتظر تحميل التقرير والتحقق من مراجعه. الشارة تقول **تقرير محفوظ — ليس تحليلًا جديدًا**.

| السيناريو | مستوفى | مخالف | دليل ناقص | يحتاج مراجعة |
|---|---:|---:|---:|---:|
| case_101 | 11 | 0 | 0 | 3 |
| case_202 | 2 | 8 | 0 | 3 |
| case_303 | 3 | 0 | 0 | 10 |

case_101 تقرير قبول OpenAI سابق. case_202 وcase_303 تقارير Replay محفوظة وفق وصفها في القائمة. الثلاثة ليسوا نتائج AI تتولد وقت العرض. اكتمال مجموعات المستندات غير مؤكد في التقارير، لذلك MISSING_EVIDENCE صفر؛ لا نحول نقص الدليل إلى مخالفة أو نختلق تنوعًا في الحالات.

لشرح اختلاف الحالات ابحث عن **R02** واضغط Enter في كل سيناريو: ترخيص سارٍ في case_101، منتهٍ في case_202، وتاريخ انتهائه غير محدد في case_303. عارض الأدلة يعرض الشرط والتفسير واقتباسات المصدر واسم PDF ورقم الصفحة. لو اللوحة طويلة مرّر داخلها لرؤية كل الاقتباسات. يمكن فلترة الحالة ونوع الشرط والبحث، ثم تنزيل التقرير الأصلي عبر **تنزيل التقرير الأصلي · JSON**. احفظه باسم السيناريو أو في مجلد مستقل لأن اسم التنزيل الافتراضي قد يتكرر.

Evidence Verification يطابق النص المستشهد به بصفحته الأصلية، لكنه وحده لا يثبت أصالة المستند أو صحة كل تفسير. تحذيرات BOQ ظاهرة؛ أصناف الجدول الثلاثة هنا NEEDS_REVIEW بسبب غموض الاستخراج. لا تقدم التقرير كقرار قانوني نهائي أو ضمان أهلية كامل.

## ملفات PDF التي ترفعها لكل سيناريو

المستندات كلها افتراضية، ومكانها **demo** بجوار START. استخدم ملفات سيناريو واحد معًا، وتاريخ تقييم **2026-10-31**. كراسة كل سيناريو هي `requirements_ar.pdf`؛ لا تحتاج `ida-335.pdf` في هذا الديمو.

**case_101 — demo/case_101/**

- خانة كراسة الشروط: `requirements_ar.pdf`.
- خانة مستندات الشركة: `01_company_profile.pdf`، `02_activity_license.pdf`، `03_tax_statement.pdf`، `04_previous_work.pdf`، `05_maintenance_authorization.pdf`، `06_service_commitment.pdf`، `07_technical_team.pdf`، `08_financial_offer.pdf`.

**case_202 — demo/case_202/**

- خانة كراسة الشروط: `requirements_ar.pdf`.
- خانة مستندات الشركة: `01_company_profile.pdf`، `02_activity_license.pdf`، `03_tax_statement.pdf`، `04_previous_work.pdf`، `05_maintenance_authorization.pdf`، `06_service_commitment.pdf`، `07_technical_team.pdf`، `08_financial_offer.pdf`.

**case_303 — demo/case_303/**

- خانة كراسة الشروط: `requirements_ar.pdf`.
- خانة مستندات الشركة الستة فقط: `01_company_profile.pdf`، `02_activity_license.pdf`، `04_previous_work.pdf`، `06_service_commitment.pdf`، `07_technical_team.pdf`، `08_financial_offer.pdf`.
- غياب 03 و05 مقصود في الملفات الحالية؛ لا تنشئهما أو تضف ملفات من سيناريو آخر.

`report.json` في كل مجلد تقرير محفوظ للعرض، وليس ملفًا ترفعه في خانة PDF. ملف `demo/manifest.json` يربط هذه الملفات بالديمو؛ احتفظ بأسماء الملفات كما هي. في Saved Demo لا تحتاج رفع أي ملفات أصلًا. رفع الملفات بوضع MOCK يفحص المسار دون LLM، ولا يولد أحكامًا؛ صفر نتائج في MOCK متوقع.

## Real AI — اختياري ومقفول افتراضيًا

لا تحتوي نسخة التسليم على `.env` أو API Keys أو ملفات secret. `START_TENDERPROOF.bat` يشغّل Saved Demo وMOCK فقط، ويغلق بوابة المدفوع حتى لو سبق تشغيل Real AI. اختيار AI وحده لا يبدأ تحليلًا.

لتفعيل Real AI بعد موافقة المسؤول على التكلفة:

1. أنشئ مجلد `.secrets` داخل Final، وفيه ملف نصي بلا امتداد اسمه `openai_api_key`، وضع فيه المفتاح فقط عبر محرر محلي. لا تضعه في BAT أو Dockerfile، ولا ترسله في ZIP أو الرسائل، ولا تنسخه من مجلد قديم تلقائيًا. راجع أن اسم الملف ليس `openai_api_key.txt` عند إخفاء الامتدادات في Windows.
2. افتح **START_REAL_AI.bat** بدبل كليك. يمرر secret للـAPI فقط وقت التشغيل، read-only، ولا ينسخه إلى Image أو UI. لو المفتاح ناقص/فارغ أو غير مقروء تظهر رسالة واضحة. صلاحية المفتاح والرصيد لا يمكن إثباتهما من فحص الجاهزية فقط.
3. في الواجهة اختار **رفع ملفات**، ثم **إعدادات متقدمة → AI — OpenAI حقيقي**. ارفع PDFs المذكورة للسيناريو، واضبط تاريخ التقييم `2026-10-31`. فعّل **مستندات افتراضية فقط — synthetic-test** لهذه المجموعة. لا تؤكد اكتمال المستندات إلا لو تعريف الاختبار يثبته؛ التقارير المرفقة لا تفترضه.
4. وافق على إرسال المستندات والتكلفة، ثم اضغط **بدء المراجعة** فقط عندما تريد تحليلًا مدفوعًا بالفعل. الموديل الحالي `gpt-6-luna`.
5. الحماية الحالية: محاولة AI واحدة لكل runtime، 3 generation calls كحد أقصى وبدون retries، مع token counting وحجز تكلفة تقديري أقصاه $0.50. القفل `runtime/docker/api/real-ai-e2e/single-attempt.lock` محفوظ بعد المحاولة، حتى لو فشلت. إعادة START/STOP لا تحذفه ولا تفتح محاولة جديدة. لا تغيّر runtime أو تحذف القفل لتكرار تجربة دون تصريح جديد.
6. لتعطيل المدفوع، افتح **START_TENDERPROOF.bat** العادي، ثم اعمل Refresh. API Health يجب أن يرجع `paid_ai_enabled=false`. أو أوقف التطبيق بـSTOP.

الـHealth: http://127.0.0.1:8002/health، والـAPI docs: http://127.0.0.1:8002/docs. `READY` تعني جاهزية إعدادات وليست اختبار API ناجحًا. لم يتم تشغيل أي تحليل OpenAI أثناء تجهيز Final أو اختبارها.

## المستندات والأدلة المرفقة

- `docs/DEMO_REHEARSAL.md`: كلام العرض وخطواته في 4–5 دقائق.
- `docs/TENDERPROOF_BENCHMARK_FINAL_REPORT.md`: تقرير المقارنة المختصر.
- `docs/benchmark/`: المقارنة CSV/JSON، وتشخيص فشل المزود، ومثال اختلاف case_101:R02. الملفات مصدرها سجلات محفوظة، وليست تجارب جديدة.
- `docs/evidence/previous-real-ai-acceptance.json` و`previous-real-ai-case_101.json`: دليل تشغيل Web حقيقي سابق منفصل، أنتج 12 SATISFIED و3 NEEDS_REVIEW. مختلف عن Saved Demo case_101 ذي 11 SATISFIED؛ لم نعدّل أيًا منهما أو نستبدل أحدهما بالآخر.
- `docs/evidence/`: صور الأدلة ونتيجة فحص Final المستقل. كلمة previous تميز صور ونتائج البروفة السابقة عن فحص Final.
- `docs/source-file-hashes.json`: بصمات ملفات المصادر وقت النسخ لإثبات عدم تعديل المجلدات الأصلية. المسارات فيه سجل مصدر فقط، وليست اعتمادًا لتشغيل Final.
- `DELIVERY_MANIFEST.json`: قائمة ملفات التسليم وبصماتها للتحقق من سلامة النقل.

الـBenchmark **LLM-Judged Development** بمراجع Claude مؤقتة، وليس Human Gold أو Holdout مستقلًا. GPT أكمل 18، Gemini أكمل 2، Nemotron أكمل 16. المقارنة الصالحة المشتركة على 16 حالة: اتفاق GPT مع Claude 16/16 وNemotron 15/16، وF1 للفئتين المدعومتين 100% و97.37% على الترتيب. لا تعرض Gemini كترتيب نهائي أو الأرقام كدقة عامة على مستندات جديدة. التقرير يشرح أسباب عدم اكتمال المقارنة.

## ماذا ترسل؟

**للفريق:** أرسل `TenderProof-Final.zip` كاملة. تحتوي كود التشغيل وDocker والمستندات الافتراضية والتقارير والأدلة والتوثيق، دون Git أو venv أو كاش أو أسرار أو MLflow database. يفكونها ويشغلون START؛ لا يحتاجون TenderProof-Core أو TenderProof-Web أو TenderProof-Experiments.

**للجنة:** أرسل نفس ZIP لو مطلوب تطبيق قابل للتجربة. وللمراجعة المختصرة أرسل README وتقرير Benchmark ونتيجة فحص Final وصور الأدلة، مع الإيضاح أن Saved Demo محفوظ وأن المرجع البحثي مؤقت. لا ترسل key أو `.env` أو runtime الذي سينشأ على جهازك بعد الاستخدام. النسخة الحالية محلية وليست خدمة منشورة للإنترنت، ولا تضم Authentication أو Image جاهزة للعمل دون إنترنت أول مرة.

لو Docker غير موجود أو المحرك لا يبدأ، افتح Docker Desktop وراجع WSL2 وLinux containers. ملفات BAT تستخدم docker.exe بالمسار الكامل لتجنب ملف Windows المسمى docker بلا امتداد. لا تحتاج اختيار برنامج لفتح docker يدويًا. شغّل START من المجلد المفكوك، وليس من ZIP، ولا تشغّل START أثناء تحليل جارٍ لأنه قد يعيد إنشاء الحاويات. في العرض استخدم Saved Demo لتجنب انتظار LLM والتكلفة.


## مراجعة UX النهائية

قسم النتائج العلوي «تغيير الملفات أو اختيار سيناريو آخر» يفتح إعدادات المدخلات؛ ليس حقل بيانات إضافيًا. تنبيه Saved Demo معلومة زرقاء توضح أن المعروض تقرير سابق، مع استمرار الشارة الثابتة. تحذير عدم تأكيد اكتمال المستندات منفصل وواضح؛ ملاحظات القراءة الأصلية وتحذيرات BOQ وأسباب NEEDS_REVIEW محفوظة. تفاصيل جاهزية السيرفر التقنية موجودة في Advanced Settings، بينما رسالة الصفحة تشرح للمستخدم ما الذي يمكنه عمله.

نجح فحص Chromium Headless على Desktop وMobile، مع رفع 9 PDFs بوضع MOCK على الحجمين، وعرض Saved Demo للسيناريوهات الثلاثة والفلاتر والأدلة والصفحات وتنزيل JSON مطابق للأصل. الصور قبل وبعد ونتيجة الفحص داخل `runtime/ux-review/`. لم يتغير Core أو API أو CSS أو التقارير، ولم تُجرَ استدعاءات مدفوعة أو اختبارات شاملة أو Commit/Push/Merge.

تعديلات UX الحالية داخل هذا المجلد. أرشيف ZIP السابق خارج المجلد لم يُحدَّث في مراجعة UX؛ يلزم إعادة إنشائه عند تجهيز التسليم التالي.


## النسخة الموحدة للتسليم — integration/samsung-final

النسخة دي تحتفظ بـAI Core والـPrompts المعتمدة، FastAPI وStreamlit وDocker وSaved Demo، وتضيف MLflow اختياري لتسجيل مؤشرات التشغيل فقط. التسجيل لا يغيّر التقرير ولا يصنع Ground Truth. تقرير الـBenchmark السابق في `docs/benchmark/` مستقل عن مؤشرات التشغيل الجديدة.

### التشغيل على Windows بدبل كليك

1. ثبّت Git وDocker Desktop، وشغّل Linux Containers.
2. نزّل أو اعمل Clone للنسخة الحالية من GitHub.
3. افتح `START_TENDERPROOF.bat`؛ الواجهة على http://127.0.0.1:8503 وFastAPI على http://127.0.0.1:8002/docs.
4. اختَر Demo Mode ثم case_101 أو case_202 أو case_303 واضغط عرض التقرير المحفوظ. دي نتائج محفوظة بعلامة واضحة، وليست تحليل AI جديدًا.
5. ملفات الرفع لكل سيناريو داخل `demo/case_XXX`: `requirements_ar.pdf` للكراسة، وكل ملفات `0*.pdf` للشركة في نفس المجلد. استخدم تاريخ 2026-10-31. لا تخلط السيناريوهات.
6. `STOP_TENDERPROOF.bat` يوقف التطبيق دون حذف ملفات أو أقفال.

### Docker من الطرفية

```powershell
& "C:\Program Files\Docker\Docker\resources\bin\docker.exe" compose up --build -d --wait
```

### تشغيل محلي بدون Docker

Python 3.12 أو أحدث؛ من داخل مجلد المشروع في PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r web/requirements.txt
$env:TENDERPROOF_RUNTIME_DIR="$PWD/runtime"
$env:TENDERPROOF_DEMO_DIR="$PWD/demo"
$env:TENDERPROOF_ALLOW_PAID_API="0"
$env:TENDERPROOF_SINGLE_AI_RUN="1"
.\.venv\Scripts\python.exe -m uvicorn web.api:app --host 127.0.0.1 --port 8000 --no-access-log
```

في نافذة تانية من نفس المجلد:

```powershell
$env:TENDERPROOF_API_URL="http://127.0.0.1:8000"
.\.venv\Scripts\python.exe -m streamlit run web/app.py --server.address 127.0.0.1 --server.port 8501
```

### Real AI — تفعيل صريح فقط

التشغيل العادي لا يرسل طلبات مدفوعة. Docker: أنشئ محليًا `.secrets/openai_api_key` واكتب المفتاح في محرر محلي؛ الملف مستبعد من Git وDocker build. افتح `START_REAL_AI.bat` أو:

```powershell
& "C:\Program Files\Docker\Docker\resources\bin\docker.exe" compose -f docker-compose.yml -f docker-compose.ai.yml up --build -d --wait
```

محليًا بدون Docker: ضع المفتاح في `.env` محلي غير متتبع، أو استخدم `OPENAI_API_KEY_FILE` لمسار ملف سري. اضبط في نافذة API قبل تشغيله:

```powershell
$env:TENDERPROOF_ALLOW_PAID_API="1"
$env:OPENAI_MODEL="gpt-6-luna"
$env:TENDERPROOF_SINGLE_AI_RUN="1"
```

اختَر AI في Advanced Settings، وارفع الملفات ووافق على تكلفة التشغيل، ثم اضغط بدء المراجعة مرة واحدة. الحد التقديري المحجوز $0.50، بحد أقصى 3 طلبات توليد، ولا توجد إعادة تلقائية. `synthetic-test` للمستندات الافتراضية فقط وليس افتراضيًا. `/health` يعرض READY أو سبب عدم الجاهزية؛ READY لا يؤكد صلاحية المفتاح أو الرصيد، ولم يتم اختبارهما بطلب مدفوع أثناء التكامل.

قفل المحاولة محفوظ في `runtime/docker/api/real-ai-e2e/single-attempt.lock` في Docker، و`runtime/real-ai-e2e/` محليًا. لا تحذفه ولا تغيّر runtime لإعادة تسليح محاولة مستهلكة. لو ATTEMPT_USED ظاهر، استخدم Saved Demo؛ أي تشغيل إضافي يتطلب موافقة جديدة ومراجعة مسؤول التشغيل. الإيقاف وإعادة التشغيل يحافظان على القفل.

لإغلاق Real AI: افتح START_TENDERPROOF بدون `--real-ai`؛ أو شغّل Compose الأساسي فقط؛ محليًا اضبط `TENDERPROOF_ALLOW_PAID_API=0` وأعد تشغيل API.

### MLflow اختياري ومتكامل

افتراضيًا التسجيل مقفول. لتفعيله مع Docker وفتح صفحة MLflow:

```powershell
$env:TENDERPROOF_MLFLOW_ENABLED="1"
& "C:\Program Files\Docker\Docker\resources\bin\docker.exe" compose --profile tracking up --build -d --wait
```

الواجهة http://127.0.0.1:5001، experiment اسمه `TenderProof_Evaluation`. اختَر **Model training → Runs** لعرض السجلات التشغيلية؛ صفحة GenAI Overview تعرض Traces غير مستخدمة هنا وقد تظهر فارغة. رابط مباشر للتجربة الأولى: http://127.0.0.1:5001/#/experiments/1/runs?workflowType=machine_learning . نفّذ فحص MOCK أو افتح Saved Demo لتظهر Runs؛ لا تحتاج API مدفوعة. الـAgents تسجل أعداد الشروط والـBOQ ومدة التشغيل، ثم نتائج التحقق. Saved Demo يسجل التحقق من تقرير محفوظ بعلامة SAVED_DEMO. لا تُعرض Precision/Recall/F1 بدون مرجع مستقل؛ المؤشرات هنا تشغيلية فقط. لا تُسجَّل مستندات أو اقتباسات أو أسماء ملفات أو مفاتيح أو مخرجات LLM. SQLite محفوظ تحت `runtime/docker/api/mlflow/mlflow.db`؛ فشل MLflow لا يوقف التحليل.

محليًا اضبط `TENDERPROOF_MLFLOW_ENABLED=1` قبل API، ثم:

```powershell
.\.venv\Scripts\python.exe -m mlflow ui --backend-store-uri "sqlite:///$($PWD.Path.Replace('\','/'))/runtime/mlflow/mlflow.db" --host 127.0.0.1 --port 5001
```

أوقف التسجيل بـ`TENDERPROOF_MLFLOW_ENABLED=0` وأعد تشغيل API. لا تعرّض MLflow على الإنترنت. عند تفعيل Docker Real AI وMLflow معًا أضف `-f docker-compose.yml -f docker-compose.ai.yml` قبل `--profile tracking`.

### تحقق مجاني

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

الاختبارات تستخدم Fake LLM أو MOCK؛ بعض اختبارات Replay الخاصة اختيارية وتتخطى نفسها لو سجلات API المحلية غير موجودة. لا تشغّل سكربت Agent 2 اليدوي الحقيقي أو وضع AI أثناء الفحص المجاني.
