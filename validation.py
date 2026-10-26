"""Shared Python checks for contracts, exact citations and conservative findings."""
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from types import UnionType
from typing import Literal, get_args, get_origin, get_type_hints, is_typeddict

from models import (
    Citation, DocumentPages, EligibilityOutput, Report, TechnicalOutput,
    VerificationOutput,
)


def build_line_index(tender: DocumentPages, *, prefix=""):
    """Return model input lines and exact source lookup."""

    indexed_pages = []
    line_lookup = {}

    for page in tender["pages"]:
        page_number = page["pdf_page"]
        indexed_lines = []

        for number, raw_line in enumerate(
            page["text"].splitlines(),
            start=1,
        ):
            if not raw_line.strip():
                continue

            line_id = f"{prefix}P{page_number:03d}-L{number:04d}"

            if line_id in line_lookup:
                raise ValueError(
                    f"Duplicate line reference: {line_id}"
                )

            citation = {
                "document_id": tender["document_id"],
                "pdf_page": page_number,
                "quote": raw_line,
            }

            line_lookup[line_id] = citation

            indexed_lines.append({
                "line_id": line_id,
                "text": raw_line,
                "needs_review": page_text_uncertain(page, raw_line),
            })

        indexed_pages.append({
            "pdf_page": page_number,
            "readability": page["readability"],
            "warnings": page["warnings"],
            "tables": page["tables"],
            "lines": indexed_lines,
        })

    return indexed_pages, line_lookup


def resolve_sources(
    references,
    line_lookup,
):
    """Convert model-selected line IDs into exact Citations."""

    if not isinstance(references, list) or not references:
        raise ValueError("Missing source line references.")

    citations = []
    seen = set()

    for reference in references:
        if not isinstance(reference, dict):
            raise ValueError("Invalid line reference object.")

        if set(reference) != {"line_id"}:
            raise ValueError("Unexpected line reference fields.")

        line_id = reference["line_id"]

        if not isinstance(line_id, str):
            raise ValueError("Line ID must be a string.")

        if line_id not in line_lookup:
            raise ValueError(
                f"Unknown source line: {line_id}"
            )

        if line_id in seen:
            continue

        seen.add(line_id)

        # Never ask the LLM to recreate the quote.
        citations.append(dict(line_lookup[line_id]))

    return citations


def validate_shape(value, contract, path="output"):
    """Enforce the existing TypedDict contracts, including required null fields."""
    origin, args = get_origin(contract), get_args(contract)
    if is_typeddict(contract):
        fields = get_type_hints(contract)
        if not isinstance(value, dict) or set(value) != set(fields):
            raise ValueError(f"{path}: missing or unexpected fields.")
        for key, field in fields.items():
            validate_shape(value[key], field, f"{path}.{key}")
    elif origin is list:
        if not isinstance(value, list):
            raise ValueError(f"{path}: expected a list.")
        for index, item in enumerate(value):
            validate_shape(item, args[0], f"{path}[{index}]")
    elif origin is Literal:
        if not any(type(value) is type(option) and value == option for option in args):
            raise ValueError(f"{path}: invalid choice.")
    elif origin is UnionType:
        for option in args:
            try:
                validate_shape(value, option, path)
                return
            except ValueError:
                pass
        raise ValueError(f"{path}: invalid nullable value.")
    elif type(value) is not contract:
        raise ValueError(f"{path}: expected {contract.__name__}.")


def advisory_warning(warning):
    # Only explicitly scoped informational/table notes are non-textual.
    return (warning.startswith(("INFO:", "TABLE:"))
            or warning == "Table structure and visual reading order were not verified.")


