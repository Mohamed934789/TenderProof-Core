# TenderProof Core
مساحة مستقلة للفريق، مش نسخة من الـAgents الجاهزة. كل دوال التنفيذ
ترفع NotImplementedError عمدًا. مفيش parser أو Mock أو AI أو Backend أو UI شغّال هنا.

## افتح المشروع
VS Code > File > Open Workspace from File > TenderProof-Team.code-workspace.
هتشوف Core والأصل كمرجع. اسم Reference تذكير فقط، مش منع كتابة تقني.
الإعدادات تخص النافذة؛ مفيش ملفات إعداد اتضافت داخل الأصل.
Dependencies وCache وRuntime مخفيين بصريًا فقط؛ المصدر وtests وfixtures وschemas
وgenerated ظاهرين. لو فتحت مجلد Core وحده، إخفاء الـWorkspace مش هيتطبق.

## الدوال والعقود المبدئية
| الدالة | المدخل | المخرج |
|---|---|---|
| pdf_reader.read_pdf | مسار PDF + document_id + role | DocumentPages |
| agent1.extract_requirements | صفحات الكراسة + mode | قائمة Requirement |
| agent2.verify_requirements | الشروط + صفحات الشركة + reference_date + mode | قائمة Finding |
| validation.validate_citation | Citation + مستندات مسموحة | لا شيء أو ValueError |
| validation.validate_report | Report + المستندات | لا شيء أو ValueError |
| orchestrator.analyze | مسارات الكراسة والشركة + التاريخ + mode | Report بعد نجاح كل الخطوات |

models.py عقد تعليمي DRAFT مكتوب بـTypedDict، مش فحص قيم أثناء التشغيل.
العقد مبسط وغير مطابق لكل حقول API v1 في الأصل. لاحقًا نكتب adapter صريح،
بدل تغيير Schemas الأصلية. المنسق ينادي المكونات بترتيب ثابت، مش Autonomous Agents.

## مثال JSON واحد لانتقال البيانات
مثال صناعي للشرح فقط، لم ينتج عن تحليل منفذ. الظرف الخارجي يعرض انتقال البيانات؛
Report هو محتوى report فقط.
```json
{
  "pdf_reader_output": {
    "document_id": "tender-example",
    "filename": "example.pdf",
    "role": "TENDER",
    "pages": [
      {"pdf_page": 1, "text": "The bidder must submit a commercial registration.", "readability": "READABLE"}
    ]
  },
  "company_documents": [],
  "report": {
    "mode": "MOCK",
    "reference_date": "2026-11-01",
    "coverage_confirmed": false,
    "requirements": [{
      "requirement_id": "R-0001",
      "text": "Submit a commercial registration.",
      "needs_review": false,
      "sources": [{
        "document_id": "tender-example",
        "pdf_page": 1,
        "quote": "The bidder must submit a commercial registration."
      }]
    }],
    "findings": [{
      "requirement_id": "R-0001",
      "status": "MISSING_EVIDENCE",
      "explanation": "No company evidence supplied in this controlled example.",
      "evidence": []
    }],
    "warnings": ["Illustration only. Coverage not confirmed."]
  }
}
```

لو مواد الشركة موجودة لكن القراءة أو اكتمالها غير مؤكد، نرجع NEEDS_REVIEW،
مش غيابًا قاطعًا. العقد المبدئي لا يمثل completeness بالتفصيل لسه:
أول مراجعة لـMember 1 لازم تحسم تمثيله قبل دعم حسم نتائج الشركة.
لا نفترض إن كل ملف مرفوع كامل تلقائيًا.

## أول تشغيل تطوير
راجعوا TEAM_TASKS.md. اتأكدوا من Python فعلي، يفضل 3.12، باستخدام python --version؛
WindowsApps/python.exe قد يكون alias فقط. لم تُنشأ .venv أو تُثبت مكتبات الآن.
لا إعدادات Windows عامة ولا مفاتيح API في المرحلة دي.
ابدأوا ببيانات في الذاكرة واختبارات unittest وMock محلي يكتبه الفريق.
أي موديل حقيقي يحتاج خطة طلبات وتكلفة وموافقة جديدة.

## القبول
الصفحة الأصلية تبدأ من 1، والاقتباس لازم موجود فيها.
SATISFIED تحتاج دليلًا واضحًا وكافيًا، والغموض NEEDS_REVIEW.
غياب الدليل مختلف عن التعارض؛ التاريخ يتقارن برمجيًا.
فشل خطوة لا ينتج تقريرًا مكتملًا. coverage_confirmed لا يصبح true بمجرد اكتمال التشغيل.
كل الخمسة يفهموا الرحلة كلها. لا تعديل مرجع ولا نقل Backend أو UI.
الرجوع للأصل في REFERENCE.md.
