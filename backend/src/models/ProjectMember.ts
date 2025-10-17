import { z } from 'zod';

export const ProjectMemberSchema = z.object({
  id: z.string().optional(),
  projectId: z.string(),
  userId: z.string(),
  role: z.string().min(2),
  department: z.string().optional(),
  rate: z.number().positive().optional(),
  overtimeRate: z.number().positive().optional(),
  joinedAt: z.date().default(() => new Date()),
  leftAt: z.date().optional(),
  isActive: z.boolean().default(true),
  createdAt: z.date().optional(),
  updatedAt: z.date().optional(),
});

export const CreateProjectMemberSchema = ProjectMemberSchema.omit({
  id: true, createdAt: true, updatedAt: true
});
export const UpdateProjectMemberSchema = ProjectMemberSchema.partial().omit({
  id: true, createdAt: true, updatedAt: true
});

export type ProjectMember = z.infer<typeof ProjectMemberSchema>;
export type CreateProjectMember = z.infer<typeof CreateProjectMemberSchema>;
export type UpdateProjectMember = z.infer<typeof UpdateProjectMemberSchema>;