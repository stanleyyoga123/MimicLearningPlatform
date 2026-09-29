"""Run generation and review queues serially without starving either queue."""

from pydantic import ValidationError

from apprenticeship.features.modules.module_pipeline import ModulePipeline
from apprenticeship.features.modules.module_repository import ModuleRepository
from apprenticeship.features.submissions.submission_pipeline import SubmissionPipeline
from apprenticeship.features.submissions.submission_repository import SubmissionRepository


class JobWorker:
    def __init__(
        self,
        modules: ModuleRepository,
        module_pipeline: ModulePipeline,
        submissions: SubmissionRepository,
        submission_pipeline: SubmissionPipeline,
    ) -> None:
        self._modules = modules
        self._module_pipeline = module_pipeline
        self._submissions = submissions
        self._submission_pipeline = submission_pipeline
        self._prefer_submission = False

    def run_next(self) -> bool:
        operations = (self._run_submission, self._run_module) if self._prefer_submission else (
            self._run_module, self._run_submission,
        )
        for operation in operations:
            if operation():
                return True
        return False

    def _run_module(self) -> bool:
        module = self._modules.claim_next()
        if module is None:
            return False
        self._prefer_submission = True
        try:
            self._module_pipeline.run(module)
        except Exception as error:
            module.status = "failed"
            module.error = str(error) or type(error).__name__
            self._modules.save(module)
        return True

    def _run_submission(self) -> bool:
        submission = self._submissions.claim_next()
        if submission is None:
            return False
        self._prefer_submission = False
        try:
            self._submission_pipeline.run(submission)
        except ValidationError:
            submission.status = "failed"
            submission.error = "Review data could not be validated. Retry this submission."
            self._submissions.save(submission)
        except (RuntimeError, ValueError, TimeoutError) as error:
            submission.status = "failed"
            submission.error = str(error) or "Review failed. Retry this submission."
            self._submissions.save(submission)
        except Exception:
            submission.status = "failed"
            submission.error = "Review worker failed unexpectedly. Retry this submission."
            self._submissions.save(submission)
        return True
