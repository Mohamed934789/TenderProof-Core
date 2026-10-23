"""Member 3: BOQ/technical extraction; verification now belongs to agent3."""
from llm_client import LLMClient
from models import DocumentPages, Mode, TechnicalOutput

async def extract_technical(
    tender: DocumentPages, *, client: LLMClient, mode: Mode = "MOCK"
) -> TechnicalOutput:
    """Extract BOQ, specs/models and technical deadlines with sources.
    Distinguish NOT_FOUND from unreadable/uncertain tables. Never invent quantities.
    Technical requirements can exist without a BOQ.
    """
    raise NotImplementedError("Member 3: BOQ/technical extraction and prompt")
