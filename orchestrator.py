"""Member 5: fixed-order pipeline exercise, disconnected from old backend."""
from pathlib import Path
from models import Report

def analyze(
    tender_path: Path, company_paths: list[Path],
    *, reference_date: str, mode: str = "MOCK",
) -> Report:
    """Read -> extract -> verify -> validate. Never publish partial success."""
    raise NotImplementedError("Member 5: integrate student implementations")