def page_text_uncertain(page, quote=None):
    if page["readability"] == "UNREADABLE":
        return True
    affected_lines = set()
    for warning in page["warnings"]:
        if advisory_warning(warning):
            continue
        match = re.match(r"TEXT_LINE:(\d+):", warning)
        if match:
            affected_lines.add(int(match[1]))
        else:
            return True  # Unknown/material warnings remain conservative.
    if affected_lines:
        if quote is None:
            return True
        lines = page["text"].splitlines(keepends=True)
        if any(number < 1 or number > len(lines) for number in affected_lines):
            return True
        offset, affected_spans = 0, []
        for number, line in enumerate(lines, 1):
            if number in affected_lines:
                affected_spans.append((offset, offset + len(line)))
            offset += len(line)
        occurrences = list(re.finditer(re.escape(quote), page["text"]))
        return not occurrences or any(match.start() < end and start < match.end()
                                      for match in occurrences for start, end in affected_spans)
    return page["readability"] != "READABLE"


def table_uncertain(page):
    return (any(w.startswith("TABLE:") or w == "Table structure and visual reading order were not verified."
                for w in page["warnings"])
            or any(t["structure_quality"] != "RECOVERED" or t["warnings"] for t in page["tables"]))


def documents_complete(documents):
    """Absence needs a confirmed complete set and fully searchable text."""
    return bool(documents) and all(
        doc["completeness"] == "COMPLETE"
        and doc["completeness_basis"] in {"USER_CONFIRMED", "TEST_FIXTURE"}
        and doc["pages"] and all(advisory_warning(w) for w in doc["warnings"])
        and all(not page_text_uncertain(page)
                and all(table["structure_quality"] == "RECOVERED" and not table["warnings"]
                        for table in page["tables"])
                for page in doc["pages"])
        for doc in documents
    )


def validate_document(document: DocumentPages) -> None:
    if not document.get("pages"):
        raise ValueError("Document has no pages.")
    validate_shape(document, DocumentPages)
    if not document["document_id"].strip() or not document["filename"].strip():
        raise ValueError("Document ID and filename must not be empty.")
    if not any(page["text"].strip() for page in document["pages"]):
        raise ValueError("Document has no extractable text.")
    if document["completeness"] == "COMPLETE" and document["completeness_basis"] == "UNKNOWN":
        raise ValueError("Complete documents require a confirmed completeness basis.")
    for number, page in enumerate(document["pages"], 1):
        if page["pdf_page"] != number:
            raise ValueError(f"Invalid page numbering: expected {number}.")
        if page["readability"] == "READABLE" and not page["text"].strip():
            raise ValueError("A readable page must contain text.")
        for table in page["tables"]:
            if table["pdf_page"] != number:
                raise ValueError("Table page does not match its page.")
            for cell in table["cells"]:
                for source in cell["sources"]:
                    validate_citation(source, [document])


def validate_citation(citation: Citation, documents: list[DocumentPages]) -> None:
    validate_shape(citation, Citation, "citation")
    document = next((doc for doc in documents
                     if doc["document_id"] == citation["document_id"]), None)
    if document is None:
        raise ValueError(f"Unknown document ID: {citation['document_id']}")
    page = next((p for p in document["pages"] if p["pdf_page"] == citation["pdf_page"]), None)
    if page is None or citation["pdf_page"] < 1:
        raise ValueError(f"Invalid page number: {citation['pdf_page']}")
    if not citation["quote"].strip() or citation["quote"] not in page["text"]:
        raise ValueError("Citation quote was not found in the referenced page.")


def source_uncertain(citations, documents, *, table=False):
    return any(
        page_text_uncertain(page, citation["quote"]) or table and table_uncertain(page)
        for citation in citations for doc in documents
        if doc["document_id"] == citation["document_id"]
        for page in doc["pages"] if page["pdf_page"] == citation["pdf_page"]
    )


def numbers_in_text(text):
    """Read numeric tokens, including Arabic digits; exclude model identifiers."""
    normalized = text.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩٫", "0123456789."))
    return {Decimal(token.replace(",", "."))
            for token in re.findall(r"(?<![\w.])[+-]?\d+(?:[.,]\d+)?(?![\w.])", normalized)}


