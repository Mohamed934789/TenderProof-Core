"""Member 4: company evidence exercise. No matching rules/provider calls yet."""
from llm_client import LLMClient
from models import DocumentPages, EligibilityOutput, Mode, TechnicalOutput, VerificationOutput

async def verify_company(
    eligibility: EligibilityOutput, technical: TechnicalOutput,
    company_documents: list[DocumentPages], *,
    reference_date: str, client: LLMClient, mode: Mode = "MOCK",
) -> VerificationOutput:
    """One finding for each eligibility/technical/BOQ target, with real evidence.
    Unknown completeness/reading does not establish missing evidence or ineligibility.
    Supported dates/numbers must be checked in Python, not trusted from LLM arithmetic.
    """
    raise NotImplementedError("Member 4: evidence verification and prompt")
