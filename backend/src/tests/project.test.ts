import request from 'supertest';
import app from '../server';
import { connectDB, closeDB, clearDB } from './helpers/database';
import { createTestUser, createAuthToken } from './helpers/auth';

describe('Project Management API Tests', () => {
  let authToken: string;
  let supervisorToken: string;

  beforeAll(async () => {
    await connectDB();
  });

  afterAll(async () => {
    await closeDB();
  });

  beforeEach(async () => {
    await clearDB();

    // Create regular user
    const { token } = await createTestUser({
      email: 'crew@filmcrew.com',
      firstName: 'John',
      lastName: 'Doe',
      role: 'CREW',
      department: 'Camera'
    });
    authToken = token;

    // Create supervisor
    const { token: superToken } = await createTestUser({
      email: 'supervisor@filmcrew.com',
      firstName: 'Jane',
      lastName: 'Smith',
      role: 'SUPERVISOR',
      department: 'Production'
    });
    supervisorToken = superToken;
  });

  describe('POST /api/projects', () => {
    const validProject = {
      name: 'Summer Blockbuster 2025',
      code: 'SB2025-001',
      type: 'FEATURE_FILM',
      startDate: '2025-10-15',
      endDate: '2025-12-20',
      budget: 5000000,
      locations: ['Studio A', 'Location B', 'Studio C'],
      departments: ['Camera', 'Lighting', 'Sound', 'Production'],
      status: 'ACTIVE'
    };

    it('should create a new project with supervisor role', async () => {
      const response = await request(app)
        .post('/api/projects')
        .set('Authorization', `Bearer ${supervisorToken}`)
        .send(validProject)
        .expect(201);

      expect(response.body).toHaveProperty('id');
      expect(response.body.name).toBe(validProject.name);
      expect(response.body.code).toBe(validProject.code);
      expect(response.body.createdBy).toBeDefined();
    });

    it('should reject project creation from non-supervisor', async () => {
      const response = await request(app)
        .post('/api/projects')
        .set('Authorization', `Bearer ${authToken}`)
        .send(validProject)
        .expect(403);

      expect(response.body.message).toContain('insufficient permissions');
    });

    it('should validate required project fields', async () => {
      const invalidProject = { ...validProject };
      delete (invalidProject as any).name;

      const response = await request(app)
        .post('/api/projects')
        .set('Authorization', `Bearer ${supervisorToken}`)
        .send(invalidProject)
        .expect(400);

      expect(response.body.message).toContain('name is required');
    });

    it('should prevent duplicate project codes', async () => {
      // Create first project
      await request(app)
        .post('/api/projects')
        .set('Authorization', `Bearer ${supervisorToken}`)
        .send(validProject)
        .expect(201);

      // Try to create duplicate
      const response = await request(app)
        .post('/api/projects')
        .set('Authorization', `Bearer ${supervisorToken}`)
        .send(validProject)
        .expect(400);

      expect(response.body.message).toContain('project code already exists');
    });
  });

  describe('GET /api/projects', () => {
    beforeEach(async () => {
      // Create sample projects
      const projects = [
        {
          name: 'Summer Blockbuster 2025',
          code: 'SB2025-001',
          type: 'FEATURE_FILM',
          status: 'ACTIVE'
        },
        {
          name: 'TV Series Episode 5',
          code: 'TVS2025-005',
          type: 'TV_EPISODE',
          status: 'ACTIVE'
        },
        {
          name: 'Commercial Campaign',
          code: 'CC2025-003',
          type: 'COMMERCIAL',
          status: 'COMPLETED'
        }
      ];

      for (const project of projects) {
        await request(app)
          .post('/api/projects')
          .set('Authorization', `Bearer ${supervisorToken}`)
          .send({
            ...project,
            startDate: '2025-10-15',
            endDate: '2025-12-20',
            budget: 1000000,
            locations: ['Studio A'],
            departments: ['Camera', 'Production']
          });
      }
    });

    it('should return all active projects', async () => {
      const response = await request(app)
        .get('/api/projects')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      expect(response.body).toHaveProperty('projects');
      expect(response.body.projects).toHaveLength(2); // Only active projects
    });

    it('should filter projects by status', async () => {
      const response = await request(app)
        .get('/api/projects?status=COMPLETED')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      expect(response.body.projects).toHaveLength(1);
      expect(response.body.projects[0].code).toBe('CC2025-003');
    });

    it('should filter projects by type', async () => {
      const response = await request(app)
        .get('/api/projects?type=FEATURE_FILM')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      expect(response.body.projects).toHaveLength(1);
      expect(response.body.projects[0].code).toBe('SB2025-001');
    });
  });

  describe('POST /api/projects/:projectId/assign', () => {
    let projectId: string;

    beforeEach(async () => {
      const projectResponse = await request(app)
        .post('/api/projects')
        .set('Authorization', `Bearer ${supervisorToken}`)
        .send({
          name: 'Test Project',
          code: 'TP2025-001',
          type: 'FEATURE_FILM',
          startDate: '2025-10-15',
          endDate: '2025-12-20',
          budget: 1000000,
          locations: ['Studio A'],
          departments: ['Camera', 'Production'],
          status: 'ACTIVE'
        });

      projectId = projectResponse.body.id;
    });

    it('should assign crew member to project', async () => {
      const assignment = {
        userId: 'crew-user-id', // This would come from the created user
        role: 'Camera Operator',
        department: 'Camera',
        startDate: '2025-10-15',
        endDate: '2025-12-20',
        rate: 45.50,
        overtimeRate: 68.25
      };

      const response = await request(app)
        .post(`/api/projects/${projectId}/assign`)
        .set('Authorization', `Bearer ${supervisorToken}`)
        .send(assignment)
        .expect(201);

      expect(response.body).toHaveProperty('id');
      expect(response.body.projectId).toBe(projectId);
      expect(response.body.role).toBe(assignment.role);
    });

    it('should prevent duplicate assignments', async () => {
      const assignment = {
        userId: 'crew-user-id',
        role: 'Camera Operator',
        department: 'Camera',
        startDate: '2025-10-15',
        endDate: '2025-12-20'
      };

      // First assignment
      await request(app)
        .post(`/api/projects/${projectId}/assign`)
        .set('Authorization', `Bearer ${supervisorToken}`)
        .send(assignment)
        .expect(201);

      // Duplicate assignment
      const response = await request(app)
        .post(`/api/projects/${projectId}/assign`)
        .set('Authorization', `Bearer ${supervisorToken}`)
        .send(assignment)
        .expect(400);

      expect(response.body.message).toContain('already assigned');
    });
  });

  describe('GET /api/projects/:projectId/timesheets', () => {
    let projectId: string;

    beforeEach(async () => {
      // Create project
      const projectResponse = await request(app)
        .post('/api/projects')
        .set('Authorization', `Bearer ${supervisorToken}`)
        .send({
          name: 'Test Project',
          code: 'TP2025-001',
          type: 'FEATURE_FILM',
          startDate: '2025-10-15',
          endDate: '2025-12-20',
          budget: 1000000,
          locations: ['Studio A'],
          departments: ['Camera', 'Production'],
          status: 'ACTIVE'
        });

      projectId = projectResponse.body.id;

      // Create timesheet entries for this project
      const entries = [
        { date: '2025-10-13', clockIn: '08:00', clockOut: '17:00' },
        { date: '2025-10-14', clockIn: '09:00', clockOut: '18:00' },
        { date: '2025-10-15', clockIn: '08:30', clockOut: '16:30' }
      ];

      for (const entry of entries) {
        await request(app)
          .post('/api/timesheet/entry')
          .set('Authorization', `Bearer ${authToken}`)
          .send({
            ...entry,
            projectId,
            breakDuration: 60,
            department: 'Camera',
            location: 'Studio A'
          });
      }
    });

    it('should return timesheet summary for project', async () => {
      const response = await request(app)
        .get(`/api/projects/${projectId}/timesheets`)
        .set('Authorization', `Bearer ${supervisorToken}`)
        .expect(200);

      expect(response.body).toHaveProperty('summary');
      expect(response.body).toHaveProperty('entries');
      expect(response.body.summary.totalHours).toBeGreaterThan(0);
      expect(response.body.summary.totalCrew).toBe(1);
      expect(response.body.entries).toHaveLength(3);
    });

    it('should calculate project cost breakdown', async () => {
      const response = await request(app)
        .get(`/api/projects/${projectId}/timesheets?includeCosts=true`)
        .set('Authorization', `Bearer ${supervisorToken}`)
        .expect(200);

      expect(response.body.summary).toHaveProperty('totalRegularCost');
      expect(response.body.summary).toHaveProperty('totalOvertimeCost');
      expect(response.body.summary).toHaveProperty('totalCost');
    });
  });
});