def quantity_value(raw, sources):
    """Read one explicit count from an exact, whole-token source span.

    This deliberately recognizes a small count vocabulary, not arbitrary Arabic
    arithmetic. Unsupported or qualified wording needs review, never a guess.
    """
    if not raw.strip():
        raise ValueError("BOQ raw quantity is not supported by its sources.")
    # The optional conjunction permits جهازي in وجهازي Plotter, but never a
    # suffix of another word/number, identifier, decimal or grouped number.
    pattern = (r"(?<![\w.,٫٬+/-])(?:و)?" + re.escape(raw)
               + r"(?![\w٫٬+/-]|[.,]\d)")
    matches = [(source["quote"], match) for source in sources
               for match in re.finditer(pattern, source["quote"])]
    if not matches:
        raise ValueError("BOQ raw quantity is not supported by its sources.")
    ambiguous = r"(?<!\w)(?:أو|او|بين|حوالي|نحو|تقريبًا|تقريبا|عدة|بعض|حسب|غير محدد|غير واضح|هذا جهازي)(?!\w)"
    if any(re.search(ambiguous, quote) for quote, _ in matches):
        return None
    words = {
        "واحد": 1, "واحدة": 1,
        "اثنان": 2, "اثنين": 2, "إثنان": 2, "إثنين": 2,
        "اثنتان": 2, "اثنتين": 2,
        "جهازان": 2, "جهازين": 2, "جهازي": 2,
        "طابعتان": 2, "طابعتين": 2, "وحدتان": 2, "وحدتين": 2,
        "ثلاثة": 3, "ثلاث": 3, "أربعة": 4, "أربع": 4,
        "خمسة": 5, "خمس": 5, "ستة": 6, "ست": 6,
        "سبعة": 7, "سبع": 7, "ثمانية": 8, "ثمان": 8,
        "تسعة": 9, "تسع": 9, "عشرة": 10, "عشر": 10,
        "أحد عشر": 11, "إحدى عشرة": 11,
        "اثنا عشر": 12, "اثني عشر": 12, "اثنتا عشرة": 12, "اثنتي عشرة": 12,
    }
    count = r"[+-]?\d+(?:[.,٫]\d+)?|" + "|".join(words)
    units = r"جهاز(?:ًا|ا)?|أجهزة|طابعة|طابعات|وحدة|وحدات"
    parsed = re.fullmatch(r"(?:و)?(?P<count>" + count + r")"
                          r"(?:\s+(?:" + units + r"))?"
                          r"(?:\s+[A-Za-z][A-Za-z0-9 ./-]*)?", raw.strip())
    if not parsed:
        return None
    token = parsed["count"]
    # Do not read 'اثنان' as 2 when it is part of 'اثنان وعشرون', or
    # 'عشر' as 10 in 'اثنا عشر'. Larger unsupported expressions need review.
    parts = ("|".join(words) + r"|اثنا|اثني|اثنتا|اثنتي"
             r"|(?:عشر|ثلاث|أربع|خمس|ست|سبع|ثمان|تسع)(?:ون|ين)"
             r"|مائة|مئة|مائتان|مائتين|مئتان|مئتين|ألف|ألفان|ألفين|آلاف|مليون|ملايين")
    if token in words and any(
        re.search(r"(?<!\w)(?:" + parts + r")\s+و?$", quote[:match.start()]) or
        re.match(r"\s+و?(?:" + parts + r")(?!\w)", quote[match.end():])
        for quote, match in matches
    ):
        return None
    # جهازي can mean 'my device'. Require a product AND a quantity label or
    # parallel count list, including when the selected span is only this word.
    if token == "جهازي" and not any(
        (re.match(r"\s+[A-Za-z]", quote[match.end():]) or
         re.search(r"جهازي\s+[A-Za-z]", raw)) and
        (re.search(r"(?:الكمية|العدد|عدد)\s*[:：]?\s*$", quote[:match.start()]) or
         match[0].startswith("و") and
         re.search(r"(?:" + count + r")\s+(?:" + units + r")(?!\w)", quote[:match.start()]))
        for quote, match in matches
    ):
        return None
    if re.search(r",\d{3}(?!\d)", token):
        return None  # A comma may be a thousands separator, not a decimal mark.
    return Decimal(words[token]) if token in words else next(iter(numbers_in_text(token)))


