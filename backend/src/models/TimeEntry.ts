import { z } from 'zod';

export const EntryStatusEnum = z.enum([
  'DRAFT', 'SUBMITTED', 'APPROVED', 'REJECTED', 'LOCKED', 'PROCESSED'
]);

export const SyncStatusEnum = z.enum([
  'SYNCED', 'PENDING', 'CONFLICT', 'FAILED'
]);

export const TimeEntrySchema = z.object({
  id: z.string().optional(),
  userId: z.string(),
  projectId: z.string(),
  projectMemberId: z.string().optional(),
  phaseId: z.string().optional(),
  date: z.date(),
  clockIn: z.date(),
  clockOut: z.date().optional(),
  breakDuration: z.number().int().min(0).optional(),
  totalHours: z.number().positive().optional(),
  overtimeHours: z.number().min(0).optional(),
  rate: z.number().positive().optional(),
  totalPay: z.number().positive().optional(),
  status: EntryStatusEnum.default('DRAFT'),
  notes: z.string().optional(),
  location: z.string().optional(),
  weather: z.string().optional(),
  isOffline: z.boolean().default(false),
  syncStatus: SyncStatusEnum.default('SYNCED'),
  createdAt: z.date().optional(),
  updatedAt: z.date().optional(),
});

export const CreateTimeEntrySchema = TimeEntrySchema.omit({
  id: true, createdAt: true, updatedAt: true
});
export const UpdateTimeEntrySchema = TimeEntrySchema.partial().omit({
  id: true, createdAt: true, updatedAt: true
});
export const ClockInOutSchema = z.object({
  clockIn: z.date().optional(),
  clockOut: z.date().optional(),
  breakDuration: z.number().int().min(0).optional(),
  notes: z.string().optional(),
  location: z.string().optional(),
});

export type TimeEntry = z.infer<typeof TimeEntrySchema>;
export type CreateTimeEntry = z.infer<typeof CreateTimeEntrySchema>;
export type UpdateTimeEntry = z.infer<typeof UpdateTimeEntrySchema>;
export type ClockInOut = z.infer<typeof ClockInOutSchema>;
export type EntryStatus = z.infer<typeof EntryStatusEnum>;
export type SyncStatus = z.infer<typeof SyncStatusEnum>;