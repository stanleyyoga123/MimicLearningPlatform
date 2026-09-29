import { z } from 'zod';

export const reviewFindingSchema = z.object({
  severity: z.enum(['high', 'medium', 'low']),
  blocking: z.boolean(),
  body: z.string(),
  path: z.string().nullable(),
  line: z.number().int().nullable(),
  side: z.enum(['LEFT', 'RIGHT']).nullable(),
});

export const submissionSchema = z.object({
  id: z.string(),
  module_id: z.string(),
  repository_full_name: z.string(),
  pr_number: z.number().int(),
  pr_url: z.string().url(),
  pr_title: z.string(),
  base_sha: z.string(),
  head_sha: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
  status: z.enum(['queued', 'running', 'needs_review', 'success', 'failed', 'outdated']),
  stage: z.enum(['queued', 'fetching', 'reviewing', 'publishing', 'completed']),
  error: z.string().nullable(),
  findings: z.array(reviewFindingSchema),
  summary: z.string().nullable(),
  github_review_id: z.number().int().nullable(),
  github_review_url: z.string().url().nullable(),
});

export const submissionListSchema = z.array(submissionSchema);
export type Submission = z.infer<typeof submissionSchema>;
