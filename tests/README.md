# اختبارات يكتبها الفريق - 3 Agents
مفيش ملفات اختبارات سلوك بعد. لم ننفذ منطق الأعضاء أو Prompts بدلًا منهم.
الفحوص الهيكلية وقت التجهيز لا تثبت تشغيل pipeline أو دقة AI.

| الملف المقترح | المسؤول | اختبارات القبول المطلوبة |
|---|---|---|
| test_contracts.py | 5 مع الجميع | أنواع الحقول وIDs، nullable لا صفر مخترع، provenance، UNKNOWN completeness |
| test_pdf_reader.py | 1 | رقم ونص كل صفحة، عربي/جدول مشوش، صفحة صورة، ملف غير صالح |
| test_agent1.py | 2 | أهلية ومستندات مستقلة، OR، نطاق ما بعد الترسية، اقتباس مختلق، شرط غامض |
| test_agent2.py | 3 | FOUND/NOT_FOUND/NEEDS_REVIEW، كميات ووحدات مجهولة، مواصفات بلا BOQ، تعذر ربط الأعمدة |
| test_agent3.py | 4 | الحالات الأربع، أهلية/فني/BOQ، عرض غير مقدم، completeness مجهول، دليل مخالف أو غامض |
| test_validation.py | 5 | صفحة/quote غلط، target مكرر/غائب، Decimal/تاريخ خاطئ، وحدات غير قابلة للتحويل، قطع بلا دليل |
| test_orchestrator.py | 5 | A3 بعد المخرجين المتحققين فقط، فشل مرحلة، قبول NOT_FOUND، عدم نشر تقرير جزئي |

ابدأ بunittest وFakeClient محلي يكتبه الفريق. Async interfaces يمكن اختبارها بـ
unittest.IsolatedAsyncioTestCase، دون تثبيت pytest أو SDK.
من الجذر، بعد اختيار Python:
python -m unittest discover -s tests -v
صفر اختبارات لا يساوي نجاح. Expected outcomes تُكتب أولًا.
Real AI evaluation منفصل: عينة جديدة وGround Truth معلن وحدوده، وبعد موافقة تكلفة جديدة.
لا نسب دقة من نجاح اختبارات Fake أو نوع TypedDict وحده.

## إعداد جهاز جديد
راجع خطوات Windows في README الرئيسي؛ البيئة تستخدم Python 3.12+ ولا Dependencies خارجية حاليًا.
قبل اختبار السلوك شغّل python scripts/check_environment.py داخل .venv.
في فحص التجهيز بتاريخ 24 أكتوبر 2026، unittest وجد صفر اختبارات وأرجع NO TESTS RAN / exit 1.
ده متوقع لغياب ملفات test_*.py، ولا يثبت صحة pipeline. لا تضف اختبارات وهمية لإخفاء الرسالة.