def _validate_sources(sources, documents):
    if not sources:
        raise ValueError("Extracted requirement or quantity must have sources.")
    for source in sources:
        validate_citation(source, documents)


def _validate_items(items, id_field, tender):
    ids = [item[id_field] for item in items]
    if any(not ident.strip() for ident in ids) or len(ids) != len(set(ids)):
        raise ValueError(f"Empty or duplicate {id_field}.")
    for item in items:
        text = item.get("text", item.get("description", ""))
        if not text.strip():
            raise ValueError("Extracted text must not be empty.")
        _validate_sources(item["sources"], [tender])
        if item["needs_review"] != bool(item["review_reasons"]):
            raise ValueError("Review flag and review reasons must agree.")
        if source_uncertain(item["sources"], [tender]) and not item["needs_review"]:
            raise ValueError("Uncertain source requires extraction review.")


def validate_eligibility(eligibility, tender):
    validate_shape(eligibility, EligibilityOutput)
    _validate_items(eligibility["requirements"], "requirement_id", tender)


def validate_technical(technical, tender):
    validate_shape(technical, TechnicalOutput)
    _validate_items(technical["technical_requirements"], "technical_id", tender)
    _validate_items(technical["boq_items"], "boq_item_id", tender)
    items, status = technical["boq_items"], technical["boq_status"]
    if status == "NOT_FOUND" and items:
        raise ValueError("BOQ cannot contain items when status is NOT_FOUND.")
    if status == "FOUND" and not items:
        raise ValueError("BOQ status is FOUND but no items were returned.")
    if status == "NEEDS_REVIEW" and not technical["boq_review_reasons"]:
        raise ValueError("BOQ review requires a reason.")
    if status != "NEEDS_REVIEW" and (not documents_complete([tender])
                                    or any(item["needs_review"] for item in items)):
        raise ValueError("Uncertain tender or BOQ requires review.")
    for item in items:
        quantity = item["quantity"]
        _validate_sources(quantity["sources"], [tender])
        raw = quantity["raw_text"]
        supported = quantity_value(raw, quantity["sources"])
        value = quantity["decimal_value"]
        if value is None:
            if not item["needs_review"]:
                raise ValueError("Unknown quantity requires review.")
        else:
            try:
                number = Decimal(value)
            except InvalidOperation:
                raise ValueError("Invalid normalized BOQ quantity.") from None
            if not number.is_finite() or number <= 0 or supported is None or number != supported:
                raise ValueError("Normalized BOQ quantity is not supported by raw_text.")
        if source_uncertain(item["sources"] + quantity["sources"], [tender], table=True) and not item["needs_review"]:
            raise ValueError("Uncertain quantity or table source requires review.")
        if item["table_id"] is not None:
            tables = [t for p in tender["pages"] for t in p["tables"]
                      if t["table_id"] == item["table_id"]]
            if len(tables) != 1 or not any(src["pdf_page"] == tables[0]["pdf_page"]
                                        for src in item["sources"]):
                raise ValueError("Unknown or unrelated BOQ table ID.")


def validate_extractions(eligibility, technical, tender):
    if technical.get("boq_status") == "NOT_FOUND" and technical.get("boq_items"):
        raise ValueError("BOQ cannot contain items when status is NOT_FOUND.")
    validate_eligibility(eligibility, tender)
    validate_technical(technical, tender)


def collect_targets(eligibility, technical):
    return [("ELIGIBILITY", item["requirement_id"], item) for item in eligibility["requirements"]] + [
        ("TECHNICAL", item["technical_id"], item) for item in technical["technical_requirements"]] + [
        ("BOQ", item["boq_item_id"], item) for item in technical["boq_items"]]


