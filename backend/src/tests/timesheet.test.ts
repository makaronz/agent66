import request from 'supertest';
import app from '../server';
import { connectDB, closeDB, clearDB } from './helpers/database';
import { createTestUser, createAuthToken } from './helpers/auth';

describe('Timesheet API Tests', () => {
  let authToken: string;
  let userId: string;

  beforeAll(async () => {
    await connectDB();
  });

  afterAll(async () => {
    await closeDB();
  });

  beforeEach(async () => {
    await clearDB();
    const { user, token } = await createTestUser({
      email: 'crew@filmcrew.com',
      firstName: 'John',
      lastName: 'Doe',
      role: 'CREW',
      department: 'Camera'
    });
    authToken = token;
    userId = user.id;
  });

  describe('POST /api/timesheet/entry', () => {
    const validTimeEntry = {
      date: '2025-10-15',
      clockIn: '08:00',
      clockOut: '17:00',
      breakDuration: 60, // minutes
      projectId: 'proj-001',
      department: 'Camera',
      location: 'Studio A',
      notes: 'Regular shooting day',
      overtimeApproved: false
    };

    it('should create a new timesheet entry', async () => {
      const response = await request(app)
        .post('/api/timesheet/entry')
        .set('Authorization', `Bearer ${authToken}`)
        .send(validTimeEntry)
        .expect(201);

      expect(response.body).toHaveProperty('id');
      expect(response.body.userId).toBe(userId);
      expect(response.body.totalHours).toBe(7.5); // 9 hours - 1 hour break
      expect(response.body.status).toBe('PENDING');
    });

    it('should validate required fields', async () => {
      const invalidEntry = { ...validTimeEntry };
      delete (invalidEntry as any).date;

      const response = await request(app)
        .post('/api/timesheet/entry')
        .set('Authorization', `Bearer ${authToken}`)
        .send(invalidEntry)
        .expect(400);

      expect(response.body.message).toContain('date is required');
    });

    it('should prevent duplicate entries for same date', async () => {
      // Create first entry
      await request(app)
        .post('/api/timesheet/entry')
        .set('Authorization', `Bearer ${authToken}`)
        .send(validTimeEntry)
        .expect(201);

      // Try to create duplicate
      const response = await request(app)
        .post('/api/timesheet/entry')
        .set('Authorization', `Bearer ${authToken}`)
        .send(validTimeEntry)
        .expect(400);

      expect(response.body.message).toContain('already exists');
    });

    it('should calculate overtime correctly', async () => {
      const overtimeEntry = {
        ...validTimeEntry,
        clockIn: '06:00',
        clockOut: '20:00',
        breakDuration: 60
      };

      const response = await request(app)
        .post('/api/timesheet/entry')
        .set('Authorization', `Bearer ${authToken}`)
        .send(overtimeEntry)
        .expect(201);

      expect(response.body.regularHours).toBe(8);
      expect(response.body.overtimeHours).toBe(5); // 13 total - 8 regular
    });
  });

  describe('GET /api/timesheet/entries', () => {
    beforeEach(async () => {
      // Create sample timesheet entries
      const entries = [
        { date: '2025-10-13', clockIn: '08:00', clockOut: '17:00', projectId: 'proj-001' },
        { date: '2025-10-14', clockIn: '09:00', clockOut: '18:00', projectId: 'proj-002' },
        { date: '2025-10-15', clockIn: '08:30', clockOut: '16:30', projectId: 'proj-001' }
      ];

      for (const entry of entries) {
        await request(app)
          .post('/api/timesheet/entry')
          .set('Authorization', `Bearer ${authToken}`)
          .send({
            ...entry,
            breakDuration: 60,
            department: 'Camera',
            location: 'Studio A'
          });
      }
    });

    it('should return all timesheet entries for user', async () => {
      const response = await request(app)
        .get('/api/timesheet/entries')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      expect(response.body).toHaveProperty('entries');
      expect(response.body.entries).toHaveLength(3);
      expect(response.body.entries[0]).toHaveProperty('totalHours');
    });

    it('should filter entries by date range', async () => {
      const response = await request(app)
        .get('/api/timesheet/entries?startDate=2025-10-14&endDate=2025-10-15')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      expect(response.body.entries).toHaveLength(2);
    });

    it('should filter entries by project', async () => {
      const response = await request(app)
        .get('/api/timesheet/entries?projectId=proj-001')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      expect(response.body.entries).toHaveLength(2);
    });

    it('should paginate results', async () => {
      const response = await request(app)
        .get('/api/timesheet/entries?page=1&limit=2')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      expect(response.body.entries).toHaveLength(2);
      expect(response.body.pagination).toHaveProperty('total');
      expect(response.body.pagination).toHaveProperty('page');
      expect(response.body.pagination).toHaveProperty('totalPages');
    });
  });

  describe('PUT /api/timesheet/entry/:id', () => {
    let entryId: string;

    beforeEach(async () => {
      const response = await request(app)
        .post('/api/timesheet/entry')
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          date: '2025-10-15',
          clockIn: '08:00',
          clockOut: '17:00',
          breakDuration: 60,
          projectId: 'proj-001',
          department: 'Camera'
        });

      entryId = response.body.id;
    });

    it('should update timesheet entry', async () => {
      const updates = {
        clockOut: '19:00',
        notes: 'Extended shooting due to weather delay'
      };

      const response = await request(app)
        .put(`/api/timesheet/entry/${entryId}`)
        .set('Authorization', `Bearer ${authToken}`)
        .send(updates)
        .expect(200);

      expect(response.body.clockOut).toBe('19:00');
      expect(response.body.notes).toBe(updates.notes);
      expect(response.body.totalHours).toBeGreaterThan(8); // Should recalculate
    });

    it('should prevent editing approved entries', async () => {
      // First approve the entry
      await request(app)
        .put(`/api/timesheet/entry/${entryId}/approve`)
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      // Try to edit approved entry
      const response = await request(app)
        .put(`/api/timesheet/entry/${entryId}`)
        .set('Authorization', `Bearer ${authToken}`)
        .send({ notes: 'Trying to edit approved entry' })
        .expect(400);

      expect(response.body.message).toContain('cannot edit approved');
    });
  });

  describe('POST /api/timesheet/entry/:id/approve', () => {
    let entryId: string;
    let supervisorToken: string;

    beforeEach(async () => {
      // Create supervisor user
      const { token } = await createTestUser({
        email: 'supervisor@filmcrew.com',
        firstName: 'Jane',
        lastName: 'Smith',
        role: 'SUPERVISOR'
      });
      supervisorToken = token;

      // Create time entry
      const response = await request(app)
        .post('/api/timesheet/entry')
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          date: '2025-10-15',
          clockIn: '08:00',
          clockOut: '17:00',
          breakDuration: 60,
          projectId: 'proj-001',
          department: 'Camera'
        });

      entryId = response.body.id;
    });

    it('should approve timesheet entry with supervisor role', async () => {
      const response = await request(app)
        .post(`/api/timesheet/entry/${entryId}/approve`)
        .set('Authorization', `Bearer ${supervisorToken}`)
        .send({ notes: 'Approved after review' })
        .expect(200);

      expect(response.body.status).toBe('APPROVED');
      expect(response.body.approvedBy).toBeDefined();
      expect(response.body.approvedAt).toBeDefined();
    });

    it('should reject approval from non-supervisor', async () => {
      const response = await request(app)
        .post(`/api/timesheet/entry/${entryId}/approve`)
        .set('Authorization', `Bearer ${authToken}`) // Regular crew member
        .send({ notes: 'Trying to approve own entry' })
        .expect(403);

      expect(response.body.message).toContain('insufficient permissions');
    });
  });
});