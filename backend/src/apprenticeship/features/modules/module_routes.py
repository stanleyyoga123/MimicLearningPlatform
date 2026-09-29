from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from apprenticeship.features.modules.document_ingestion import DocumentError, MAX_UPLOAD_BYTES
from apprenticeship.features.modules.module_record import ModuleRecord
from apprenticeship.features.modules.module_service import ModuleService


def create_module_router(service: ModuleService) -> APIRouter:
    router = APIRouter(prefix="/modules", tags=["modules"])

    @router.post("", response_model=ModuleRecord, status_code=202)
    async def submit_module(
        text: str | None = Form(default=None),
        file: UploadFile | None = File(default=None),
    ) -> ModuleRecord:
        content = await file.read(MAX_UPLOAD_BYTES + 1) if file else None
        try:
            return service.submit(text, file.filename if file else None, content)
        except DocumentError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @router.get("", response_model=list[ModuleRecord])
    def list_modules() -> list[ModuleRecord]:
        return service.list()

    @router.get("/{module_id}", response_model=ModuleRecord)
    def get_module(module_id: str) -> ModuleRecord:
        module = service.get(module_id)
        if module is None:
            raise HTTPException(status_code=404, detail="Module not found")
        return module

    @router.post("/{module_id}/retry", response_model=ModuleRecord, status_code=202)
    def retry_module(module_id: str) -> ModuleRecord:
        try:
            module = service.retry(module_id)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        if module is None:
            raise HTTPException(status_code=404, detail="Module not found")
        return module

    return router
