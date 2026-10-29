# مراجعة النسخة الموحدة — 2026-10-29

- Branch الشغل: `integration/samsung-final`، في Worktree منفصل `D:/TenderProof-Integration`.
- الأساس: `main` عند `311b19e`، مع تاريخ `mlflow-api-tracker` عند `5609b42`.
- `mlflow` مطابق لـmain. احتفظنا بفصل schemas وArabic helpers، وأصلحنا ربط tracker غير المتوافق بدل تمرير وسيط غير مدعوم أو استيراد MLflow الإجباري عند بدء API.
- `release/tenderproof-final` عند `194c472`: رجعنا الاختبارات والـFixtures والوثائق المحذوفة، واستعدنا نصوص Prompts الثلاثة المعتمدة حرفيًا. منطق الحالات والتحقق والاقتباسات لم يُستبدل. أضفنا aliases للحفاظ على imports السابقة بعد نقل الدوال.
- فروع eligibility/pdf-reader/orchestrator-validation القديمة موجودة في التاريخ أو ممثلة بالنسخة المستقرة الأحدث. فرع evidence القديم يحتوي قواعد BOQ أقدم؛ التغطية وقواعد الكميات المصححة موجودة بالفعل في المستقر، ولم نستبدلها بالإصدار الأقدم. لم يُحذف أي Branch.

## النتائج المثبتة في التكامل الحالي

- داخل صورة Docker Linux: **193 passed، 6 skipped، 16 subtests passed**. الاختبارات الستة اختيارية تحتاج الكراسة أو سجلات API الخاصة غير الموجودة في حزمة التسليم. يوجد SQLAlchemy deprecation warning داخل MLflow؛ لا يمنع التشغيل.
- اختبارات Core تشمل Agents الثلاثة وValidation والكميات العربية والسريان والمراجع الأصلية وتصنيف الأدلة عبر Fake LLM، دون API مدفوعة.
- Chromium Desktop وMobile: رفع 9 PDFs وفحص MOCK، الفلاتر، تفاصيل الأدلة والصفحات والنصوص، وتنزيل JSON مطابق للأصل. التصميم لم يتغير.
- Docker: Build نجح بالأمر المعتاد، FastAPI وStreamlit وMLflow اشتغلوا. رفع HTTP فعلي لـ9 PDFs اكتمل بوضع MOCK. `pip check` ناجح.
- التقارير الثلاثة داخل Docker خضعت لـvalidate_report مع صفحات PDFs الأصلية، وبقيت مطابقة للملفات المحفوظة:

| السيناريو | SATISFIED | CONTRADICTED | MISSING_EVIDENCE | NEEDS_REVIEW |
|---|---:|---:|---:|---:|
| case_101 | 11 | 0 | 0 | 3 |
| case_202 | 2 | 8 | 0 | 3 |
| case_303 | 3 | 0 | 0 | 10 |

الأرقام دي تحقق من **Saved Demo** وليست تشغيل OpenAI جديدًا. الأدلة التاريخية للـAPI والـBenchmark ما زالت في `docs/`، وتقرير الـBenchmark مكتوب بصفته LLM-Judged Development؛ لم ننشئ Human Gold أو Holdout.

## MLflow

- التسجيل اختياري بـ`TENDERPROOF_MLFLOW_ENABLED=1`، وفشله لا يوقف التحليل.
- ثبتنا SDK وUI، وسجلنا فعليًا مراحل agent1 وagent2 وagent3 وvalidation من MOCK، وسجلات تحقق SAVED_DEMO في SQLite، وفحصنا صفحة Runs بصريًا.
- نسجل counters ووقت التنفيذ ونجاح التحقق فقط. لا نصوص مستندات أو اقتباسات أو أسماء ملفات أو مفاتيح أو JSON خاص، ولا Precision/Recall/F1 بلا مرجع صالح.
- افتح **Model training → Runs** في `TenderProof_Evaluation`؛ GenAI Overview ليس مستخدمًا هنا. طريقة التفعيل ومكان قاعدة البيانات في README.

## Real AI والأمان

- جاهزية المفتاح والـGate اختُبرت محليًا وداخل Docker وأعادت READY، والمفتاح موجود كـruntime Secret فقط. اختيار AI والموافقة غير المفعّلة افتراضيًا اتفحصوا من الواجهة.
- **صفر استدعاءات OpenAI مدفوعة أثناء التكامل**. لم نختبر صلاحية المفتاح أو الرصيد عن بعد، ولم ندّع نجاح تجربة AI جديدة. نحتفظ بأدلة القبول التاريخية كما هي.
- الموافقة قبل التحليل، حد 3 طلبات توليد، سقف تقديري محجوز $0.50، وعدم إعادة المحاولة وقفل التشغيل الواحد محفوظة. لم نحذف قفلًا أو نُعد تسليح محاولة. أعدنا بيئة Docker للاختيار الافتراضي المجاني بعد فحص الجاهزية.
- فحص كل الفروع المسحوبة: 182 Git blobs تاريخية بلا credential-pattern findings أو ملفات .env/.secrets/runtime متتبعة. فحص صورة Docker أكد استبعاد المفاتيح وPDFs و.env وruntime. Build context بقي allowlist صريحًا؛ كاش الحزم يحتوي public wheels فقط ولا يدخل الصورة أو Git.
- إصدارات Core requirements مثبتة على البيئة المستقرة، مع MLflow 3.17.2. البناء الأول يحتاج إنترنت؛ BuildKit يستخدم كاش اعتماديات فقط لتحمل بطء PyPI.

## الرجوع للإصدار المستقر

المجلد `D:/TenderProof-Final` بقي بدون تعديل. نسخة Git قابلة للاسترجاع: `D:/TenderProof-Stable-194c472.bundle`؛ تم التحقق منها وتحتوي التاريخ الكامل. صورة Docker المستقرة محفوظة محليًا باسم `tenderproof-stable:194c472`. فرع release الأصلي باقٍ على GitHub.

`docs/source-file-hashes.json` وملفات previous/final-verification القديمة أدلة تاريخية لحزمة Final السابقة. `DELIVERY_MANIFEST.json` هو جرد ملفات النسخة الموحدة الحالية، وليس جرد runtime أو أسرار.
