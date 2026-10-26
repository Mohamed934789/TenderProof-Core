import unittest
from decimal import Decimal

import pytest

from validation import (
    quantity_value, validate_document, validate_citation, validate_extractions, validate_verification,
)


@pytest.mark.parametrize("raw,expected", [
    ("2", "2"), ("٢", "2"), ("۲", "2"), ("12", "12"), ("١٢", "12"), ("۱۲", "12"),
    ("اثنان", "2"), ("جهازان", "2"), ("جهازي Plotter", "2"),
    ("١٢ جهاز Xerox", "12"), ("صيانة ١٢ جهاز Xerox", "12"),
    ("ثمانية أجهزة Canon", "8"), ("اثنا عشر جهاز Xerox", "12"),
    ("2.5", "2.5"), ("٢٫٥", "2.5"),
])
def test_explicit_quantity_keeps_exact_source(raw, expected):
    source = {"document_id": "tender-001", "pdf_page": 3, "quote": f"الكمية: {raw}؛"}
    original = dict(source)
    assert quantity_value(raw, [source]) == Decimal(expected)
    assert source == original


@pytest.mark.parametrize("raw,quote", [
    ("2", "12"), ("٢", "١٢"), ("۲", "۱۲"), ("12", "120"), ("١٢", "١٢٠"),
    ("2", "2.5"), ("٢", "٢٫٥"), ("2", "-2"), ("2", "2,000"),
    ("2", "B2"), ("2", "B7030-2"), ("اثنان", "اثنانجهاز"),
])
def test_quantity_cannot_match_part_of_number_or_word(raw, quote):
    with pytest.raises(ValueError, match="not supported"):
        quantity_value(raw, [{"quote": quote}])


@pytest.mark.parametrize("raw,quote", [
    ("عدد غير محدد", "الكمية: عدد غير محدد"),
    ("جهازان أو ثلاثة", "الكمية: جهازان أو ثلاثة"),
    ("جهازان", "الكمية: حوالي جهازان"),
    ("جهازي", "هذا جهازي الشخصي"),
    ("جهازي Plotter", "هذا جهازي Plotter"),
    ("جهازي Plotter", "أصلح جهازي Plotter"),
    ("اثنان", "اثنان وعشرون جهازًا"),
    ("اثنان", "اثنان وأربعون جهازًا"),
    ("عشر", "اثنا عشر جهازًا"),
    ("اثنان وعشرون", "الكمية: اثنان وعشرون جهازًا"),
    ("2,000", "الكمية: 2,000"),
])
def test_ambiguous_or_unsupported_quantity_is_not_inferred(raw, quote):
    assert quantity_value(raw, [{"quote": quote}]) is None


def test_quantity_cannot_be_taken_from_another_product_in_the_same_line():
    with pytest.raises(ValueError, match="described product"):
        quantity_value("١٢", [{"quote": "صيانة ١٢ جهاز Xerox و٨ أجهزة Canon"}], "صيانة أجهزة Canon")


def test_price_before_a_product_quantity_is_not_a_linked_quantity():
    source = {"quote": "السعر ١٢٠ جنيه؛ صيانة ١٢ جهاز Xerox"}
    assert quantity_value("١٢٠", [source], "صيانة أجهزة Xerox") is None


class TestValidation(unittest.TestCase):

    def test_document_without_pages(self):
        document = {"pages": []}

        with self.assertRaises(ValueError):
            validate_document(document)

    def test_citation_with_wrong_quote(self):
        documents = [
            {
                "document_id": "tender-001",
                "pages": [
                    {
                        "pdf_page": 1,
                        "text": "يجب تقديم سجل تجاري ساري.",
                    }
                ],
            }
        ]

        citation = {
            "document_id": "tender-001",
            "pdf_page": 1,
            "quote": "شهادة ISO 9001",
        }

        with self.assertRaises(ValueError):
            validate_citation(citation, documents)

    def test_boq_not_found_cannot_have_items(self):
        eligibility = {
            "requirements": [],
        }

        technical = {
            "technical_requirements": [],
            "boq_status": "NOT_FOUND",
            "boq_items": [
                {"boq_item_id": "BOQ-001"}
            ],
        }

        with self.assertRaisesRegex(
            ValueError,
            "BOQ cannot contain items",
        ):
            validate_extractions(
                eligibility,
                technical,
                tender={},
            )

    def test_missing_finding_is_rejected(self):
        eligibility = {
            "requirements": [
                {"requirement_id": "REQ-001"}
            ]
        }

        technical = {
            "technical_requirements": [],
            "boq_items": [],
        }

        verification = {
            "findings": [],
        }

        with self.assertRaisesRegex(
            ValueError,
            "Findings do not match",
        ):
            validate_verification(
                verification,
                eligibility,
                technical,
                company_documents=[],
                reference_date="2026-10-24",
            )


    def test_missing_evidence_without_completeness(self):
        eligibility = {
            "requirements": [
                {"requirement_id": "REQ-001"}
            ]
        }

        technical = {
            "technical_requirements": [],
            "boq_items": [],
        }

        verification = {
            "findings": [
                {
                    "target_type": "ELIGIBILITY",
                    "target_id": "REQ-001",
                    "status": "MISSING_EVIDENCE",
                    "evidence": [],
                }
            ]
        }

        with self.assertRaisesRegex(
            ValueError,
            "requires confirmed document completeness",
        ):
            validate_verification(
                verification,
                eligibility,
                technical,
                company_documents=[],
                reference_date="2026-10-24",
            )



if __name__ == "__main__":
    unittest.main()
