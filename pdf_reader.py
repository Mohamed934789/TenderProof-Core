"""PDF reader module with Arabic text support."""
from pathlib import Path
import re
import unicodedata
from pypdf import PdfReader

from models import (
    Completeness,
    CompletenessBasis,
    DocumentPages,
    DocumentRole,
)
from arabic_utils import (
    _has_arabic,
    _unshape_arabic,
    normalize_arabic_text,
    _arabic_order_errors,
    recover_arabic_run,
)

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
                page_warnings.append("Native text extraction failed for this page.")

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
                        if "".join(chunks) == original_text:
                            repaired = []
                            for chunk in chunks:
                                value = recover_arabic_run(chunk)
                                repaired.append(value)
                                for raw, normalized in zip(
                                    chunk.splitlines(), value.splitlines()
                                ):
                                    if (
                                        _arabic_order_errors(raw) > 0
                                        and normalized == _unshape_arabic(raw)
                                    ):
                                        uncertain_fragments.append(normalized.strip())
                            page_text = "".join(repaired)
                        else:
                            page_warnings.append(
                                "Arabic extraction callbacks did not match page text."
                            )
                    except Exception:
                        page_warnings.append(
                            "Arabic directional run extraction failed."
                        )
                    page_text, _ = normalize_arabic_text(page_text)
                    if page_text != original_text:
                        page_warnings.append(
                            "INFO: Arabic presentation forms/order normalized using contextual glyph evidence."
                        )

                for number, line in enumerate(page_text.splitlines(), 1):
                    if any(
                        fragment and fragment in line for fragment in uncertain_fragments
                    ):
                        page_warnings.append(
                            f"TEXT_LINE:{number}: Uncertain Arabic contextual-form order."
                        )
                    if "\ufffd" in line or re.search(r"\(cid:\d+\)", line) or any(
                        unicodedata.category(c) in {"Co", "Cs"}
                        or unicodedata.category(c) == "Cc" and c not in "\t"
                        for c in line
                    ):
                        page_warnings.append(
                            f"TEXT_LINE:{number}: Extracted text contains replacement characters or unmapped glyphs."
                        )
                    if re.search(r"(?<![\w\u0640])ل(?![\w\u0640])", line):
                        page_warnings.append(
                            f"TEXT_LINE:{number}: Isolated Arabic lam may be a truncated ligature."
                        )
                readability = (
                    "PARTIAL"
                    if any(not w.startswith("INFO:") for w in page_warnings)
                    else "READABLE"
                )

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

# Compatibility alias for the extracted Arabic helper.
from arabic_utils import recover_arabic_run as _recover_arabic_run
