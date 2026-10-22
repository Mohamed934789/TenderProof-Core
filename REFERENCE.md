# النسخة المرجعية
الأصل D:\TenderProof-AI؛ فرع main؛ Commit مستقر 5999295، إصدار v0.6.0.
الملفات المتتبعة بلا تعديل عند الفحص، ولا tag أو remote ظاهرين.
Git حفظ محلي، وليس نسخة خارج الجهاز.
أربعة مستندات خارج Git تُركت كما هي: PROJECT_SIMPLIFICATION_PLAN.md،
TenderProof_AI_From_Zero_To_Agents.html وPDF، وTenderProof_Team_Onboarding.pdf داخل docs.
ليست ضمن commit الإصدار؛ كود الإصدار محفوظ بالفعل. لم نعمل commit أو tag في الأصل.

## خريطة الأصل
- PDF: backend/app/pdf_processing/processor.py :: NativePDFProcessor.process
- Extraction: backend/app/extraction/openai.py :: OpenAIRequirementExtractor.extract،
  ومعه prompts.py وsegments.py وcommon.py وscope.py وcoverage.py.
- Verification: backend/app/verification/openai.py :: OpenAIEvidenceVerifier.verify،
  ومعه prompts.py وsources.py وrules.py.
- Validation: backend/app/contracts/validation.py :: validate_citation / validate_report؛
  models.py وinterfaces.py للعقود.
- Orchestrator: backend/app/service/orchestrator.py :: Orchestrator.run؛ jobs.py وstorage.py.

المراجع للقراءة فقط؛ لم ننسخ تنفيذها. العربي PARTIAL والتغطية غير مثبتة في الأصل،
ونجاح اختبارات البرامج ليس دقة AI.

## العودة للأصل
افتح D:\TenderProof-AI في نافذة مستقلة أو مجلد Reference.
راجع git status وgit log -1؛ لا reset --hard ولا clean.
من PowerShell في الأصل: .\run.ps1 لتشغيل Mock،
.\run.ps1 -Mode Status للحالة، .\run.ps1 -Mode Stop للإيقاف الآمن.
رمز الاتصال المحلي في runtime/phase4/api-token.txt، مش مفتاح OpenAI.
الملفات والتقارير المحلية لم تتغير. نتائج AI السابقة موضحة في docs/DEMO.md
كتشغيل سابق معلن؛ لا تبدأ paid analysis جديدة.
لو port 8765 مشغول افحص Status، لا توقف process عشوائيًا.

لو احتجنا استرجاع كود commit مستقبلًا، نعمل checkout/worktree منفصل بعد مراجعة،
ولا نستبدل الأصل أو نحذف مستنداته. الـCore Git مستقل، مش nested repo أو submodule.
إخفاء Explorer لا يمنع تحرير المرجع تقنيًا؛ راجع المسار قبل الحفظ.
