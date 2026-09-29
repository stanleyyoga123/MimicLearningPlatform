import { moduleListSchema, moduleSchema, type Module } from '../schemas/module';

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = 'ApiError';
  }
}

export class ModuleApi {
  constructor(private readonly baseUrl: string, private readonly request: typeof fetch) {}

  async list(): Promise<Module[]> {
    return moduleListSchema.parse(await this.read('/modules'));
  }

  async get(id: string): Promise<Module> {
    return moduleSchema.parse(await this.read(`/modules/${encodeURIComponent(id)}`));
  }

  async create(input: { text?: string; file?: File }): Promise<Module> {
    const body = new FormData();
    if (input.text) body.set('text', input.text);
    if (input.file) body.set('file', input.file);
    return moduleSchema.parse(await this.read('/modules', { method: 'POST', body }));
  }

  async retry(id: string): Promise<Module> {
    return moduleSchema.parse(await this.read(`/modules/${encodeURIComponent(id)}/retry`, { method: 'POST' }));
  }

  private async read(path: string, options?: RequestInit): Promise<unknown> {
    let response: Response;
    try {
      const request = this.request;
      response = await request(`${this.baseUrl}${path}`, options);
    } catch {
      throw new ApiError('Could not reach the local API. Make sure the backend is running.', 0);
    }
    const payload: unknown = await response.json().catch(() => null);
    if (!response.ok) {
      const detail = payload && typeof payload === 'object' && 'detail' in payload ? payload.detail : null;
      throw new ApiError(typeof detail === 'string' ? detail : `Request failed (${response.status}).`, response.status);
    }
    return payload;
  }
}
