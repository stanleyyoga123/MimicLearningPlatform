# Verification evidence

Checked locally on 29 September 2026 with Python 3.12, Node.js 26, and Docker
Desktop 27.5.1.

## Automated checks

- Backend: `.venv/bin/pytest -q` from `backend` — **104 passed, 6 Docker-gated checks skipped**.
- Backend style: `.venv/bin/ruff check src tests verification` — passed.
- Frontend unit tests: **26 passed in the earlier streaming verification**; not rerun for PR submissions, per the requested workflow.
- Frontend build: `npm run build` — passed.
- Frontend style: `npm run lint` — passed.

The backend suite includes real offline Docker runs for a valid reference and
unsolved starter, changed acceptance tests, failing baseline behavior, unexpected
exceptions, different collected test identities, and whitespace parameter IDs
combined with unmet expected-exception assertions. Local Git integration tests
exercise privacy, idempotent publication, ambiguous remote outcomes, and refusal
to overwrite unrelated content. GitHub HTTP calls are replaced at that boundary
in the automated suite.

The Docker verifier was exercised in the earlier generation checks; the latest
workspace/chat run did not opt into those six Docker checks. New chat checks use
an injected model, clock, and HTTP transport to verify per-agent history,
starter-only context, close/expiry cancellation, input validation, provider
errors, retries, and the configured OpenRouter request without external calls.
Streaming checks cover SSE parsing, incremental delivery, truncated/error streams,
timeouts, and disconnect cleanup. ASGI send failures on both a content chunk and
the terminal completion event release the session and keep failed turns out of
history. Frontend checks cover split UTF-8/NDJSON frames, progressive rendering,
interrupted-reply retries, per-agent isolation, and closing during a reply.

PR submission checks use mocked GitHub/Codex boundaries. They cover URL and PR
eligibility, persisted history, revision deduplication, active-job exclusion,
restart recovery, queue fairness, stale retries, structured review validation,
blocking versus optional findings, publication reconciliation, and refusal to
mark an unconfirmed GitHub review successful. Snapshot checks cover merge-base
diffs, deleted-file anchors, and rejecting submodules or symlinks. Provider
malformed-response/timeout tests verify safe API errors, and the worker preserves
actionable failure messages. Codex process tests verify read-only review mode
and exclusion of GitHub/OpenRouter credentials.

GitHub App/webhook checks cover signed raw-body verification, installation-token
scope and refresh, duplicate deliveries, durable retries and recovery, repository
and installation matching, pending updates during an active review, and reopening
an outdated PR at the same revision. The webhook-only listener is checked for
exclusion of authoring, chat, administration, and API documentation routes.
App private-key configuration and Codex credential isolation are also covered.
Legacy database checks verify migration and repository backfill without rewriting
module records, including concurrent startup and preservation of existing mappings.

The final PR submission and GitHub App checks ran only backend tests/lint and frontend
type/build/lint checks. No browser checks or live GitHub/Codex/OpenRouter requests
were performed for this feature; the browser/live evidence below is historical.

The tests also cover text/PDF ingestion, API validation, job persistence and
retry, frozen-test checks, generated-file restrictions, source-tree separation,
Codex process behavior, nested exercise discovery, and strictly validated pytest
reporting. Frontend checks cover
submission errors, API validation and browser fetch binding, and non-overlapping
polling. Page integration checks cover the junior catalog's publication filter,
task selection and direct links, empty and error states, exclusion of author
controls and diagnostics, and legacy senior module links.

An upstream Starlette/AnyIO deprecation warning is emitted by TestClient; there
are no failing checks.

## Browser checks

The local app was inspected in Chrome. Confirmed module history, live progress,
empty-submission validation, selection preserved across refresh, worker restart
recovery, and retry through the UI. A real-browser fetch-binding error found
during this check was fixed and covered by a regression test.

The `/senior` and `/junior` pages were also checked in Chrome against the running
local API. The junior board showed the published webhook task while the senior
history retained both the ready and failed modules. Opening a task, refreshing
its URL, browser Back, and switching to the senior submission page all worked.

The new **Start task** workspace was checked in Chrome against a temporary local
API with an explicitly labeled test responder. Confirmed a coworker question and
reply, separate mentor conversation, and close returning to the task. A browser
scrolling issue found in this check was fixed so conversation updates scroll only
the message panel. Temporary preview services were stopped after checking.

Streaming was checked in Chrome against a local responder emitting four delayed
chunks. The reply visibly grew while the responding indicator remained present;
completion cleared the composer, and closing returned to the assignment.

## Live integration

The local app contains a published duplicate-webhook exercise. A fresh-clone
verification has not been recorded here. A live OpenRouter streaming probe using
`z-ai/glm-5.3-flash` succeeded with a fixed synthetic programming-language prompt:
first content at 7.73 seconds, five chunks totaling 44 characters, completion at
8.07 seconds. The key stayed server-side. No module context was sent.

Automatic approval review rejected the proposed live workspace probe because it
would transmit private module context to OpenRouter. That probe was not run;
the approved synthetic provider probe and local browser responder were used
instead. Full workspace-to-provider integration with module context remains
unverified live.

## Review

Independent correctness and style reviews identified and resolved browser fetch
binding, export/verification file consistency, HTTP response validation, and
stage typing issues. Live checks additionally improved pytest result collection
and handling of generated cache files.
Independent streaming reviews are complete. A completion-delivery failure that
could prematurely commit conversation history was corrected and covered by an
ASGI regression test; the follow-up correctness review found no remaining issue.

Independent PR submission correctness and style reviews are complete. Required
fixes covered incomplete submodule source, actionable worker errors, and malformed
GitHub response normalization. The focused correctness re-review confirmed those
fixes with no remaining actionable findings.

Independent GitHub App/webhook correctness and style reviews are complete. The
legacy module database migration and typed webhook administration responses were
corrected; focused re-reviews found no remaining actionable findings.
