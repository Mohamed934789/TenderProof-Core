
import copy
import unittest

from agent2 import extract_technical


class FakeLLMClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = 0

    async def generate(
        self, *, instructions, input_data, output_schema
    ):
        self.calls += 1

        return {
            "payload": copy.deepcopy(self.payload),
            "provider": "fake",
            "model": "fake-model",
            "usage": None,
        }


ORIGINAL_LINE = "104  Xerox Versa Link B7030 1 "


def make_tender():
    return {
        "document_id": "tender-001",
        "filename": "sample.pdf",
        "role": "TENDER",
        "completeness": "COMPLETE",
        "completeness_basis": "TEST_FIXTURE",
        "pages": [
            {
                "pdf_page": 6,
                "text": ORIGINAL_LINE + "\n",
                "readability": "READABLE",
                "extraction_method": "NATIVE_TEXT",
                "tables": [],
                "warnings": [],
            }
        ],
        "warnings": [],
    }


def make_payload():
    ref = {"line_id": "P006-L0001"}

    return {
        "boq_status": "FOUND",
        "boq_review_reasons": [],
        "boq_items": [
            {
                "boq_item_id": "BOQ-001",
                "description": "Xerox Versa Link B7030",
                "quantity": {
                    "raw_text": "104",
                    "decimal_value": "104",
                    "sources": [ref],
                },
                "unit": "جهاز",
                "unit_normalized": "piece",
                "table_id": None,
                "needs_review": False,
                "review_reasons": [],
                "sources": [ref],
            }
        ],
        "technical_requirements": [],
    }


class TestAgent2(unittest.IsolatedAsyncioTestCase):

    async def test_mock_does_not_call_llm(self):
        client = FakeLLMClient(make_payload())

        result = await extract_technical(
            make_tender(),
            client=client,
            mode="MOCK",
        )

        self.assertEqual(client.calls, 0)
        self.assertEqual(result["boq_status"], "NEEDS_REVIEW")

    async def test_ai_resolves_line_reference(self):
        client = FakeLLMClient(make_payload())

        result = await extract_technical(
            make_tender(),
            client=client,
            mode="AI",
        )

        source = result["boq_items"][0]["sources"][0]

        self.assertEqual(client.calls, 1)
        self.assertEqual(source["document_id"], "tender-001")
        self.assertEqual(source["pdf_page"], 6)
        self.assertEqual(source["quote"], ORIGINAL_LINE)
        self.assertEqual(result["boq_status"], "FOUND")

    async def test_invalid_line_reference_is_rejected(self):
        payload = make_payload()

        payload["boq_items"][0]["sources"] = [
            {"line_id": "P006-L9999"}
        ]

        with self.assertRaises(ValueError):
            await extract_technical(
                make_tender(),
                client=FakeLLMClient(payload),
                mode="AI",
            )

    async def test_missing_quantity_requires_review(self):
        payload = make_payload()
        item = payload["boq_items"][0]

        item["quantity"]["decimal_value"] = None
        item["needs_review"] = False

        with self.assertRaises(ValueError):
            await extract_technical(
                make_tender(),
                client=FakeLLMClient(payload),
                mode="AI",
            )

    async def test_partial_page_requires_review(self):
        tender = make_tender()
        tender["pages"][0]["readability"] = "PARTIAL"

        result = await extract_technical(
            tender,
            client=FakeLLMClient(make_payload()),
            mode="AI",
        )

        self.assertEqual(result["boq_status"], "NEEDS_REVIEW")
        self.assertTrue(result["boq_items"][0]["needs_review"])
        self.assertTrue(result["warnings"])

    async def test_incomplete_tender_requires_review(self):
        tender = make_tender()
        tender["completeness"] = "INCOMPLETE"

        result = await extract_technical(
            tender,
            client=FakeLLMClient(make_payload()),
            mode="AI",
        )

        self.assertEqual(result["boq_status"], "NEEDS_REVIEW")

    async def test_company_document_is_rejected(self):
        tender = make_tender()
        tender["role"] = "COMPANY"

        client = FakeLLMClient(make_payload())

        with self.assertRaises(ValueError):
            await extract_technical(
                tender,
                client=client,
                mode="AI",
            )

        self.assertEqual(client.calls, 0)

    async def test_duplicate_boq_id_is_rejected(self):
        payload = make_payload()
        payload["boq_items"].append(
            copy.deepcopy(payload["boq_items"][0])
        )

        with self.assertRaises(ValueError):
            await extract_technical(
                make_tender(),
                client=FakeLLMClient(payload),
                mode="AI",
            )

    async def test_negative_quantity_is_rejected(self):
        payload = make_payload()
        payload["boq_items"][0]["quantity"]["decimal_value"] = "-104"

        with self.assertRaises(ValueError):
            await extract_technical(
                make_tender(),
                client=FakeLLMClient(payload),
                mode="AI",
            )


    async def test_normalized_quantity_must_match_quoted_raw_quantity(self):
        payload = make_payload()
        payload["boq_items"][0]["quantity"]["decimal_value"] = "999"
        with self.assertRaisesRegex(ValueError, "not supported"):
            await extract_technical(make_tender(), client=FakeLLMClient(payload), mode="AI")

    async def test_raw_quantity_must_exist_in_its_source(self):
        payload = make_payload()
        payload["boq_items"][0]["quantity"].update(raw_text="999", decimal_value="999")
        with self.assertRaisesRegex(ValueError, "not supported"):
            await extract_technical(make_tender(), client=FakeLLMClient(payload), mode="AI")

    async def test_malformed_review_flag_is_rejected_before_uncertainty_handling(self):
        tender = make_tender()
        tender["pages"][0]["readability"] = "PARTIAL"
        payload = make_payload()
        payload["boq_items"][0]["needs_review"] = "false"
        with self.assertRaises(ValueError):
            await extract_technical(tender, client=FakeLLMClient(payload), mode="AI")

if __name__ == "__main__":
    unittest.main()
