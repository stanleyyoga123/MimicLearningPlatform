import type { Module } from '../../../src/features/modules/schemas/module';

export function learnerModule(overrides: Partial<Module> = {}): Module {
  return {
    id: 'ready-1', title: 'Webhook idempotency', status: 'completed', stage: 'completed',
    created_at: '2026-09-29T00:00:00Z', updated_at: '2026-09-29T00:00:00Z',
    error: null, repository_url: 'https://github.com/example/webhook-exercise', commit_sha: 'abc123',
    spec: {
      title: 'Webhook idempotency', scenario: 'Retries create duplicate orders.',
      learning_objective: 'Handle repeated events safely.', task_type: 'bugfix',
      task_brief: 'Make webhook processing idempotent.', expected_behavior: 'Return the existing order on retry.',
      acceptance_criteria: ['A repeated event creates only one order.'],
      simplifications: ['Payments are simulated locally.'],
    },
    peers: [{
      name: 'Maya', role: 'Backend teammate', contribution_history: 'Built the order endpoint.',
      responsibilities: ['Order persistence'], owned_files: ['app/orders.py'],
    }],
    verification: {
      passed: true, summary: 'Verified',
      checks: [{ name: 'reference', passed: true, detail: 'Author verification diagnostics' }],
    },
    ...overrides,
  };
}
