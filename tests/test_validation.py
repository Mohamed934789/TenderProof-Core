import unittest
from validation import validate_document, validate_citation,validate_extractions,validate_verification


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