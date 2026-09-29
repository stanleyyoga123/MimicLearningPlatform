from io import BytesIO

import pytest
from pypdf import PdfWriter

from apprenticeship.features.modules.document_ingestion import (
    DocumentError,
    extract_document,
    validate_upload,
)


def test_text_document_extracts_source() -> None:
    assert extract_document(b"Duplicate webhook deliveries create two orders", ".md") == (
        "Duplicate webhook deliveries create two orders"
    )


def test_unreadable_pdf_has_actionable_error() -> None:
    with pytest.raises(DocumentError, match="could not be read"):
        extract_document(b"not a PDF", ".pdf")


def test_empty_scanned_pdf_is_rejected() -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    output = BytesIO()
    writer.write(output)
    with pytest.raises(DocumentError, match="scanned PDFs"):
        extract_document(output.getvalue(), ".pdf")


def test_unsupported_upload_is_rejected() -> None:
    with pytest.raises(DocumentError, match=".txt, .md, or text-based .pdf"):
        validate_upload("script.py", b"print('hello')")
