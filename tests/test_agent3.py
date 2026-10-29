"""Regression checks for the evidence agent; every AI client here is a local fake."""
import asyncio
import copy

import pytest

from agent3 import verify_company

PAGE_TEXT = "ترخيص صيانة. ينتهي الترخيص في 15 أكتوبر 2026"


def result_for(kind="ELIGIBILITY", ident="REQ-002", **changes):
    result = {"target_type": kind, "target_id": ident, "evidence_found": True,
              "sources": [{"line_id": "D001-P001-L0001"}],
              "assessment": "SUPPORTS", "explanation": "الدليل يدعم المتطلب.",
              "expiry_date": "2026-10-15", "offered_quantity": None, "offered_unit": None}
    result.update(changes)
    return result


def no_evidence():
    return result_for(evidence_found=False, sources=[], assessment="UNCERTAIN", expiry_date=None)


class FakeClient:
    def __init__(self, results):
        self.results, self.calls = results, 0

    async def generate(self, **kwargs):
        self.calls += 1
        self.input_data = kwargs["input_data"]
        return {"payload": {"results": copy.deepcopy(self.results)}, "provider": "fake",
                "model": "fake-1", "usage": None}


def inputs(completeness="COMPLETE", readability="READABLE", text=PAGE_TEXT):
    provenance = {"mode": "AI", "provider": "fake", "model": "fake-1", "prompt_version": "t"}
    eligibility = {"requirements": [{
        "requirement_id": "REQ-002", "text": "ترخيص صيانة ساري في تاريخ التقييم",
        "category": "LICENSE", "needs_review": False, "review_reasons": [], "sources": [],
    }], "provenance": provenance, "warnings": []}
    technical = {"boq_status": "NOT_FOUND", "boq_review_reasons": [], "boq_items": [],
                 "technical_requirements": [], "provenance": provenance, "warnings": []}
    docs = [{"document_id": "nile-license", "filename": "license.pdf", "role": "COMPANY",
             "completeness": completeness, "completeness_basis": "TEST_FIXTURE", "warnings": [],
             "pages": [{"pdf_page": 1, "text": text, "readability": readability,
                        "extraction_method": "NATIVE_TEXT", "tables": [], "warnings": []}]}]
    return eligibility, technical, docs


def run(results, *, mode="AI", **kwargs):
    eligibility, technical, docs = inputs(**kwargs)
    client = FakeClient(results)
    output = asyncio.run(verify_company(eligibility, technical, docs, reference_date="2026-11-01",
                                       client=client, mode=mode))
    return output["findings"][0], client


def test_expired_license_is_contradicted():
    finding, _ = run([result_for()])
    assert finding["status"] == "CONTRADICTED"
    assert finding["evidence"][0]["pdf_page"] == 1


def test_valid_license_is_satisfied():
    text = "ينتهي الترخيص في 1 يناير 2027"
    finding, _ = run([result_for(expiry_date="2027-01-01")], text=text)
    assert finding["status"] == "SATISFIED"


def test_ungrounded_expiry_date_needs_review():
    finding, _ = run([result_for(expiry_date="2027-01-01")])
    assert finding["status"] == "NEEDS_REVIEW"


def test_model_supplied_quote_is_rejected():
    with pytest.raises(ValueError):
        run([result_for(quote="جملة مش موجودة في الصفحة")])


def test_no_evidence_in_complete_docs_is_missing():
    assert run([no_evidence()])[0]["status"] == "MISSING_EVIDENCE"


@pytest.mark.parametrize("quality", ["UNREADABLE", "PARTIAL"])
def test_no_evidence_in_uncertain_docs_needs_review(quality):
    assert run([no_evidence()], readability=quality)[0]["status"] == "NEEDS_REVIEW"


def test_mock_never_calls_llm():
    finding, client = run([], mode="MOCK")
    assert client.calls == 0
    assert finding["status"] == "NEEDS_REVIEW"


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "unknown", "wrong-type"])
def test_invalid_result_coverage_is_rejected(mutation):
    results = [result_for()]
    if mutation == "missing":
        results = []
    elif mutation == "duplicate":
        results.append(result_for())
    elif mutation == "unknown":
        results[0]["target_id"] = "wrong"
    else:
        results[0]["target_type"] = "TECHNICAL"
    with pytest.raises(ValueError):
        run(results)


