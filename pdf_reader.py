
"""Read PDF pages while preserving extracted text and page numbers.

OCR and table reconstruction are intentionally not implemented.
An empty tables list does not prove that a PDF contains no tables or BOQ.
"""

from pathlib import Path

from pypdf import PdfReader

from models import (
    Completeness,
    CompletenessBasis,
    DocumentPages,
    DocumentRole,
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

                if "\ufffd" in page_text:
                    readability = "PARTIAL"
                    page_warnings.append(
                        "Extracted text contains replacement characters; "
                        "some content may be corrupted."
                    )
                else:
                    readability = "READABLE"
                    page_warnings.append(
                        "Text was extracted, but semantic readability "
                        "and Arabic character order are not guaranteed."
                    )


            page_warnings.append(
                "Arabic text order and table structure were not verified; "
                "review the extracted content before relying on it."
            )

            page_warnings.append(
                "Table structure and visual reading order were not verified."
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
