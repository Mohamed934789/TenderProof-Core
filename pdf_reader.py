import re
import unicodedata
from pathlib import Path
from pypdf import PdfReader
from models import (
    Completeness,
    CompletenessBasis,
    DocumentPages,
    DocumentRole,
)


def _has_arabic(text: str) -> bool:
    return any("ARABIC" in unicodedata.name(char, "") for char in text)


def _unshape_arabic(text: str) -> str:
    # Normalize only Arabic presentation forms, never identifiers or other scripts.
    return "".join(
        unicodedata.normalize("NFKC", char)
        if "ARABIC" in unicodedata.name(char, "")
        and ("\uFB50" <= char <= "\uFDFF" or "\uFE70" <= char <= "\uFEFC")
        else char
        for char in text
    )


def normalize_arabic_text(text: str) -> tuple[str, bool]:
    """Normalize presentation forms without guessing ordinary Arabic order."""
    return _unshape_arabic(text), _has_arabic(text)


def _arabic_order_errors(value: str) -> int:
    count = 0
    forms = {"INITIAL": (False, True), "MEDIAL": (True, True),
             "FINAL": (True, False), "ISOLATED": (False, False)}
    for word in value.split():
        edges = []
        for char in word:
            if not unicodedata.category(char).startswith("L"):
                continue
            name = unicodedata.name(char, "")
            edges.append(next((pair for form, pair in forms.items()
                               if "ARABIC" in name and f"{form} FORM" in name), None))
        if len(edges) < 2:
            continue
        count += bool(edges[0] and edges[0][0])
        count += bool(edges[-1] and edges[-1][1])
        count += sum(left[1] != right[0] for left, right in zip(edges, edges[1:])
                     if left is not None and right is not None)
    return count


def _recover_arabic_run(text: str) -> str:
    """Repair a pypdf visitor run only with consistent contextual-form evidence.

    INITIAL forms belong at the start of a logical word, FINAL forms at its
    end. Adjacent forms must agree on whether their shared edge is connected.
    Require inconsistent edges resolved by reversal; a single error is sufficient
    only for a complete word bounded by whitespace/punctuation on both sides.
    Ordinary Unicode Arabic provides no such evidence and is never reversed.
    This is intentionally limited to pypdf's directional runs: Arabic-Indic
    digits and neutral punctuation in those runs were prepended with the letters.
    """
    result = []
    for line in text.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        ending = line[len(content):]

        # LTR scripts and European digits are hard boundaries, never reversed.
        has_ltr = any(unicodedata.bidirectional(c) in {"L", "EN"} for c in content)
        errors = _arabic_order_errors(content)
        # A complete, whitespace/punctuation-bounded word has an unambiguous
        # direction when reversing removes its single contextual-form error.
        bounded_word = (bool(content) and not content[0].isalpha() and not content[-1].isalpha()
                        and len([word for word in content.split()
                                 if any(char.isalpha() for char in word)]) == 1)
        if not has_ltr and (errors >= 2 or errors == 1 and bounded_word) and _arabic_order_errors(content[::-1]) == 0:
            content = content[::-1]
        result.append(_unshape_arabic(content) + ending)
    return "".join(result)


def read_pdf(
    path: Path,
    *,
    document_id: str,
    role: DocumentRole,
    completeness: Completeness = "UNKNOWN",
    completeness_basis: CompletenessBasis = "UNKNOWN",
) -> DocumentPages:
    """Extract native text and report limitations for every PDF page."""
    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(f"PDF file not found: {path}")

    try:
        reader = PdfReader(path)

        if reader.is_encrypted:
            raise ValueError("Encrypted PDFs are not supported.")

        pages = []
        document_warnings = []

        for page_number, pdf_page in enumerate(reader.pages, start=1):
            page_warnings = []
            uncertain_fragments = []

            try:
                extracted_text = pdf_page.extract_text()
                page_text = extracted_text if extracted_text is not None else ""
            except Exception:
                page_text = ""
                page_warnings.append(
                    "Native text extraction failed for this page."
                )


            if not page_text.strip():
                readability = "UNREADABLE"
                extraction_method = "NONE"
                page_warnings.append(
                    "No native text was extracted; OCR is not implemented."
                )
            else:
                extraction_method = "NATIVE_TEXT"
                if _has_arabic(page_text):
                    original_text = page_text
                    chunks = []
                    try:
                        pdf_page.extract_text(
                            visitor_text=lambda text, *_: chunks.append(text)
                        )
                        # Some PDFs (e.g. nested forms) may report callbacks twice.
                        # Never reconstruct a page from inconsistent callbacks.
                        if "".join(chunks) == original_text:
                            repaired = []
                            for chunk in chunks:
                                value = _recover_arabic_run(chunk)
                                repaired.append(value)
                                for raw, normalized in zip(chunk.splitlines(), value.splitlines()):
                                    if (_arabic_order_errors(raw) > 0
                                            and normalized == _unshape_arabic(raw)):
                                        uncertain_fragments.append(normalized.strip())
                            page_text = "".join(repaired)
                        else:
                            page_warnings.append(
                                "Arabic extraction callbacks did not match page text."
                            )
                    except Exception:
                        page_warnings.append("Arabic directional run extraction failed.")
                    page_text, _ = normalize_arabic_text(page_text)
                    if page_text != original_text:
                        page_warnings.append("INFO: Arabic presentation forms/order normalized using contextual glyph evidence.")
                # Reading quality concerns text, separately from unreconstructed tables.
                # Keep malformed spans visible instead of guessing missing letters.
                for number, line in enumerate(page_text.splitlines(), 1):
                    if any(fragment and fragment in line for fragment in uncertain_fragments):
                        page_warnings.append(f"TEXT_LINE:{number}: Uncertain Arabic contextual-form order.")
                    if ("\ufffd" in line or re.search(r"\(cid:\d+\)", line)
                            or any(unicodedata.category(c) in {"Co", "Cs"}
                                   or unicodedata.category(c) == "Cc" and c not in "\t" for c in line)):
                        page_warnings.append(f"TEXT_LINE:{number}: Extracted text contains replacement characters or unmapped glyphs.")
                    # Observed in the local PDF: a lam-alef glyph maps to an isolated
                    # lam, including the negation in the experience condition. Do not
                    # invent the missing alef or trust the affected condition.
                    if re.search(r"(?<![\w\u0640])ل(?![\w\u0640])", line):
                        page_warnings.append(f"TEXT_LINE:{number}: Isolated Arabic lam may be a truncated ligature.")
                readability = "PARTIAL" if any(not w.startswith("INFO:") for w in page_warnings) else "READABLE"

            page_warnings.append(
                "TABLE: Table structure and visual reading order were not verified."
            )

            pages.append(
                {
                    "pdf_page": page_number,
                    "text": page_text,
                    "readability": readability,
                    "extraction_method": extraction_method,
                    "tables": [],
                    "warnings": page_warnings,
                }
            )

        if not pages:
            document_warnings.append("The PDF contains no pages.")

        return {
            "document_id": document_id,
            "filename": path.name,
            "role": role,
            "completeness": completeness,
            "completeness_basis": completeness_basis,
            "pages": pages,
            "warnings": document_warnings,
        }

    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Could not read PDF: {path.name}") from exc