def run_boq(offered_quantity, offered_unit="طابعة", quote=None, target_review=False, warnings=()):
    eligibility, technical, docs = inputs()
    eligibility["requirements"] = []
    quote = quote or f"نقدم صيانة {offered_quantity or 'عدد غير محدد'} {offered_unit or ''} Xerox B7070"
    docs[0]["pages"][0]["text"] = quote
    docs[0]["pages"][0]["warnings"] = list(warnings)
    technical["boq_items"] = [{
        "boq_item_id": "BOQ-1", "description": "صيانة طابعات Xerox B7070",
        "quantity": {"raw_text": "20", "decimal_value": "20", "sources": []},
        "unit": "طابعة", "unit_normalized": None, "table_id": None,
        "needs_review": target_review, "review_reasons": ["table uncertainty"] if target_review else [],
        "sources": [],
    }]
    result = result_for("BOQ", "BOQ-1", expiry_date=None,
                        offered_quantity=offered_quantity, offered_unit=offered_unit)
    output = asyncio.run(verify_company(eligibility, technical, docs, reference_date="2026-11-01",
                                       client=FakeClient([result]), mode="AI"))
    return output["findings"][0]


def test_boq_quantity_too_low_is_contradicted():
    assert run_boq("15")["status"] == "CONTRADICTED"


def test_boq_quantity_enough_is_satisfied():
    assert run_boq("20")["status"] == "SATISFIED"


def test_boq_unit_mismatch_needs_review():
    assert run_boq("20", offered_unit="جهاز")["status"] == "NEEDS_REVIEW"


def test_boq_missing_quantity_needs_review():
    assert run_boq(None)["status"] == "NEEDS_REVIEW"


@pytest.mark.parametrize("quantity", ["NaN", "Infinity", "-1", "999"])
def test_boq_ungrounded_and_invalid_quantities_need_review(quantity):
    assert run_boq(quantity, quote="نقدم صيانة 20 طابعة Xerox B7070")["status"] == "NEEDS_REVIEW"


def test_boq_model_number_does_not_prove_quantity():
    assert run_boq("7070", quote="نقدم صيانة طابعة Xerox B7070")["status"] == "NEEDS_REVIEW"


def test_uncertain_target_cannot_be_satisfied():
    assert run_boq("20", target_review=True)["status"] == "NEEDS_REVIEW"


def test_completeness_without_basis_cannot_prove_missing():
    eligibility, technical, docs = inputs()
    docs[0]["completeness_basis"] = "UNKNOWN"
    output = asyncio.run(verify_company(eligibility, technical, docs, reference_date="2026-11-01",
                                       client=FakeClient([no_evidence()]), mode="AI"))
    assert output["findings"][0]["status"] == "NEEDS_REVIEW"


def test_partial_evidence_page_cannot_prove_compliance():
    assert run([result_for()], readability="PARTIAL")[0]["status"] == "NEEDS_REVIEW"


def test_arabic_indic_expiry_is_compared_in_python():
    quote = "ينتهي الترخيص في ١٥ أكتوبر ٢٠٢٦"
    assert run([result_for()], text=quote)[0]["status"] == "CONTRADICTED"


@pytest.mark.parametrize("sources", [[], [{"line_id": "D001-P001-L9999"}],
                                    [{"line_id": "D001-P001-L0001"}, {"line_id": "D001-P002-L0001"}]])
def test_invalid_evidence_line_references_are_rejected(sources):
    with pytest.raises(ValueError):
        run([result_for(sources=sources)])


def test_company_line_ids_do_not_collide_across_documents():
    eligibility, technical, docs = inputs()
    second = copy.deepcopy(docs[0])
    second["document_id"] = "second-license"
    second["pages"][0]["text"] = "  ينتهي الترخيص في 1 يناير 2027  "
    docs.append(second)
    client = FakeClient([result_for(sources=[{"line_id": "D002-P001-L0001"}], expiry_date="2027-01-01")])
    output = asyncio.run(verify_company(eligibility, technical, docs, reference_date="2026-11-01",
                                       client=client, mode="AI"))
    assert output["findings"][0]["status"] == "SATISFIED"
    assert output["findings"][0]["evidence"] == [{"document_id": "second-license", "pdf_page": 1,
                                                 "quote": "  ينتهي الترخيص في 1 يناير 2027  "}]
    assert client.input_data["documents"][0]["pages"][0]["lines"][0]["line_id"] == "D001-P001-L0001"
    assert client.input_data["documents"][1]["pages"][0]["lines"][0]["line_id"] == "D002-P001-L0001"


