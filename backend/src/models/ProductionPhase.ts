import { z } from 'zod';

export const PhaseStatusEnum = z.enum([
  'PLANNED', 'ACTIVE', 'COMPLETED', 'DELAYED', 'CANCELLED'
]);

export const ProductionPhaseSchema = z.object({
  id: z.string().optional(),
  projectId: z.string(),
  name: z.string().min(2),
  description: z.string().optional(),
  startDate: z.date(),
  endDate: z.date(),
  status: PhaseStatusEnum.default('PLANNED'),
  createdAt: z.date().optional(),
  updatedAt: z.date().optional(),
});

export const CreateProductionPhaseSchema = ProductionPhaseSchema.omit({
  id: true, createdAt: true, updatedAt: true
});
export const UpdateProductionPhaseSchema = ProductionPhaseSchema.partial().omit({
  id: true, createdAt: true, updatedAt: true
});

export type ProductionPhase = z.infer<typeof ProductionPhaseSchema>;
export type CreateProductionPhase = z.infer<typeof CreateProductionPhaseSchema>;
export type UpdateProductionPhase = z.infer<typeof UpdateProductionPhaseSchema>;
export type PhaseStatus = z.infer<typeof PhaseStatusEnum>;