import jwt from 'jsonwebtoken';
import { User } from '../../models/User';

export const createAuthToken = (userId: string, role: string = 'CREW'): string => {
  return jwt.sign(
    { userId, role },
    process.env.JWT_SECRET || 'test-secret',
    { expiresIn: '1d' }
  );
};

export const verifyToken = (token: string): any => {
  return jwt.verify(token, process.env.JWT_SECRET || 'test-secret');
};

export const createTestUserWithToken = async (userData: any = {}) => {
  const defaultUserData = {
    email: 'test@example.com',
    firstName: 'Test',
    lastName: 'User',
    role: 'CREW',
    password: 'password123',
    ...userData
  };

  const user = new User(defaultUserData);
  await user.save();

  const token = createAuthToken(user._id.toString(), user.role);

  return {
    user: user.toJSON(),
    token,
    userId: user._id.toString()
  };
};

export const createSupervisorToken = async (): Promise<string> => {
  const { token } = await createTestUserWithToken({
    email: 'supervisor@example.com',
    firstName: 'Supervisor',
    lastName: 'User',
    role: 'SUPERVISOR'
  });

  return token;
};

export const createAdminToken = async (): Promise<string> => {
  const { token } = await createTestUserWithToken({
    email: 'admin@example.com',
    firstName: 'Admin',
    lastName: 'User',
    role: 'ADMIN'
  });

  return token;
};