def test_all_evidence_lines_keep_their_original_pages_and_whitespace():
    eligibility, technical, docs = inputs(text="  ترخيص صيانة.  ")
    second_page = copy.deepcopy(docs[0]["pages"][0])
    second_page.update(pdf_page=2, text="\n ينتهي الترخيص في 15 أكتوبر 2026\t")
    docs[0]["pages"].append(second_page)
    client = FakeClient([result_for(sources=[{"line_id": "D001-P001-L0001"},
                                            {"line_id": "D001-P002-L0002"}])])
    output = asyncio.run(verify_company(eligibility, technical, docs, reference_date="2026-11-01",
                                       client=client, mode="AI"))
    assert output["findings"][0]["status"] == "CONTRADICTED"
    assert output["findings"][0]["evidence"] == [
        {"document_id": "nile-license", "pdf_page": 1, "quote": "  ترخيص صيانة.  "},
        {"document_id": "nile-license", "pdf_page": 2, "quote": " ينتهي الترخيص في 15 أكتوبر 2026\t"},
    ]


@pytest.mark.parametrize("warning,expected", [
    ("INFO: Unused font mapping warning.", "SATISFIED"),
    ("TABLE: Table structure is unverified.", "SATISFIED"),
    ("Unresolved font mapping affects extracted text.", "NEEDS_REVIEW"),
])
def test_advisory_notes_do_not_block_clear_valid_license(warning, expected):
    text = "ينتهي الترخيص في 1 يناير 2027"
    eligibility, technical, docs = inputs(text=text)
    docs[0]["pages"][0]["warnings"] = [warning]
    output = asyncio.run(verify_company(eligibility, technical, docs, reference_date="2026-11-01",
                                       client=FakeClient([result_for(expiry_date="2027-01-01")]), mode="AI"))
    assert output["findings"][0]["status"] == expected


def test_explicit_noncompliance_does_not_require_an_invented_expiry_date():
    text = "ترخيص الشركة غير ساري."
    result = result_for(assessment="CONTRADICTS", expiry_date=None, explanation="الترخيص غير ساري صراحةً.")
    assert run([result], text=text)[0]["status"] == "CONTRADICTED"


@pytest.mark.parametrize("include_damaged_source,expected", [(False, "SATISFIED"), (True, "NEEDS_REVIEW")])
def test_localized_damage_only_blocks_the_affected_evidence(include_damaged_source, expected):
    eligibility, technical, docs = inputs(text="ينتهي الترخيص في 1 يناير 2027\nبيان تالف \ufffd", readability="PARTIAL")
    docs[0]["pages"][0]["warnings"] = ["TEXT_LINE:2: Unmapped glyph."]
    sources = [{"line_id": "D001-P001-L0001"}]
    if include_damaged_source:
        sources.append({"line_id": "D001-P001-L0002"})
    output = asyncio.run(verify_company(eligibility, technical, docs, reference_date="2026-11-01",
                                       client=FakeClient([result_for(sources=sources, expiry_date="2027-01-01")]), mode="AI"))
    assert output["findings"][0]["status"] == expected


def test_missing_evidence_needs_all_text_readable_even_when_damage_is_elsewhere():
    eligibility, technical, docs = inputs(text="بيانات الشركة واضحة.\nبيان ترخيص غير مقروء \ufffd", readability="PARTIAL")
    docs[0]["pages"][0]["warnings"] = ["TEXT_LINE:2: Unmapped glyph."]
    output = asyncio.run(verify_company(eligibility, technical, docs, reference_date="2026-11-01",
                                       client=FakeClient([no_evidence()]), mode="AI"))
    assert output["findings"][0]["status"] == "NEEDS_REVIEW"


