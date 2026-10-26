"""Member 4: company evidence verification."""
from datetime import date
from decimal import Decimal, InvalidOperation

from llm_client import LLMClient
from models import (
    DocumentPages, EligibilityOutput, Mode,
    TechnicalOutput, VerificationOutput,
)

PROMPT_VERSION = "agent3-v0.2"

INSTRUCTIONS = (
    "For each target, search ONLY the given company documents. "
    "Return document_id, pdf_page and an exact quote copied from the page. "
    "If there is no evidence, set evidence_found to false. Never guess. "
    "If the evidence has an expiry date, return it as YYYY-MM-DD. "
    "If the evidence states an offered quantity, return offered_quantity "
    "as a number string and offered_unit exactly as written."
)

OUTPUT_SCHEMA = {"results": [{
    "target_id": "str", "evidence_found": "bool", "document_id": "str",
    "pdf_page": "int", "quote": "str", "expiry_date": "str | null",
    "offered_quantity": "str | null", "offered_unit": "str | null",
}]}


def _norm(s: str) -> str:
    return " ".join(s.split())


def _collect_targets(eligibility, technical):
    targets = []
    for r in eligibility["requirements"]:
        targets.append(("ELIGIBILITY", r["requirement_id"], r["text"], None))
    for t in technical["technical_requirements"]:
        targets.append(("TECHNICAL", t["technical_id"], t["text"], None))
    for b in technical["boq_items"]:
        extra = {
            "qty": b["quantity"].get("decimal_value"),
            "unit": b.get("unit_normalized") or b.get("unit"),
        }
        targets.append(("BOQ", b["boq_item_id"], b["description"], extra))
    return targets


def _quote_is_real(docs, document_id, pdf_page, quote) -> bool:
    for d in docs:
        if d["document_id"] != document_id:
            continue
        for p in d["pages"]:
            if p["pdf_page"] == pdf_page:
                return bool(quote) and _norm(quote) in _norm(p["text"])
    return False


def _no_evidence_status(docs):
    sure = bool(docs) and all(
        d["completeness"] == "COMPLETE"
        and all(p["readability"] == "READABLE" for p in d["pages"])
        for d in docs
    )
    return "MISSING_EVIDENCE" if sure else "NEEDS_REVIEW"


def _finding(target_type, target_id, status, explanation,
             evidence=None, reasons=None):
    return {
        "target_type": target_type, "target_id": target_id,
        "status": status, "explanation": explanation,
        "evidence": evidence or [],
        "review_required": status == "NEEDS_REVIEW",
        "uncertainty_reasons": reasons or [],
    }


def _check_quantity(tt, tid, r, extra, citation):
    try:
        required = Decimal(extra["qty"])
        offered = Decimal(r.get("offered_quantity"))
    except (InvalidOperation, TypeError):
        return _finding(tt, tid, "NEEDS_REVIEW",
                        "Required or offered quantity is missing or unclear.",
                        [citation], ["quantity unclear"])
    req_unit, off_unit = extra["unit"], r.get("offered_unit")
    if req_unit and off_unit and _norm(req_unit) != _norm(off_unit):
        return _finding(tt, tid, "NEEDS_REVIEW",
                        "Units differ; no conversion attempted.",
                        [citation], ["unit mismatch"])
    if offered < required:
        return _finding(tt, tid, "CONTRADICTED",
                        f"Offered {offered} is less than required {required}.",
                        [citation])
    return _finding(tt, tid, "SATISFIED",
                    f"Offered {offered} covers required {required}.",
                    [citation])


def _decide(target_type, target_id, r, docs, ref, extra):
    if r is None or not r.get("evidence_found"):
        status = _no_evidence_status(docs)
        msg = "No supporting evidence found in company documents."
        return _finding(target_type, target_id, status, msg,
                        reasons=[msg] if status == "NEEDS_REVIEW" else [])
    if not _quote_is_real(docs, r.get("document_id"),
                          r.get("pdf_page"), r.get("quote")):
        return _finding(target_type, target_id, "NEEDS_REVIEW",
                        "Quoted evidence could not be verified.",
                        reasons=["quote not found on cited page"])
    citation = {"document_id": r["document_id"],
                "pdf_page": r["pdf_page"], "quote": r["quote"]}
    expiry = r.get("expiry_date")
    if expiry:
        try:
            expiry_d = date.fromisoformat(expiry)
        except ValueError:
            return _finding(target_type, target_id, "NEEDS_REVIEW",
                            "Expiry date could not be parsed.", [citation],
                            ["invalid expiry date"])
        if expiry_d < ref:
            return _finding(target_type, target_id, "CONTRADICTED",
                            f"Expired on {expiry}, before {ref.isoformat()}.",
                            [citation])
    if extra is not None:
        return _check_quantity(target_type, target_id, r, extra, citation)
    return _finding(target_type, target_id, "SATISFIED",
                    "Supported by cited evidence.", [citation])


async def verify_company(
    eligibility: EligibilityOutput, technical: TechnicalOutput,
    company_documents: list[DocumentPages], *,
    reference_date: str, client: LLMClient, mode: Mode = "MOCK",
) -> VerificationOutput:
    """One finding for each eligibility/technical/BOQ target, with real evidence.
    Unknown completeness/reading does not establish missing evidence or ineligibility.
    Supported dates/numbers must be checked in Python, not trusted from LLM arithmetic.
    """
    ref = date.fromisoformat(reference_date)
    targets = _collect_targets(eligibility, technical)
    response = await client.generate(
        instructions=INSTRUCTIONS,
        input_data={
            "reference_date": reference_date,
            "targets": [{"target_id": i, "text": t} for _, i, t, _ in targets],
            "documents": company_documents,
        },
        output_schema=OUTPUT_SCHEMA,
    )
    results = {r["target_id"]: r
               for r in response["payload"].get("results", [])}
    findings = [
        _decide(tt, tid, results.get(tid), company_documents, ref, extra)
        for tt, tid, _, extra in targets
    ]
    return {
        "findings": findings,
        "provenance": {"mode": mode, "provider": response["provider"],
                       "model": response["model"],
                       "prompt_version": PROMPT_VERSION},
        "warnings": [],
    }