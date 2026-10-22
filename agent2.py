"""Member 3: evidence exercise. No provider calls or finished rules."""
from models import DocumentPages, Requirement, Finding

def verify_requirements(
    requirements: list[Requirement], company_documents: list[DocumentPages],
    *, reference_date: str, mode: str = "MOCK",
) -> list[Finding]:
    """One finding per requirement. Uncertain material requires review."""
    raise NotImplementedError("Member 3: verification exercise")