def test_company_table_uncertainty_cannot_be_ignored_for_boq():
    assert run_boq("20", warnings=["TABLE: Offered quantities have unverified columns."])["status"] == "NEEDS_REVIEW"


def test_multi_line_quote_cannot_skip_localized_text_damage():
    from validation import source_uncertain
    _, _, docs = inputs(text="متطلب واضح.\nتاريخ تالف \ufffd", readability="PARTIAL")
    docs[0]["pages"][0]["warnings"] = ["TEXT_LINE:2: Unmapped glyph."]
    source = {"document_id": "nile-license", "pdf_page": 1, "quote": "واضح.\nتاريخ"}
    assert source_uncertain([source], docs)


def verify_one(quote, requirement, result=None, *, synthetic_test=False):
    eligibility, technical, docs = inputs(text=quote)
    eligibility["requirements"][0]["text"] = requirement
    result = copy.deepcopy(result or result_for(expiry_date=None))
    result["sources"] = [{"line_id": f"D001-P001-L{i:04d}"} for i, line in
                         enumerate(quote.splitlines(), 1) if line.strip()]
    client = FakeClient([result])
    output = asyncio.run(verify_company(eligibility, technical, docs, reference_date="2026-10-31",
                                       client=client, mode="AI", synthetic_test=synthetic_test))
    return output["findings"][0], client


@pytest.mark.parametrize("days,expected", [("٩٠", "SATISFIED"), ("٤٥", "CONTRADICTED")])
def test_offer_duration_is_grounded_in_days_and_the_closing_date(days, expected):
    quote = f"يسري هذا العرض لمدة {days} يومًا تبدأ من تاريخ الإقفال المحدد في ٣١ أكتوبر ٢٠٢٦."
    requirement = "يجب أن ينص العرض على سريانه لمدة لا تقل عن 90 يومًا من تاريخ الإقفال."
    finding, _ = verify_one(quote, requirement)
    assert finding["status"] == expected
    assert finding["evidence"][0]["quote"] == quote


@pytest.mark.parametrize("quote", [
    "يسري هذا العرض لمدة ٩٠ يومًا تبدأ من تاريخ الإقفال المحدد في ١ أكتوبر ٢٠٢٦.",
    "يسري هذا العرض حتى إخطار آخر دون تحديد عدد الأيام.",
    "يسري هذا العرض لمدة ٩٠ يومًا تبدأ من تاريخ الإقفال المحدد في ٣١ أكتوبر ٢٠٢٦. العرض مشروط.",
    "يسري هذا العرض لمدة ٩٠ يومًا تبدأ من تاريخ الإقفال المحدد في ٣١ أكتوبر ٢٠٢٦. نسخة أخرى لمدة ٤٥ يومًا.",
])
def test_unclear_offer_validity_stays_under_review(quote):
    assert verify_one(quote, "سريان العرض لمدة لا تقل عن 90 يومًا")[0]["status"] == "NEEDS_REVIEW"


@pytest.mark.parametrize("repair,expected", [
    ("يحدد وفق طبيعة العطل بعد الفحص الفني", "NEEDS_REVIEW"),
    ("خلال ٤٨ ساعة", "CONTRADICTED"),
])
def test_missing_repair_limit_is_distinct_from_an_explicit_breach(repair, expected):
    quote = f"زمن الاستجابة الفنية: خلال ٤ ساعات.\nزمن إعادة الجهاز إلى الخدمة: {repair}."
    requirement = "الاستجابة خلال ٤ ساعات وإعادة الجهاز إلى الخدمة خلال ٢٤ ساعة."
    result = result_for(assessment="CONTRADICTS", expiry_date=None)
    assert verify_one(quote, requirement, result)[0]["status"] == expected


def test_explicit_response_breach_survives_an_unknown_repair_deadline():
    quote = "زمن الاستجابة الفنية: خلال ٨ ساعات.\nزمن إعادة الجهاز إلى الخدمة: غير محدد."
    requirement = "الاستجابة خلال ٤ ساعات وإعادة الجهاز إلى الخدمة خلال ٢٤ ساعة."
    result = result_for(assessment="CONTRADICTS", expiry_date=None)
    assert verify_one(quote, requirement, result)[0]["status"] == "CONTRADICTED"


