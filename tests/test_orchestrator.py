
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch, ANY

from orchestrator import analyze


def fake_read_pdf(path, *, document_id, role):
    text = (
        ""
        if path.name == "tax_card.pdf"
        else "يجب تقديم سجل تجاري ساري المفعول."
    )

    return {
        "document_id": document_id,
        "filename": path.name,
        "role": role,
        "completeness": "UNKNOWN",
        "completeness_basis": "UNKNOWN",
        "pages": [
            {
                "pdf_page": 1,
                "text": text,
                "readability": "PARTIAL" if text else "UNREADABLE",
                "extraction_method": "NATIVE_TEXT" if text else "NONE",
                "tables": [],
                "warnings": [],
            }
        ],
        "warnings": [],
    }


class TestOrchestrator(unittest.IsolatedAsyncioTestCase):

    async def test_invalid_company_document_stops_pipeline(self):
        with (
            patch(
                "orchestrator.read_pdf",
                side_effect=fake_read_pdf,
            ),
            patch(
                "orchestrator.extract_eligibility",
                new_callable=AsyncMock,
            ) as agent1,
            patch(
                "orchestrator.extract_technical",
                new_callable=AsyncMock,
            ) as agent2,
            patch(
                "orchestrator.verify_company",
                new_callable=AsyncMock,
            ) as agent3,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "Document has no extractable text",
            ):
                await analyze(
                    tender_path=Path("ida-335.pdf"),
                    company_paths=[
                        Path("commercial_register.pdf"),
                        Path("tax_card.pdf"),
                    ],
                    reference_date="2026-10-24",
                    eligibility_client=None,
                    technical_client=None,
                    verification_client=None,
                    mode="MOCK",
                )

            # No agent should run after document validation fails.
            agent1.assert_not_awaited()
            agent2.assert_not_awaited()
            agent3.assert_not_awaited()

    async def test_agents_are_called(self):
        provenance = {
            "mode": "MOCK",
            "provider": "mock",
            "model": "none",
            "prompt_version": "test-1",
        }

        eligibility_output = {
            "requirements": [],
            "provenance": provenance.copy(),
            "warnings": [],
        }

        technical_output = {
            "boq_status": "NEEDS_REVIEW",
            "boq_review_reasons": ["Tender completeness is unknown."],
            "boq_items": [],
            "technical_requirements": [],
            "provenance": provenance.copy(),
            "warnings": [],
        }

        verification_output = {
            "findings": [],
            "provenance": provenance.copy(),
            "warnings": [],
        }

        def valid_fake_pdf(path, *, document_id, role):
            return {
                "document_id": document_id,
                "filename": path.name,
                "role": role,
                "completeness": "UNKNOWN",
                "completeness_basis": "UNKNOWN",
                "pages": [
                    {
                        "pdf_page": 1,
                        "text": "كراسة شروط تجريبية.",
                        "readability": "PARTIAL",
                        "extraction_method": "NATIVE_TEXT",
                        "tables": [],
                        "warnings": [],
                    }
                ],
                "warnings": [],
            }

        with (
            patch(
                "orchestrator.read_pdf",
                side_effect=valid_fake_pdf,
            ) as pdf_reader,
            patch(
                "orchestrator.extract_eligibility",
                new_callable=AsyncMock,
                return_value=eligibility_output,
            ) as agent1,
            patch(
                "orchestrator.extract_technical",
                new_callable=AsyncMock,
                return_value=technical_output,
            ) as agent2,
            patch(
                "orchestrator.validate_extractions",
            ) as extraction_validator,
            patch(
                "orchestrator.verify_company",
                new_callable=AsyncMock,
                return_value=verification_output,
            ) as agent3,
            patch(
                "orchestrator.validate_verification",
            ) as verification_validator,
        ):
            report = await analyze(
                tender_path=Path("fake_tender.pdf"),
                company_paths=[],
                reference_date="2026-10-24",
                eligibility_client=None,
                technical_client=None,
                verification_client=None,
                mode="MOCK",
            )

            # Check the PDF Reader.
            pdf_reader.assert_called_once_with(
                Path("fake_tender.pdf"),
                document_id="tender-001",
                role="TENDER",
            )

            # Check Agent 1 and Agent 2.
            agent1.assert_awaited_once()
            agent2.assert_awaited_once()

            extraction_validator.assert_called_once_with(
                eligibility_output,
                technical_output,
                ANY,
            )

            # Check Agent 3.
            agent3.assert_awaited_once_with(
                eligibility_output,
                technical_output,
                [],
                reference_date="2026-10-24",
                client=None,
                mode="MOCK",
                synthetic_test=False,
                tender_context=ANY,
            )

            # Check verification validation.
            verification_validator.assert_called_once_with(
                verification_output,
                eligibility_output,
                technical_output,
                [],
                reference_date="2026-10-24",
            )

            # Check the final report structure.
            self.assertEqual(
                report["schema_version"],
                "core-draft-0.2",
            )

            self.assertEqual(report["mode"], "MOCK")
            self.assertEqual(
                report["reference_date"],
                "2026-10-24",
            )

            self.assertEqual(
                report["eligibility"],
                eligibility_output,
            )

            self.assertEqual(
                report["technical"],
                technical_output,
            )

            self.assertEqual(
                report["findings"],
                verification_output["findings"],
            )

            self.assertEqual(
                report["verification_provenance"],
                verification_output["provenance"],
            )

            self.assertEqual(len(report["documents"]), 1)
            self.assertEqual(
                report["documents"][0]["document_id"],
                "tender-001",
            )
            self.assertEqual(
                report["documents"][0]["role"],
                "TENDER",
            )

            self.assertFalse(report["coverage_confirmed"])
            self.assertTrue(report["warnings"])

    async def test_full_pipeline_preserves_uncertain_evidence(self):
        tender_text = "يشترط تقديم سجل تجاري ساري المفعول."
        company_text = "السجل التجاري للشركة ساري المفعول."

        def mock_pdf(path, *, document_id, role):
            text = tender_text if role == "TENDER" else company_text

            return {
                "document_id": document_id,
                "filename": path.name,
                "role": role,
                "completeness": "UNKNOWN",
                "completeness_basis": "UNKNOWN",
                "pages": [{
                    "pdf_page": 1,
                    "text": text,
                    "readability": "PARTIAL",
                    "extraction_method": "NATIVE_TEXT",
                    "tables": [],
                    "warnings": [],
                }],
                "warnings": [],
            }

        provenance = {
            "mode": "MOCK",
            "provider": "mock",
            "model": "none",
            "prompt_version": "test-1",
        }

        eligibility = {
            "requirements": [{
                "requirement_id": "REQ-001",
                "text": "تقديم سجل تجاري ساري المفعول",
                "category": "REGISTRATION",
                "needs_review": True,
                "review_reasons": ["Tender reading is partial."],
                "sources": [{
                    "document_id": "tender-001",
                    "pdf_page": 1,
                    "quote": "يشترط تقديم سجل تجاري ساري المفعول.",
                }],
            }],
            "provenance": provenance.copy(),
            "warnings": [],
        }

        technical = {
            "boq_status": "NEEDS_REVIEW",
            "boq_review_reasons": ["Tender completeness is unknown."],
            "boq_items": [],
            "technical_requirements": [],
            "provenance": provenance.copy(),
            "warnings": [],
        }

        verification = {
            "findings": [{
                "target_type": "ELIGIBILITY",
                "target_id": "REQ-001",
                "status": "NEEDS_REVIEW",
                "explanation": "المستند المرفوع يشير إلى سريان السجل.",
                "evidence": [{
                    "document_id": "company-001",
                    "pdf_page": 1,
                    "quote": company_text,
                }],
                "review_required": True,
                "uncertainty_reasons": ["Source reading is partial."],
            }],
            "provenance": provenance.copy(),
            "warnings": [],
        }

        with (
            patch("orchestrator.read_pdf", side_effect=mock_pdf),
            patch(
                "orchestrator.extract_eligibility",
                new_callable=AsyncMock,
                return_value=eligibility,
            ),
            patch(
                "orchestrator.extract_technical",
                new_callable=AsyncMock,
                return_value=technical,
            ),
            patch(
                "orchestrator.verify_company",
                new_callable=AsyncMock,
                return_value=verification,
            ),
        ):
            report = await analyze(
                tender_path=Path("mock_tender.pdf"),
                company_paths=[Path("mock_company.pdf")],
                reference_date="2026-10-24",
                eligibility_client=None,
                technical_client=None,
                verification_client=None,
                mode="MOCK",
            )

        self.assertEqual(len(report["eligibility"]["requirements"]), 1)
        self.assertEqual(report["findings"][0]["target_id"], "REQ-001")
        self.assertEqual(report["findings"][0]["status"], "NEEDS_REVIEW")
        self.assertEqual(
            report["findings"][0]["evidence"][0]["document_id"],
            "company-001",
        )
        self.assertEqual(len(report["documents"]), 2)
        self.assertFalse(report["coverage_confirmed"])


if __name__ == "__main__":
    unittest.main()
