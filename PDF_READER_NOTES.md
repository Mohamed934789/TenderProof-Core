# PDF Reader — Limitations

- **OCR:** Not implemented. Image-only or scanned PDF pages with no extractable text are classified as `UNREADABLE`.
- **Arabic text:** Arabic character order, ligatures, and font encoding may be extracted incorrectly. `READABLE` indicates that text was extracted, not that its Arabic meaning or order was verified.
- **Tables:** Table reconstruction is not implemented. The `tables` field remains an empty list; this does not mean the PDF contains no tables. Table content may appear as plain text in an unreliable order.
- **Readability classification:** Empty extracted text is classified as `UNREADABLE`; text containing the replacement character (`�`) is classified as `PARTIAL`; other non-empty text is classified as `READABLE`, with warnings about unverified content.