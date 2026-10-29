import re
import unittest
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pypdf import PdfReader

from pdf_reader import _recover_arabic_run, normalize_arabic_text, read_pdf
from validation import build_line_index, documents_complete, source_uncertain, validate_citation


FIXTURES = Path(__file__).parent / "fixtures"
# Logical contextual forms for "بيان"; reversing these simulates pypdf's
# prepending of a logical Arabic run. No dictionary or guessed wording is used.
SHAPED = "\ufe91\ufef4\ufe8e\u0646"


class TestArabicExtraction(unittest.TestCase):
    def test_logical_arabic_and_mixed_identifiers_are_not_reversed(self):
        text = "غير صالح للاستخدام الرسمي TEST-ORG-001 2026 ٢٠٢٦ A3/A4"
        self.assertEqual(_recover_arabic_run(text), text)
        self.assertEqual(normalize_arabic_text(text), (text, True))

    def test_presentation_forms_do_not_alone_imply_reversal(self):
        self.assertEqual(_recover_arabic_run(SHAPED), "بيان")
        self.assertEqual(_recover_arabic_run(SHAPED[::-1]), "بيان")

    def test_reversal_precedes_ligature_expansion(self):
        # "بلا": expanding lam-alef before reversal would turn it into alef-lam.
        logical = "\ufe91\ufefc"
        self.assertEqual(_recover_arabic_run(logical[::-1]), "بلا")

    def test_ltr_tokens_are_hard_boundaries(self):
        for token in ("TEST-ORG-001", "2026", "12.50", "A3/A4", "English"):
            with self.subTest(token=token):
                text = SHAPED[::-1] + " " + token
                self.assertEqual(_recover_arabic_run(text), "نايب " + token)

    def test_pypdf_reversed_arabic_indic_digits_and_line_endings(self):
        run = (SHAPED + " ٢٠٢٦")[::-1] + "\r\n"
        self.assertEqual(_recover_arabic_run(run), "بيان ٢٠٢٦\r\n")

    def test_conflicting_direction_evidence_is_not_guessed(self):
        raw = SHAPED + " " + SHAPED[::-1]
        self.assertEqual(_recover_arabic_run(raw), "بيان نايب")

    def test_unshaped_reversed_arabic_is_left_for_review(self):
        text = "يمسرلا مادختسالل حلاص ريغ"
        self.assertEqual(_recover_arabic_run(text), text)

    def test_company_and_previous_work_actual_text_and_schema(self):
        for filename, page_count in (("01_company_profile.pdf", 1),
                                     ("04_previous_work.pdf", 2)):
            result = read_pdf(FIXTURES / filename, document_id="arabic", role="COMPANY",
                              completeness="COMPLETE", completeness_basis="TEST_FIXTURE")
            self.assertEqual(set(result), {"document_id", "filename", "role", "completeness",
                                           "completeness_basis", "pages", "warnings"})
            self.assertEqual(result["completeness"], "COMPLETE")
            self.assertEqual(result["completeness_basis"], "TEST_FIXTURE")
            self.assertEqual(len(result["pages"]), page_count)
            raw_pages = PdfReader(FIXTURES / filename).pages
            for number, page in enumerate(result["pages"], 1):
                with self.subTest(filename=filename, page=number):
                    text = page["text"]
                    self.assertEqual(set(page), {"pdf_page", "text", "readability",
                                                 "extraction_method", "tables", "warnings"})
                    self.assertEqual(page["pdf_page"], number)
                    self.assertIn("غير صالح للاستخدام الرسمي", text)
                    self.assertIn("نايل لخدمات تكنولوجيا المكاتب", text)
                    self.assertIn("تاريخ إعداد النسخة: ٢٠ أكتوبر ٢٠٢٦", text)
                    self.assertIn("الكيان: TEST-ORG-001", text)
                    self.assertIn("Nile O\ufb03ce T echnology Services", text)
                    # Preserve every English word, code, and European number,
                    # including repetition and order, not only one sentinel.
                    pattern = r"[A-Za-z0-9\ufb00-\ufb06]+(?:[-@./][A-Za-z0-9\ufb00-\ufb06]+)*"
                    raw = raw_pages[number - 1].extract_text()
                    self.assertEqual(re.findall(pattern, text), re.findall(pattern, raw))
                    self.assertEqual(Counter(c for c in text if c.isdigit()),
                                     Counter(c for c in raw if c.isdigit()))
                    self.assertEqual(page["readability"], "READABLE")
                    self.assertEqual(page["extraction_method"], "NATIVE_TEXT")
                    self.assertTrue(any(w.startswith("INFO:") for w in page["warnings"]))
                    if filename == "04_previous_work.pdf":
                        self.assertIn(f"TEST-CONTRACT-10{number}", text)
                        self.assertIn(f"TEST-ACCEPT-10{number}", text)
                        self.assertIn("بيان سابقة الأعمال والاستلام النهائي", text)
                        self.assertIn("١٥ جهازًا" if number == 1 else "١٢ جهازًا", text)

    def test_already_ordered_arabic_table_and_numbers(self):
        page = read_pdf(FIXTURES / "arabic_table.pdf", document_id="table", role="COMPANY")["pages"][0]
        for text in ("المنتج", "الكمية", "السعر", "لابتوب", "شاشة", "طابعة",
                     "Laptop", "Monitor", "Printer", "25000", "6000", "4500"):
            self.assertIn(text, page["text"])
        self.assertEqual(page["tables"], [])
        self.assertEqual(page["readability"], "READABLE")

    def _read_mock_arabic(self, callback_text=None, fail=False):
        raw = SHAPED[::-1]

        def extract_text(*, visitor_text=None):
            if visitor_text:
                if fail:
                    raise RuntimeError("unsupported callback")
                visitor_text(raw if callback_text is None else callback_text, None, None, None, None)
            return raw

        reader = SimpleNamespace(is_encrypted=False, pages=[SimpleNamespace(extract_text=extract_text)])
        with patch("pdf_reader.PdfReader", return_value=reader):
            return read_pdf(FIXTURES / "01_company_profile.pdf", document_id="mock", role="COMPANY")["pages"][0]

    def test_inconsistent_callbacks_preserve_original_order_and_warn(self):
        page = self._read_mock_arabic(callback_text=SHAPED * 2)
        self.assertEqual(page["text"], "نايب")
        self.assertEqual(page["readability"], "PARTIAL")
        self.assertTrue(any("did not match" in w for w in page["warnings"]))

    def test_callback_failure_preserves_text_and_warns(self):
        page = self._read_mock_arabic(fail=True)
        self.assertEqual(page["text"], "نايب")
        self.assertEqual(page["readability"], "PARTIAL")
        self.assertTrue(any("run extraction failed" in w for w in page["warnings"]))


    def test_short_bounded_words_recover_from_contextual_forms(self):
        # These fragments are present in the real company profile; no dictionary substitution.
        self.assertEqual(_recover_arabic_run(" ﻒﺋﺎﻇوو ، "), " ، ووظائف ")
        self.assertEqual(_recover_arabic_run("،حﻼﺻﻺﻟ "), " للإصلاح،")
        page = read_pdf(FIXTURES / "01_company_profile.pdf", document_id="company", role="COMPANY")["pages"][0]
        self.assertIn("ووظائف", page["text"])
        self.assertIn("للإصلاح", page["text"])
        self.assertEqual(page["readability"], "READABLE")

    def test_correctly_extracted_arabic_does_not_require_review_just_for_language(self):
        doc = read_pdf(FIXTURES / "04_previous_work.pdf", document_id="works", role="COMPANY",
                       completeness="COMPLETE", completeness_basis="TEST_FIXTURE")
        self.assertTrue(documents_complete([doc]))
        for page in doc["pages"]:
            quote = next(line for line in page["text"].splitlines() if "نطاق العقد" in line)
            citation = {"document_id": "works", "pdf_page": page["pdf_page"], "quote": quote}
            validate_citation(citation, [doc])
            self.assertFalse(source_uncertain([citation], [doc]))
            self.assertTrue(source_uncertain([citation], [doc], table=True))

    def test_local_tender_text_and_uncertainty_match_inspected_pages(self):
        path = FIXTURES / "ida-335.pdf"
        if not path.is_file():
            self.skipTest("Private local tender is optional.")
        doc = read_pdf(path, document_id="tender", role="TENDER")
        pages, lookup = build_line_index(doc)
        self.assertEqual(doc["pages"][2]["readability"], "READABLE")
        self.assertEqual(doc["pages"][6]["readability"], "READABLE")
        self.assertEqual(doc["pages"][3]["readability"], "PARTIAL")
        self.assertEqual(doc["pages"][5]["readability"], "PARTIAL")
        self.assertEqual(doc["completeness"], "UNKNOWN")
        for number in (3, 4, 6, 7):
            raw = PdfReader(path).pages[number - 1].extract_text()
            self.assertEqual(Counter(c for c in doc["pages"][number - 1]["text"] if c.isdigit()),
                             Counter(c for c in raw if c.isdigit()))
        registration = next(c for c in lookup.values() if c["pdf_page"] == 4 and "السجل التجاري" in c["quote"])
        experience = next(c for c in lookup.values() if c["pdf_page"] == 4 and "ثلاث سنوات حديثة" in c["quote"])
        technical = next(c for c in lookup.values() if c["pdf_page"] == 6 and "تقديم الدعم الفني الكامل" in c["quote"])
        quantity = next(c for c in lookup.values() if c["pdf_page"] == 6 and "B7030" in c["quote"])
        self.assertFalse(source_uncertain([registration, technical], [doc]))
        self.assertTrue(source_uncertain([experience], [doc]))
        self.assertTrue(source_uncertain([quantity], [doc], table=True))
        # The visible negation is truncated by the font map: flag it, never invent letters.
        self.assertIn("وان ل", experience["quote"])
        self.assertTrue(any(line["needs_review"] for page in pages if page["pdf_page"] == 4 for line in page["lines"]))


if __name__ == "__main__":
    unittest.main()