@pytest.mark.parametrize("synthetic_test,expected", [(False, "CONTRADICTED"), (True, "SATISFIED")])
def test_fictional_labels_do_not_enable_test_rules_automatically(synthetic_test, expected):
    quote = ("مستند افتراضي. صاحب البيان: شركة الاختبار. النشاط: صيانة أجهزة المكاتب.\n"
             "تاريخ الإصدار: ١ يناير ٢٠٢٦. تاريخ انتهاء السريان: ٣١ ديسمبر ٢٠٢٧.")
    result = result_for(assessment="CONTRADICTS", expiry_date="2027-12-31",
                        explanation="المحتوى مستوفٍ لكنه مستند افتراضي للاختبار.")
    finding, client = verify_one(quote, "ترخيص صيانة ساري بتاريخ الإقفال", result, synthetic_test=synthetic_test)
    assert finding["status"] == expected
    assert client.input_data["synthetic_test"] is synthetic_test


@pytest.mark.parametrize("date_line,expiry", [
    ("تاريخ الإصدار: ١ يناير ٢٠٢٦. تاريخ انتهاء السريان: ٣٠ سبتمبر ٢٠٢٦.", "2026-09-30"),
    ("تاريخ الإصدار: ١ يناير ٢٠٢٨. تاريخ انتهاء السريان: ٣١ ديسمبر ٢٠٢٨.", "2028-12-31"),
])
def test_synthetic_mode_does_not_waive_invalid_dates(date_line, expiry):
    quote = "صاحب البيان: شركة الاختبار. النشاط: صيانة أجهزة المكاتب.\n" + date_line
    result = result_for(assessment="CONTRADICTS", expiry_date=expiry, explanation="بيان افتراضي وتواريخه غير مستوفاة.")
    finding, _ = verify_one(quote, "ترخيص صيانة ساري", result, synthetic_test=True)
    assert finding["status"] != "SATISFIED"


def test_synthetic_mode_keeps_explicit_tax_arrears_contradicted():
    quote = ("اسم المنشأة: شركة الاختبار. توجد متأخرات ضريبية واجبة الأداء.\n"
             "تاريخ إصدار البيان: ١ يناير ٢٠٢٦. تاريخ انتهاء السريان: ٣١ ديسمبر ٢٠٢٦.")
    result = result_for(assessment="CONTRADICTS", expiry_date="2026-12-31",
                        explanation="بيان افتراضي يتضمن متأخرات ضريبية.")
    assert verify_one(quote, "بيان ضريبي ساري دون متأخرات", result, synthetic_test=True)[0]["status"] == "CONTRADICTED"


def test_synthetic_mode_cannot_waive_a_real_accreditation_requirement():
    quote = ("الجهة المصدرة: جهة افتراضية. الشركة المفوضة: شركة الاختبار.\n"
             "يشمل نطاق التفويض صيانة Xerox وCanon صراحة.\n"
             "تاريخ بدء السريان: ١ يناير ٢٠٢٦. تاريخ انتهاء السريان: ٣١ ديسمبر ٢٠٢٦.")
    result = result_for(assessment="CONTRADICTS", expiry_date="2026-12-31",
                        explanation="تفويض افتراضي وليس اعتمادًا حقيقيًا.")
    finding, _ = verify_one(quote, "تفويض باعتماد حقيقي من المصنع يشمل Xerox وCanon", result, synthetic_test=True)
    assert finding["status"] != "SATISFIED"


def test_license_evidence_does_not_prove_missing_authorization_is_contradicted():
    result = result_for(assessment="CONTRADICTS", expiry_date=None)
    finding, _ = verify_one("هذا بيان ترخيص نشاط وليس اعتماد مصنع.", "تفويض صيانة يشمل Xerox وCanon", result)
    assert finding["status"] == "NEEDS_REVIEW"


def test_arabic_conjunction_does_not_hide_the_end_of_a_date_range():
    from datetime import date
    from agent3 import _dates_in_text
    assert _dates_in_text("بين ١ نوفمبر ٢٠٢٣ و٣١ أكتوبر ٢٠٢٦") == {date(2023, 11, 1), date(2026, 10, 31)}