def validate_verification(verification, eligibility, technical, company_documents, *, reference_date):
    date.fromisoformat(reference_date)
    findings = verification.get("findings")
    if not isinstance(findings, list):
        raise ValueError("Findings must be a list.")
    targets = {(kind, ident): item for kind, ident, item in collect_targets(eligibility, technical)}
    actual = [(f.get("target_type"), f.get("target_id")) for f in findings]
    if len(actual) != len(set(actual)):
        raise ValueError("Duplicate findings detected.")
    if set(actual) != set(targets):
        raise ValueError("Findings do not match extracted requirements.")
    for finding in findings:
        if finding.get("status") == "MISSING_EVIDENCE" and not documents_complete(company_documents):
            raise ValueError("MISSING_EVIDENCE requires confirmed document completeness and readable pages.")
    validate_shape(verification, VerificationOutput)
    for finding in findings:
        status, evidence = finding["status"], finding["evidence"]
        if not finding["explanation"].strip():
            raise ValueError("Finding explanation must not be empty.")
        for source in evidence:
            validate_citation(source, company_documents)
        if status in {"SATISFIED", "CONTRADICTED"}:
            if not evidence:
                raise ValueError(f"{status} finding requires evidence.")
            item = targets[(finding["target_type"], finding["target_id"])]
            if item["needs_review"] or source_uncertain(evidence, company_documents, table=finding["target_type"] == "BOQ"):
                raise ValueError("Uncertain target or company evidence requires review.")
        if status == "MISSING_EVIDENCE" and finding["target_type"] == "BOQ" and any(
            table_uncertain(page) for doc in company_documents for page in doc["pages"]
        ):
            raise ValueError("Missing BOQ evidence requires searchable table relationships.")
        if status == "MISSING_EVIDENCE" and evidence:
            raise ValueError("Missing evidence finding cannot contain evidence.")
        if finding["review_required"] != (status == "NEEDS_REVIEW"):
            raise ValueError("Finding review flag does not match status.")
        if bool(finding["uncertainty_reasons"]) != finding["review_required"]:
            raise ValueError("Finding review requires explicit uncertainty reasons.")


def validate_report(report: Report, documents: list[DocumentPages]) -> None:
    validate_shape(report, Report)
    date.fromisoformat(report["reference_date"])
    for document in documents:
        validate_document(document)
    if len({doc["document_id"] for doc in documents}) != len(documents):
        raise ValueError("Duplicate document IDs.")
    if len([doc for doc in documents if doc["role"] == "TENDER"]) != 1:
        raise ValueError("Report requires exactly one tender.")
    manifest_keys = ("document_id", "filename", "role", "completeness", "completeness_basis", "warnings")
    manifests = [{key: doc[key] for key in manifest_keys} for doc in documents]
    if report["documents"] != manifests:
        raise ValueError("Report manifests do not match source documents.")
    tender = next(doc for doc in documents if doc["role"] == "TENDER")
    companies = [doc for doc in documents if doc["role"] == "COMPANY"]
    for output in (report["eligibility"], report["technical"], {"provenance": report["verification_provenance"]}):
        provenance = output["provenance"]
        if provenance["mode"] != report["mode"]:
            raise ValueError("Provenance mode mismatch.")
        if any(not provenance[key].strip() for key in ("provider", "model", "prompt_version")):
            raise ValueError("Incomplete provenance.")
    validate_extractions(report["eligibility"], report["technical"], tender)
    validate_verification({"findings": report["findings"], "provenance": report["verification_provenance"],
                           "warnings": []}, report["eligibility"], report["technical"], companies,
                          reference_date=report["reference_date"])
    if report["coverage_confirmed"] and (
        report["mode"] != "AI" or not companies or not documents_complete(documents)
        or report["technical"]["boq_status"] == "NEEDS_REVIEW" or report["warnings"]
        or any(f["review_required"] for f in report["findings"])
    ):
        raise ValueError("Report coverage cannot be confirmed with uncertainty.")
