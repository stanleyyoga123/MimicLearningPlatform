from pathlib import Path
from uuid import uuid4
import shutil

from apprenticeship.features.modules.document_ingestion import (
    DocumentError,
    extract_document,
    validate_text,
    validate_upload,
)
from apprenticeship.features.modules.module_record import ModuleRecord
from apprenticeship.features.modules.module_repository import ModuleRepository


class ModuleService:
    def __init__(self, repository: ModuleRepository, data_dir: Path):
        self._repository = repository
        self._data_dir = data_dir

    def submit(self, text: str | None, filename: str | None, content: bytes | None) -> ModuleRecord:
        if bool(text and text.strip()) == bool(content):
            raise DocumentError("Provide exactly one of pasted text or a document")
        if content is not None and filename is not None:
            suffix = validate_upload(filename, content)
            extracted = extract_document(content, suffix)
        else:
            suffix = ".txt"
            content = validate_text(text or "").encode("utf-8")
            extracted = content.decode("utf-8")

        module_id = uuid4().hex
        private = self._data_dir / "modules" / module_id / "private"
        private.mkdir(parents=True, exist_ok=False)
        try:
            (private / f"source{suffix}").write_bytes(content)
            (private / "source.txt").write_text(extracted, encoding="utf-8")
            return self._repository.create(module_id)
        except Exception:
            shutil.rmtree(private.parent)
            raise

    def get(self, module_id: str) -> ModuleRecord | None:
        return self._repository.get(module_id)

    def list(self) -> list[ModuleRecord]:
        return self._repository.list()

    def retry(self, module_id: str) -> ModuleRecord | None:
        return self._repository.retry(module_id)
