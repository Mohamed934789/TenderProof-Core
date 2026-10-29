
import unittest
from pathlib import Path
from unittest.mock import patch

from pdf_reader import read_pdf


FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestReadPdf(unittest.TestCase):
    def test_read_pdf_preserves_page_numbers_and_text(self):
        pdf_path = FIXTURES_DIR / "01_company_profile.pdf"

        result = read_pdf(
            pdf_path,
            document_id="test-doc-001",
            role="COMPANY",
        )

        self.assertEqual(result["document_id"], "test-doc-001")
        self.assertEqual(result["filename"], pdf_path.name)
        self.assertEqual(len(result["pages"]), 1)

        page = result["pages"][0]
        self.assertEqual(page["pdf_page"], 1)
        self.assertIsInstance(page["text"], str)
        self.assertTrue(page["text"].strip())

    def test_missing_pdf_raises_file_not_found(self):
        missing_path = FIXTURES_DIR / "does_not_exist.pdf"

        with self.assertRaises(FileNotFoundError):
            read_pdf(
                missing_path,
                document_id="missing-doc",
                role="COMPANY",
            )

    def test_invalid_pdf_raises_value_error(self):
        invalid_path = FIXTURES_DIR / "invalid.pdf"
        invalid_path.write_text(
            "This is not a valid PDF file.",
            encoding="utf-8",
        )

        try:
            with self.assertRaises(ValueError):
                read_pdf(
                    invalid_path,
                    document_id="invalid-doc",
                    role="COMPANY",
                )
        finally:
            invalid_path.unlink(missing_ok=True)

    def test_blank_page_is_marked_unreadable(self):
        from pypdf import PdfWriter

        blank_path = FIXTURES_DIR / "blank_page.pdf"
        writer = PdfWriter()
        writer.add_blank_page(width=595, height=842)

        with blank_path.open("wb") as pdf_file:
            writer.write(pdf_file)

        try:
            result = read_pdf(
                blank_path,
                document_id="blank-doc",
                role="COMPANY",
            )

            page = result["pages"][0]
            self.assertEqual(page["pdf_page"], 1)
            self.assertEqual(page["text"], "")
            self.assertEqual(page["readability"], "UNREADABLE")
            self.assertEqual(page["extraction_method"], "NONE")
            self.assertTrue(page["warnings"])
        finally:
            blank_path.unlink(missing_ok=True)

    def test_default_completeness_is_unknown(self):
        result = read_pdf(
            FIXTURES_DIR / "01_company_profile.pdf",
            document_id="unknown-completeness",
            role="COMPANY",
        )

        self.assertEqual(result["completeness"], "UNKNOWN")
        self.assertEqual(result["completeness_basis"], "UNKNOWN")

    def test_every_page_has_quality_and_warnings(self):
        result = read_pdf(
            FIXTURES_DIR / "01_company_profile.pdf",
            document_id="page-quality",
            role="COMPANY",
        )

        self.assertTrue(result["pages"])

        for page in result["pages"]:
            with self.subTest(pdf_page=page["pdf_page"]):
                self.assertIsInstance(page["pdf_page"], int)
                self.assertIn(
                    page["readability"],
                    {"READABLE", "PARTIAL", "UNREADABLE"},
                )
                self.assertIsInstance(page["warnings"], list)
                self.assertTrue(page["warnings"])

    def test_image_only_page_is_not_claimed_as_readable(self):
        from pypdf import PdfWriter

        image_only_path = FIXTURES_DIR / "image_only_test.pdf"
        writer = PdfWriter()
        writer.add_blank_page(width=595, height=842)

        with image_only_path.open("wb") as pdf_file:
            writer.write(pdf_file)

        class ImageOnlyPage:
            def extract_text(self):
                return ""

        class ImageOnlyReader:
            is_encrypted = False
            pages = [ImageOnlyPage()]

        try:
            with patch(
                "pdf_reader.PdfReader",
                return_value=ImageOnlyReader(),
            ):
                result = read_pdf(
                    image_only_path,
                    document_id="image-only",
                    role="COMPANY",
                )

            page = result["pages"][0]
            self.assertEqual(page["readability"], "UNREADABLE")
            self.assertEqual(page["extraction_method"], "NONE")
            self.assertTrue(
                any(
                    "OCR is not implemented" in warning
                    for warning in page["warnings"]
                )
            )
        finally:
            image_only_path.unlink(missing_ok=True)

    def test_raw_table_text_does_not_claim_table_reconstruction(self):
        result = read_pdf(
            FIXTURES_DIR / "01_company_profile.pdf",
            document_id="table-check",
            role="COMPANY",
        )

        for page in result["pages"]:
            self.assertEqual(page["tables"], [])
            self.assertTrue(
                any(
                    "Table structure" in warning
                    for warning in page["warnings"]
                )
            )

    def test_arabic_table_pdf_preserves_extracted_text(self):
        result = read_pdf(
            FIXTURES_DIR / "arabic_table.pdf",
            document_id="arabic-table-test",
            role="COMPANY",
        )

        self.assertEqual(len(result["pages"]), 1)

        page = result["pages"][0]
        self.assertTrue(page["text"].strip())
        self.assertEqual(page["pdf_page"], 1)
        self.assertEqual(page["tables"], [])
        self.assertTrue(
            any(
                "Table structure" in warning
                for warning in page["warnings"]
            )
        )

    def test_text_with_replacement_character_is_partial(self):
        pdf_path = FIXTURES_DIR / "replacement_character_test.pdf"

        from pypdf import PdfWriter

        writer = PdfWriter()
        writer.add_blank_page(width=595, height=842)

        with pdf_path.open("wb") as pdf_file:
            writer.write(pdf_file)

        class PageWithCorruptedText:
            def extract_text(self):
                return "Company name: Test \ufffd Organization"

        class MockReader:
            is_encrypted = False
            pages = [PageWithCorruptedText()]

        try:
            with patch(
                "pdf_reader.PdfReader",
                return_value=MockReader(),
            ):
                result = read_pdf(
                    pdf_path,
                    document_id="partial-test",
                    role="COMPANY",
                )

            page = result["pages"][0]
            self.assertEqual(page["readability"], "PARTIAL")
            self.assertEqual(
                page["extraction_method"],
                "NATIVE_TEXT",
            )
            self.assertTrue(
                any(
                    "replacement characters" in warning
                    for warning in page["warnings"]
                )
            )
        finally:
            pdf_path.unlink(missing_ok=True)

    def test_pdf_with_multiple_pages_preserves_order_and_text(self):
        from pypdf import PdfWriter

        pdf_path = FIXTURES_DIR / "multiple_pages_test.pdf"
        writer = PdfWriter()

        for _ in range(5):
            writer.add_blank_page(width=595, height=842)

        with pdf_path.open("wb") as pdf_file:
            writer.write(pdf_file)

        class MockPage:
            def __init__(self, text):
                self.text = text

            def extract_text(self):
                return self.text

        class MockReader:
            is_encrypted = False
            pages = [
                MockPage("Unique text for page 1"),
                MockPage("Unique text for page 2"),
                MockPage("Unique text for page 3"),
                MockPage("Unique text for page 4"),
                MockPage("Unique text for page 5"),
            ]

        try:
            with patch(
                "pdf_reader.PdfReader",
                return_value=MockReader(),
            ):
                result = read_pdf(
                    pdf_path,
                    document_id="multiple-pages-test",
                    role="COMPANY",
                )

            self.assertEqual(len(result["pages"]), 5)

            for number, page in enumerate(result["pages"], start=1):
                with self.subTest(page=number):
                    self.assertEqual(page["pdf_page"], number)
                    self.assertEqual(
                        page["text"],
                        f"Unique text for page {number}",
                    )
        finally:
            pdf_path.unlink(missing_ok=True)

    def test_real_image_only_pdf_is_unreadable_without_ocr(self):
        from PIL import Image, ImageDraw
        from pypdf import PdfReader

        image_path = FIXTURES_DIR / "scanned_test.png"
        pdf_path = FIXTURES_DIR / "real_image_only_test.pdf"

        # Create a raster image containing text, but no embedded PDF text.
        image = Image.new("RGB", (600, 800), "white")
        draw = ImageDraw.Draw(image)
        draw.text((40, 50), "Scanned document test", fill="black")
        image.save(image_path, format="PNG")

        try:
            # Pillow creates an image-only PDF: the text is pixels, not text.
            image.save(pdf_path, format="PDF", resolution=100)

            # Confirm that the PDF has a page and contains no extractable text.
            reader = PdfReader(pdf_path)
            self.assertEqual(len(reader.pages), 1)
            self.assertFalse(reader.pages[0].extract_text().strip())

            result = read_pdf(
                pdf_path,
                document_id="real-image-only-test",
                role="COMPANY",
            )

            page = result["pages"][0]
            self.assertEqual(page["pdf_page"], 1)
            self.assertEqual(page["text"], "")
            self.assertEqual(page["readability"], "UNREADABLE")
            self.assertEqual(page["extraction_method"], "NONE")
            self.assertTrue(
                any(
                    "OCR is not implemented" in warning
                    for warning in page["warnings"]
                )
            )
        finally:
            image_path.unlink(missing_ok=True)
            pdf_path.unlink(missing_ok=True)

    def test_scanned_image_pdf_is_unreadable_without_ocr(self):
        pdf_path = FIXTURES_DIR / "scanned_test.pdf"

        result = read_pdf(
            pdf_path,
            document_id="scanned-test",
            role="COMPANY",
        )

        self.assertEqual(len(result["pages"]), 1)

        page = result["pages"][0]
        self.assertEqual(page["pdf_page"], 1)
        self.assertEqual(page["text"], "")
        self.assertEqual(page["readability"], "UNREADABLE")
        self.assertEqual(page["extraction_method"], "NONE")
        self.assertTrue(
            any(
                "OCR is not implemented" in warning
                for warning in page["warnings"]
            )
        )


if __name__ == "__main__":
    unittest.main()
