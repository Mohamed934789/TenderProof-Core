"""Member 2: eligibility extraction exercise. Write your own prompt."""
from llm_client import LLMClient
from models import DocumentPages, EligibilityOutput, Mode

async def extract_eligibility(
    tender: DocumentPages, *, client: LLMClient, mode: Mode = "MOCK"
) -> EligibilityOutput:
    """Extract qualification documents/criteria with original tender citations.
    Cover eligibility-related administrative/financial requirements, not every cost.
    Client injection is not permission for paid calls. No mock implementation yet.
    """
    raise NotImplementedError("Member 2: eligibility extraction and prompt")
