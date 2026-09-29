from io import BytesIO
from pathlib import Path

from pypdf import PdfReader


MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_TEXT_CHARACTERS = 50_000
SUPPORTED_SUFFIXES = {".txt", ".md", ".pdf"}


class DocumentError(ValueError):
    pass


def validate_upload(filename: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise DocumentError("Upload a .txt, .md, or text-based .pdf file")
    if not content or len(content) > MAX_UPLOAD_BYTES:
        raise DocumentError("Document must be nonempty and no larger than 10 MB")
    return suffix


def extract_document(content: bytes, suffix: str) -> str:
    try:
        if suffix == ".pdf":
            reader = PdfReader(BytesIO(content), strict=False)
            if reader.is_encrypted:
                raise DocumentError("Encrypted PDFs are not supported")
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        else:
            text = content.decode("utf-8-sig")
    except DocumentError:
        raise
    except Exception as error:
        raise DocumentError("Document could not be read") from error
    return validate_text(text)


def validate_text(text: str) -> str:
    clean = text.strip()
    if not clean:
        raise DocumentError("Document has no extractable text; scanned PDFs are not supported")
    if len(clean) > MAX_TEXT_CHARACTERS:
        raise DocumentError("Extracted text exceeds 50,000 characters")
    return clean
