import { z } from 'zod';

export const moduleSchema = z.object({
  id: z.string(),
  title: z.string(),
  status: z.enum(['queued', 'running', 'completed', 'failed']),
  stage: z.enum(['queued', 'extracting', 'specifying', 'reference', 'starter', 'peers', 'verifying', 'publishing', 'completed']),
  created_at: z.string(),
  updated_at: z.string(),
  error: z.string().nullable(),
  spec: z.object({
    title: z.string(),
    scenario: z.string(),
    learning_objective: z.string(),
    task_type: z.enum(['bugfix', 'feature']),
    task_brief: z.string(),
    expected_behavior: z.string(),
    acceptance_criteria: z.array(z.string()),
    simplifications: z.array(z.string()),
  }).nullable(),
  peers: z.array(z.object({
    name: z.string(),
    role: z.string(),
    contribution_history: z.string(),
    responsibilities: z.array(z.string()),
    owned_files: z.array(z.string()),
  })),
  verification: z.object({
    passed: z.boolean(),
    summary: z.string(),
    checks: z.array(z.object({ name: z.string(), passed: z.boolean(), detail: z.string() })),
  }).nullable(),
  repository_url: z.string().nullable(),
  commit_sha: z.string().nullable(),
});

export const moduleListSchema = z.array(moduleSchema);
export type Module = z.infer<typeof moduleSchema>;
