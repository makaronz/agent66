import { z } from 'zod';

export const UserRoleEnum = z.enum(['ADMIN', 'SUPERVISOR', 'SUPERVISOR_USER', 'CREW', 'CLIENT', 'GUEST']);

export const UserSchema = z.object({
  id: z.string().optional(),
  email: z.string().email(),
  firstName: z.string().min(2),
  lastName: z.string().min(2),
  role: UserRoleEnum.default('CREW'),
  department: z.string().optional(),
  phone: z.string().optional(),
  avatar: z.string().url().optional(),
  createdAt: z.date().optional(),
  updatedAt: z.date().optional(),
});

export const CreateUserSchema = UserSchema.omit({ id: true, createdAt: true, updatedAt: true });
export const UpdateUserSchema = UserSchema.partial().omit({ id: true, createdAt: true, updatedAt: true });

export type User = z.infer<typeof UserSchema>;
export type CreateUser = z.infer<typeof CreateUserSchema>;
export type UpdateUser = z.infer<typeof UpdateUserSchema>;
export type UserRole = z.infer<typeof UserRoleEnum>;