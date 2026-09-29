import { z } from 'zod';

export const sessionAgentSchema = z.object({
  id: z.string(),
  name: z.string(),
  role: z.string(),
  description: z.string(),
});

export const sessionStartSchema = z.object({
  id: z.string(),
  module_id: z.string(),
  agents: z.array(sessionAgentSchema),
  expires_in_seconds: z.number().int().positive(),
});

export const sessionStreamEventSchema = z.discriminatedUnion('type', [
  z.object({ type: z.literal('delta'), agent_id: z.string(), content: z.string() }),
  z.object({ type: z.literal('done'), agent_id: z.string() }),
  z.object({ type: z.literal('error'), agent_id: z.string(), detail: z.string(), status: z.number().int() }),
]);

export type SessionStart = z.infer<typeof sessionStartSchema>;
export type SessionAgent = z.infer<typeof sessionAgentSchema>;
