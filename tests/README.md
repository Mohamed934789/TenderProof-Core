# اختبارات يكتبها الفريق
المجلد فاضي من اختبارات السلوك عمدًا؛ مفيش نجاح اختبارات مزعوم.
ابدأوا بمكتبة unittest القياسية، بلا تثبيت مبكر:
python -m unittest discover -s tests -v

1: test_contracts.py، 2: test_pdf_reader.py ثم test_agent1.py،
3: test_agent2.py وtest_validation.py، 4: test_user_journey_contract.py،
5: test_orchestrator.py.
صفر اختبارات ليس دليل نجاح. اكتبوا المتوقع أولًا، ثم نفذوا الكود.
