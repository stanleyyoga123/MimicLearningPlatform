import { submissionListSchema, submissionSchema, type Submission } from '../schemas/submission';

export class SubmissionApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = 'SubmissionApiError';
  }
}

export class SubmissionApi {
  constructor(private readonly baseUrl: string, private readonly request: typeof fetch) {}

  async list(moduleId: string, signal?: AbortSignal): Promise<Submission[]> {
    return submissionListSchema.parse(await this.read(`/modules/${encodeURIComponent(moduleId)}/submissions`, { signal }));
  }

  async create(moduleId: string, prUrl: string): Promise<Submission> {
    return submissionSchema.parse(await this.read(`/modules/${encodeURIComponent(moduleId)}/submissions`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ pr_url: prUrl }),
    }));
  }

  async get(submissionId: string, signal?: AbortSignal): Promise<Submission> {
    return submissionSchema.parse(await this.read(`/submissions/${encodeURIComponent(submissionId)}`, { signal }));
  }

  async retry(submissionId: string): Promise<Submission> {
    return submissionSchema.parse(await this.read(`/submissions/${encodeURIComponent(submissionId)}/retry`, { method: 'POST' }));
  }

  private async read(path: string, options: RequestInit): Promise<unknown> {
    let response: Response;
    try {
      const request = this.request;
      response = await request(`${this.baseUrl}${path}`, options);
    } catch (error) {
      if (options.signal?.aborted) throw error;
      throw new SubmissionApiError('Could not reach the local API. Please try again.', 0);
    }
    const payload: unknown = await response.json().catch(() => null);
    if (!response.ok) {
      const detail = payload && typeof payload === 'object' && 'detail' in payload ? payload.detail : null;
      throw new SubmissionApiError(typeof detail === 'string' ? detail : `Request failed (${response.status}).`, response.status);
    }
    return payload;
  }
}
