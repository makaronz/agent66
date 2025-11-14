import mongoose from 'mongoose';
import { User, UserRoleEnum } from '../../models/User';
import { connectDB, closeDB, clearDB } from '../helpers/database';

describe('User Model', () => {
  beforeAll(async () => {
    await connectDB();
  });

  afterAll(async () => {
    await closeDB();
  });

  beforeEach(async () => {
    await clearDB();
  });

  describe('User Schema Validation', () => {
    it('should create a valid user', async () => {
      const userData = {
        email: 'test@example.com',
        firstName: 'John',
        lastName: 'Doe',
        role: 'CREW' as UserRoleEnum.ValueType
      };

      const user = new User(userData);
      const savedUser = await user.save();

      expect(savedUser.email).toBe(userData.email);
      expect(savedUser.firstName).toBe(userData.firstName);
      expect(savedUser.lastName).toBe(userData.lastName);
      expect(savedUser.role).toBe(userData.role);
      expect(savedUser.createdAt).toBeDefined();
      expect(savedUser.updatedAt).toBeDefined();
    });

    it('should require email field', async () => {
      const userData = {
        firstName: 'John',
        lastName: 'Doe',
        role: 'CREW' as UserRoleEnum.ValueType
      };

      const user = new User(userData);

      await expect(user.save()).rejects.toThrow();
    });

    it('should validate email format', async () => {
      const userData = {
        email: 'invalid-email',
        firstName: 'John',
        lastName: 'Doe',
        role: 'CREW' as UserRoleEnum.ValueType
      };

      const user = new User(userData);

      await expect(user.save()).rejects.toThrow();
    });

    it('should require firstName field', async () => {
      const userData = {
        email: 'test@example.com',
        lastName: 'Doe',
        role: 'CREW' as UserRoleEnum.ValueType
      };

      const user = new User(userData);

      await expect(user.save()).rejects.toThrow();
    });

    it('should require lastName field', async () => {
      const userData = {
        email: 'test@example.com',
        firstName: 'John',
        role: 'CREW' as UserRoleEnum.ValueType
      };

      const user = new User(userData);

      await expect(user.save()).rejects.toThrow();
    });

    it('should validate firstName minimum length', async () => {
      const userData = {
        email: 'test@example.com',
        firstName: 'J',
        lastName: 'Doe',
        role: 'CREW' as UserRoleEnum.ValueType
      };

      const user = new User(userData);

      await expect(user.save()).rejects.toThrow();
    });

    it('should validate lastName minimum length', async () => {
      const userData = {
        email: 'test@example.com',
        firstName: 'John',
        lastName: 'D',
        role: 'CREW' as UserRoleEnum.ValueType
      };

      const user = new User(userData);

      await expect(user.save()).rejects.toThrow();
    });

    it('should accept valid user roles', async () => {
      const validRoles = ['ADMIN', 'SUPERVISOR', 'SUPERVISOR_USER', 'CREW', 'CLIENT', 'GUEST'];

      for (const role of validRoles) {
        const userData = {
          email: `${role.toLowerCase()}@example.com`,
          firstName: 'Test',
          lastName: 'User',
          role: role as UserRoleEnum.ValueType
        };

        const user = new User(userData);
        const savedUser = await user.save();

        expect(savedUser.role).toBe(role);
      }
    });

    it('should reject invalid user roles', async () => {
      const userData = {
        email: 'test@example.com',
        firstName: 'John',
        lastName: 'Doe',
        role: 'INVALID_ROLE'
      };

      const user = new User(userData);

      await expect(user.save()).rejects.toThrow();
    });

    it('should accept optional fields', async () => {
      const userData = {
        email: 'test@example.com',
        firstName: 'John',
        lastName: 'Doe',
        role: 'CREW' as UserRoleEnum.ValueType,
        department: 'Camera',
        phone: '+1234567890',
        avatar: 'https://example.com/avatar.jpg'
      };

      const user = new User(userData);
      const savedUser = await user.save();

      expect(savedUser.department).toBe(userData.department);
      expect(savedUser.phone).toBe(userData.phone);
      expect(savedUser.avatar).toBe(userData.avatar);
    });

    it('should validate avatar URL format', async () => {
      const userData = {
        email: 'test@example.com',
        firstName: 'John',
        lastName: 'Doe',
        role: 'CREW' as UserRoleEnum.ValueType,
        avatar: 'invalid-url'
      };

      const user = new User(userData);

      await expect(user.save()).rejects.toThrow();
    });
  });

  describe('User Methods', () => {
    let user: any;

    beforeEach(async () => {
      user = new User({
        email: 'test@example.com',
        firstName: 'John',
        lastName: 'Doe',
        role: 'CREW' as UserRoleEnum.ValueType
      });
      await user.save();
    });

    it('should have toJSON method that removes sensitive data', () => {
      const userObject = user.toJSON();

      expect(userObject.email).toBe('test@example.com');
      expect(userObject.firstName).toBe('John');
      expect(userObject.lastName).toBe('Doe');
      expect(userObject.role).toBe('CREW');
    });

    it('should have toObject method', () => {
      const userObject = user.toObject();

      expect(userObject.email).toBe('test@example.com');
      expect(userObject.firstName).toBe('John');
      expect(userObject.lastName).toBe('Doe');
    });
  });

  describe('User Queries', () => {
    beforeEach(async () => {
      // Create test users
      const users = [
        {
          email: 'admin@example.com',
          firstName: 'Admin',
          lastName: 'User',
          role: 'ADMIN' as UserRoleEnum.ValueType
        },
        {
          email: 'crew@example.com',
          firstName: 'Crew',
          lastName: 'Member',
          role: 'CREW' as UserRoleEnum.ValueType,
          department: 'Camera'
        },
        {
          email: 'client@example.com',
          firstName: 'Client',
          lastName: 'User',
          role: 'CLIENT' as UserRoleEnum.ValueType
        }
      ];

      for (const userData of users) {
        const user = new User(userData);
        await user.save();
      }
    });

    it('should find user by email', async () => {
      const foundUser = await User.findOne({ email: 'admin@example.com' });

      expect(foundUser).toBeTruthy();
      expect(foundUser!.email).toBe('admin@example.com');
      expect(foundUser!.role).toBe('ADMIN');
    });

    it('should find users by role', async () => {
      const crewMembers = await User.find({ role: 'CREW' });

      expect(crewMembers).toHaveLength(1);
      expect(crewMembers[0].email).toBe('crew@example.com');
    });

    it('should find users by department', async () => {
      const cameraDept = await User.find({ department: 'Camera' });

      expect(cameraDept).toHaveLength(1);
      expect(cameraDept[0].email).toBe('crew@example.com');
      expect(cameraDept[0].department).toBe('Camera');
    });

    it('should count users by role', async () => {
      const adminCount = await User.countDocuments({ role: 'ADMIN' });
      const crewCount = await User.countDocuments({ role: 'CREW' });
      const clientCount = await User.countDocuments({ role: 'CLIENT' });

      expect(adminCount).toBe(1);
      expect(crewCount).toBe(1);
      expect(clientCount).toBe(1);
    });

    it('should support regex search for names', async () => {
      const usersWithJohn = await User.find({
        $or: [
          { firstName: /Admin/i },
          { lastName: /User/i }
        ]
      });

      expect(usersWithJohn.length).toBeGreaterThan(0);
      expect(usersWithJohn.every(user =>
        user.firstName.match(/Admin/i) || user.lastName.match(/User/i)
      )).toBe(true);
    });
  });

  describe('User Indexes', () => {
    it('should have unique index on email field', async () => {
      const userData = {
        email: 'test@example.com',
        firstName: 'John',
        lastName: 'Doe',
        role: 'CREW' as UserRoleEnum.ValueType
      };

      const user1 = new User(userData);
      await user1.save();

      const user2 = new User(userData);

      await expect(user2.save()).rejects.toThrow();
    });
  });

  describe('Timestamps', () => {
    it('should set createdAt on document creation', async () => {
      const user = new User({
        email: 'test@example.com',
        firstName: 'John',
        lastName: 'Doe',
        role: 'CREW' as UserRoleEnum.ValueType
      });

      const savedUser = await user.save();

      expect(savedUser.createdAt).toBeDefined();
      expect(savedUser.createdAt).toBeInstanceOf(Date);
    });

    it('should set updatedAt on document creation and update', async () => {
      const user = new User({
        email: 'test@example.com',
        firstName: 'John',
        lastName: 'Doe',
        role: 'CREW' as UserRoleEnum.ValueType
      });

      const savedUser = await user.save();
      const originalUpdatedAt = savedUser.updatedAt;

      // Wait a bit to ensure different timestamp
      await new Promise(resolve => setTimeout(resolve, 10));

      savedUser.department = 'Camera';
      const updatedUser = await savedUser.save();

      expect(updatedUser.updatedAt).toBeDefined();
      expect(updatedUser.updatedAt.getTime()).toBeGreaterThan(originalUpdatedAt.getTime());
    });
  });

  describe('User Serialization', () => {
    let user: any;

    beforeEach(async () => {
      user = new User({
        email: 'test@example.com',
        firstName: 'John',
        lastName: 'Doe',
        role: 'CREW' as UserRoleEnum.ValueType,
        department: 'Camera'
      });
      await user.save();
    });

    it('should serialize to JSON correctly', () => {
      const json = user.toJSON();

      expect(json).toHaveProperty('_id');
      expect(json).toHaveProperty('email', 'test@example.com');
      expect(json).toHaveProperty('firstName', 'John');
      expect(json).toHaveProperty('lastName', 'Doe');
      expect(json).toHaveProperty('role', 'CREW');
      expect(json).toHaveProperty('department', 'Camera');
      expect(json).toHaveProperty('createdAt');
      expect(json).toHaveProperty('updatedAt');
    });

    it('should convert to plain object correctly', () => {
      const obj = user.toObject();

      expect(obj).toHaveProperty('_id');
      expect(obj).toHaveProperty('email', 'test@example.com');
      expect(obj).toHaveProperty('firstName', 'John');
      expect(obj).toHaveProperty('lastName', 'Doe');
      expect(obj).toHaveProperty('role', 'CREW');
    });
  });
});