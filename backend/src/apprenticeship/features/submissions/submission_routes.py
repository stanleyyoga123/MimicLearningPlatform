from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from apprenticeship.features.submissions.submission_record import SubmissionRecord
from apprenticeship.features.submissions.submission_service import SubmissionError, SubmissionService


class SubmissionRequest(BaseModel):
    pr_url: str = Field(min_length=1, max_length=500)


def create_submission_router(service: SubmissionService) -> APIRouter:
    router = APIRouter(tags=["submissions"])

    @router.post("/modules/{module_id}/submissions", response_model=SubmissionRecord, status_code=202)
    def submit(module_id: str, request: SubmissionRequest) -> SubmissionRecord:
        try:
            return service.submit(module_id, request.pr_url)
        except SubmissionError as error:
            raise HTTPException(status_code=error.status_code, detail=str(error)) from error

    @router.get("/modules/{module_id}/submissions", response_model=list[SubmissionRecord])
    def list_for_module(module_id: str) -> list[SubmissionRecord]:
        try:
            return service.list(module_id)
        except SubmissionError as error:
            raise HTTPException(status_code=error.status_code, detail=str(error)) from error

    @router.get("/submissions/{submission_id}", response_model=SubmissionRecord)
    def get(submission_id: str) -> SubmissionRecord:
        try:
            return service.get(submission_id)
        except SubmissionError as error:
            raise HTTPException(status_code=error.status_code, detail=str(error)) from error

    @router.post("/submissions/{submission_id}/retry", response_model=SubmissionRecord,
                 status_code=202)
    def retry(submission_id: str) -> SubmissionRecord:
        try:
            return service.retry(submission_id)
        except SubmissionError as error:
            raise HTTPException(status_code=error.status_code, detail=str(error)) from error

    return router
