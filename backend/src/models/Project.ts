import { z } from 'zod';

export const ProjectTypeEnum = z.enum([
  'FEATURE', 'SHORT', 'DOCUMENTARY', 'COMMERCIAL', 'MUSIC_VIDEO',
  'TV_EPISODE', 'TV_SERIES', 'WEB_SERIES', 'CORPORATE'
]);

export const ProjectStatusEnum = z.enum([
  'PLANNING', 'PRE_PRODUCTION', 'PRODUCTION', 'POST_PRODUCTION',
  'DELIVERY', 'COMPLETED', 'ON_HOLD', 'CANCELLED'
]);

export const ProjectSchema = z.object({
  id: z.string().optional(),
  title: z.string().min(2),
  description: z.string().optional(),
  status: ProjectStatusEnum.default('PLANNING'),
  type: ProjectTypeEnum.default('FEATURE'),
  startDate: z.date().optional(),
  endDate: z.date().optional(),
  budget: z.number().positive().optional(),
  currency: z.string().default('USD'),
  location: z.string().optional(),
  createdBy: z.string(),
  createdAt: z.date().optional(),
  updatedAt: z.date().optional(),
});

export const CreateProjectSchema = ProjectSchema.omit({
  id: true, createdAt: true, updatedAt: true
});
export const UpdateProjectSchema = ProjectSchema.partial().omit({
  id: true, createdAt: true, updatedAt: true
});

export type Project = z.infer<typeof ProjectSchema>;
export type CreateProject = z.infer<typeof CreateProjectSchema>;
export type UpdateProject = z.infer<typeof UpdateProjectSchema>;
export type ProjectType = z.infer<typeof ProjectTypeEnum>;
export type ProjectStatus = z.infer<typeof ProjectStatusEnum>;