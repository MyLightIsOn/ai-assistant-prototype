import { z } from "zod";

/**
 * Validates cron expression format
 * Basic validation - full validation happens on backend with cron-parser
 */
const cronRegex = /^(\*|([0-9]|1[0-9]|2[0-9]|3[0-9]|4[0-9]|5[0-9])|\*\/([0-9]|1[0-9]|2[0-9]|3[0-9]|4[0-9]|5[0-9])) (\*|([0-9]|1[0-9]|2[0-3])|\*\/([0-9]|1[0-9]|2[0-3])) (\*|([1-9]|1[0-9]|2[0-9]|3[0-1])|\*\/([1-9]|1[0-9]|2[0-9]|3[0-1])) (\*|([1-9]|1[0-2])|\*\/([1-9]|1[0-2])) (\*|([0-6])|\*\/([0-6]))$/;

export const createTaskSchema = z.object({
  name: z.string().min(1, "Name is required").max(100, "Name must be less than 100 characters"),
  description: z.string().max(500, "Description must be less than 500 characters").optional(),
  command: z.string().min(1, "Command is required"),
  args: z.string().default(""),
  schedule: z.string().regex(cronRegex, "Invalid cron expression format"),
  enabled: z.boolean().default(true),
  priority: z.enum(["low", "default", "high", "urgent"]).default("default"),
  notifyOn: z.string().default("completion,error"),
  metadata: z.record(z.string(), z.any()).optional(),
});

export const updateTaskSchema = z.object({
  name: z.string().min(1).max(100).optional(),
  description: z.string().max(500).optional(),
  command: z.string().min(1).optional(),
  args: z.string().optional(),
  schedule: z.string().regex(cronRegex, "Invalid cron expression format").optional(),
  enabled: z.boolean().optional(),
  priority: z.enum(["low", "default", "high", "urgent"]).optional(),
  notifyOn: z.string().optional(),
  metadata: z.record(z.string(), z.any()).optional(),
});

export type CreateTaskInput = z.infer<typeof createTaskSchema>;
export type UpdateTaskInput = z.infer<typeof updateTaskSchema>;
