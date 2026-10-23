"""Member 5: fixed-order integration exercise; no backend or execution yet."""
from pathlib import Path
from llm_client import LLMClient
from models import Mode, Report

async def analyze(
    tender_path: Path, company_paths: list[Path], *,
    reference_date: str,
    eligibility_client: LLMClient,
    technical_client: LLMClient,
    verification_client: LLMClient,
    mode: Mode = "MOCK",
) -> Report:
    """Read documents -> A1 + A2 -> validate_extractions -> A3 -> validate -> report.
    A1/A2 may run concurrently; A3 must await BOTH valid outputs.
    Valid NOT_FOUND is not an Agent 2 failure. Failed stages must not publish success.
    Completeness stays UNKNOWN unless explicitly established by a documented input.
    """
    raise NotImplementedError("Member 5: integrate student implementations")
