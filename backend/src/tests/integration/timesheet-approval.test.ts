import request from 'supertest';
import app from '../../server';
import { connectDB, closeDB, clearDB } from '../helpers/database';
import { createTestUserWithToken } from '../helpers/auth';

describe('Timesheet Approval Workflow Integration Tests', () => {
  beforeAll(async () => {
    await connectDB();
  });

  afterAll(async () => {
    await closeDB();
  });

  beforeEach(async () => {
    await clearDB();
  });

  describe('Complete Timesheet Submission and Approval Workflow', () => {
    let crewToken: string;
    let crewUserId: string;
    let supervisorToken: string;
    let supervisorUserId: string;
    let projectId: string;

    beforeEach(async () => {
      // Create crew member
      const crewUser = await createTestUserWithToken({
        email: 'crew@filmcrew.com',
        firstName: 'John',
        lastName: 'Doe',
        role: 'CREW',
        department: 'Camera'
      });
      crewToken = crewUser.token;
      crewUserId = crewUser.userId;

      // Create supervisor
      const supervisorUser = await createTestUserWithToken({
        email: 'supervisor@filmcrew.com',
        firstName: 'Jane',
        lastName: 'Smith',
        role: 'SUPERVISOR',
        department: 'Production'
      });
      supervisorToken = supervisorUser.token;
      supervisorUserId = supervisorUser.userId;

      // Create a project
      const projectResponse = await request(app)
        .post('/api/projects')
        .set('Authorization', `Bearer ${supervisorToken}`)
        .send({
          name: 'Summer Blockbuster 2025',
          code: 'SB2025-001',
          type: 'FEATURE_FILM',
          startDate: '2025-10-15',
          endDate: '2025-12-20',
          budget: 5000000,
          locations: ['Studio A', 'Location B'],
          departments: ['Camera', 'Lighting', 'Sound'],
          status: 'ACTIVE'
        });

      projectId = projectResponse.body.id;

      // Assign crew member to project
      await request(app)
        .post(`/api/projects/${projectId}/assign`)
        .set('Authorization', `Bearer ${supervisorToken}`)
        .send({
          userId: crewUserId,
          role: 'Camera Operator',
          department: 'Camera',
          startDate: '2025-10-15',
          endDate: '2025-12-20',
          rate: 45.50,
          overtimeRate: 68.25
        });
    });

    it('should handle complete timesheet submission and approval workflow', async () => {
      // Step 1: Crew member submits timesheet entry
      const timesheetEntry = {
        date: '2025-10-15',
        clockIn: '08:00',
        clockOut: '19:00', // 11 hours total
        breakDuration: 60,
        projectId,
        department: 'Camera',
        location: 'Studio A',
        notes: 'Extended shooting due to weather delay',
        equipmentUsed: ['Camera A1', 'Lighting Kit 1'],
        scenesShot: ['Scene 23', 'Scene 24', 'Scene 25']
      };

      const entryResponse = await request(app)
        .post('/api/time-entries/entry')
        .set('Authorization', `Bearer ${crewToken}`)
        .send(timesheetEntry)
        .expect(201);

      const entryId = entryResponse.body.id;

      expect(entryResponse.body.userId).toBe(crewUserId);
      expect(entryResponse.body.projectId).toBe(projectId);
      expect(entryResponse.body.regularHours).toBe(8);
      expect(entryResponse.body.overtimeHours).toBe(2);
      expect(entryResponse.body.status).toBe('PENDING');

      // Step 2: Supervisor reviews pending timesheets
      const pendingResponse = await request(app)
        .get('/api/supervisor/timesheets/pending')
        .set('Authorization', `Bearer ${supervisorToken}`)
        .expect(200);

      expect(pendingResponse.body.entries).toHaveLength(1);
      expect(pendingResponse.body.entries[0].id).toBe(entryId);
      expect(pendingResponse.body.entries[0].crewMember.name).toBe('John Doe');

      // Step 3: Supervisor requests clarification
      const clarificationResponse = await request(app)
        .post(`/api/time-entries/${entryId}/clarification`)
        .set('Authorization', `Bearer ${supervisorToken}`)
        .send({
          message: 'Please specify which weather conditions caused the delay',
          requiresAction: true
        })
        .expect(200);

      expect(clarificationResponse.body.status).toBe('NEEDS_CLARIFICATION');

      // Step 4: Crew member provides clarification
      const updateResponse = await request(app)
        .put(`/api/time-entries/${entryId}`)
        .set('Authorization', `Bearer ${crewToken}`)
        .send({
          notes: 'Extended shooting due to heavy rain - had to wait for weather clearance',
          weatherConditions: 'Heavy rain',
          delayReason: 'Weather'
        })
        .expect(200);

      expect(updateResponse.body.notes).toContain('heavy rain');
      expect(updateResponse.body.status).toBe('PENDING');

      // Step 5: Supervisor approves timesheet
      const approvalResponse = await request(app)
        .post(`/api/time-entries/${entryId}/approve`)
        .set('Authorization', `Bearer ${supervisorToken}`)
        .send({
          approved: true,
          notes: 'Approved - weather delay verified with production logs',
          overtimeApproved: true,
          adjustedHours: null // No adjustment needed
        })
        .expect(200);

      expect(approvalResponse.body.status).toBe('APPROVED');
      expect(approvalResponse.body.approvedBy).toBe(supervisorUserId);
      expect(approvalResponse.body.approvedAt).toBeDefined();

      // Step 6: Verify timesheet is locked for editing
      const editAttemptResponse = await request(app)
        .put(`/api/time-entries/${entryId}`)
        .set('Authorization', `Bearer ${crewToken}`)
        .send({ notes: 'Trying to edit approved entry' })
        .expect(400);

      expect(editAttemptResponse.body.message).toContain('cannot edit approved');

      // Step 7: Generate daily report
      const reportResponse = await request(app)
        .get(`/api/reports/daily?date=2025-10-15&projectId=${projectId}`)
        .set('Authorization', `Bearer ${supervisorToken}`)
        .expect(200);

      expect(reportResponse.body.entries).toHaveLength(1);
      expect(reportResponse.body.summary.totalHours).toBe(10);
      expect(reportResponse.body.summary.totalCost).toBeGreaterThan(0);
    });

    it('should handle rejection and resubmission workflow', async () => {
      // Submit timesheet entry
      const entryResponse = await request(app)
        .post('/api/time-entries/entry')
        .set('Authorization', `Bearer ${crewToken}`)
        .send({
          date: '2025-10-15',
          clockIn: '08:00',
          clockOut: '17:00',
          breakDuration: 60,
          projectId,
          department: 'Camera',
          location: 'Studio A'
        })
        .expect(201);

      const entryId = entryResponse.body.id;

      // Supervisor rejects with reason
      const rejectionResponse = await request(app)
        .post(`/api/time-entries/${entryId}/approve`)
        .set('Authorization', `Bearer ${supervisorToken}`)
        .send({
          approved: false,
          notes: 'Location not verified - please confirm actual shooting location',
          requiresResubmission: true
        })
        .expect(200);

      expect(rejectionResponse.body.status).toBe('REJECTED');
      expect(rejectionResponse.body.rejectionReason).toContain('Location not verified');

      // Crew member resubmits with corrections
      const resubmissionResponse = await request(app)
        .put(`/api/time-entries/${entryId}`)
        .set('Authorization', `Bearer ${crewToken}`)
        .send({
          location: 'Studio A - Main Stage',
          notes: 'Confirmed location - Main Stage used for Scene 23-25 shooting',
          resubmissionNotes: 'Location verified with production coordinator'
        })
        .expect(200);

      expect(resubmissionResponse.body.status).toBe('PENDING');
      expect(resubmissionResponse.body.location).toBe('Studio A - Main Stage');

      // Supervisor approves resubmitted entry
      const finalApprovalResponse = await request(app)
        .post(`/api/time-entries/${entryId}/approve`)
        .set('Authorization', `Bearer ${supervisorToken}`)
        .send({
          approved: true,
          notes: 'Location verified - approved'
        })
        .expect(200);

      expect(finalApprovalResponse.body.status).toBe('APPROVED');
    });

    it('should handle bulk approval workflow', async () => {
      // Create multiple timesheet entries
      const entries = [
        { date: '2025-10-13', clockIn: '08:00', clockOut: '17:00' },
        { date: '2025-10-14', clockIn: '09:00', clockOut: '18:00' },
        { date: '2025-10-15', clockIn: '08:30', clockOut: '16:30' }
      ];

      const entryIds = [];

      for (const entry of entries) {
        const response = await request(app)
          .post('/api/time-entries/entry')
          .set('Authorization', `Bearer ${crewToken}`)
          .send({
            ...entry,
            breakDuration: 60,
            projectId,
            department: 'Camera',
            location: 'Studio A'
          });

        entryIds.push(response.body.id);
      }

      // Supervisor performs bulk approval
      const bulkApprovalResponse = await request(app)
        .post('/api/supervisor/timesheets/bulk-approve')
        .set('Authorization', `Bearer ${supervisorToken}`)
        .send({
          entryIds,
          approved: true,
          notes: 'Weekly timesheet approval - all entries verified'
        })
        .expect(200);

      expect(bulkApproval.body.approved).toHaveLength(3);
      expect(bulkApproval.body.failed).toHaveLength(0);

      // Verify all entries are approved
      for (const entryId of entryIds) {
        const entryResponse = await request(app)
          .get(`/api/time-entries/${entryId}`)
          .set('Authorization', `Bearer ${supervisorToken}`)
          .expect(200);

        expect(entryResponse.body.status).toBe('APPROVED');
      }
    });

    it('should calculate overtime rates correctly', async () => {
      // Create entry with overtime
      const overtimeEntryResponse = await request(app)
        .post('/api/time-entries/entry')
        .set('Authorization', `Bearer ${crewToken}`)
        .send({
          date: '2025-10-15',
          clockIn: '06:00',
          clockOut: '22:00', // 16 hours total
          breakDuration: 120, // 2 hour break
          projectId,
          department: 'Camera',
          location: 'Studio A',
          notes: 'Extended shooting for complex action sequence'
        })
        .expect(201);

      const entryId = overtimeEntryResponse.body.id;

      expect(overtimeEntryResponse.body.regularHours).toBe(8);
      expect(overtimeEntryResponse.body.overtimeHours).toBe(6);

      // Approve with overtime verification
      const approvalResponse = await request(app)
        .post(`/api/time-entries/${entryId}/approve`)
        .set('Authorization', `Bearer ${supervisorToken}`)
        .send({
          approved: true,
          overtimeApproved: true,
          notes: 'Overtime approved - production schedule required extended hours',
          overtimeReason: 'Complex action sequence requiring additional setup time'
        })
        .expect(200);

      expect(approvalResponse.body.overtimeApproved).toBe(true);

      // Verify cost calculation
      const reportResponse = await request(app)
        .get(`/api/reports/cost?entryId=${entryId}`)
        .set('Authorization', `Bearer ${supervisorToken}`)
        .expect(200);

      expect(reportResponse.body.regularCost).toBe(8 * 45.50); // 8 hours * regular rate
      expect(reportResponse.body.overtimeCost).toBe(6 * 68.25); // 6 hours * overtime rate
      expect(reportResponse.body.totalCost).toBeGreaterThan(500);
    });
  });

  describe('Timesheet Dispute Resolution Workflow', () => {
    let crewToken: string;
    let supervisorToken: string;
    let adminToken: string;

    beforeEach(async () => {
      const crewUser = await createTestUserWithToken({
        email: 'crew@filmcrew.com',
        firstName: 'John',
        lastName: 'Doe',
        role: 'CREW'
      });
      crewToken = crewUser.token;

      const supervisorUser = await createTestUserWithToken({
        email: 'supervisor@filmcrew.com',
        firstName: 'Jane',
        lastName: 'Smith',
        role: 'SUPERVISOR'
      });
      supervisorToken = supervisorUser.token;

      const adminUser = await createTestUserWithToken({
        email: 'admin@filmcrew.com',
        firstName: 'Admin',
        lastName: 'User',
        role: 'ADMIN'
      });
      adminToken = adminUser.token;
    });

    it('should handle timesheet dispute and resolution workflow', async () => {
      // Create and submit timesheet
      const entryResponse = await request(app)
        .post('/api/time-entries/entry')
        .set('Authorization', `Bearer ${crewToken}`)
        .send({
          date: '2025-10-15',
          clockIn: '08:00',
          clockOut: '20:00', // 12 hours
          breakDuration: 60,
          projectId: 'proj-001',
          department: 'Camera',
          location: 'Studio A'
        })
        .expect(201);

      const entryId = entryResponse.body.id;

      // Supervisor rejects overtime
      await request(app)
        .post(`/api/time-entries/${entryId}/approve`)
        .set('Authorization', `Bearer ${supervisorToken}`)
        .send({
          approved: false,
          notes: 'Overtime not authorized - please revise to standard hours',
          requiresResubmission: true
        })
        .expect(200);

      // Crew member files dispute
      const disputeResponse = await request(app)
        .post(`/api/time-entries/${entryId}/dispute`)
        .set('Authorization', `Bearer ${crewToken}`)
        .send({
          reason: 'Overtime was requested by production manager for scene reshoot',
          description: 'Production manager John Smith explicitly requested extended hours for scene reshoot due to weather issues. Witness: Sarah Johnson (Lighting)',
          evidence: ['Production schedule update', 'Weather delay report'],
          requestedResolution: 'Full overtime approval'
        })
        .expect(200);

      expect(disputeResponse.body.status).toBe('UNDER_REVIEW');
      expect(disputeResponse.body.disputeFiledAt).toBeDefined();

      // Admin reviews dispute
      const adminReviewResponse = await request(app)
        .post(`/api/admin/disputes/${disputeResponse.body.disputeId}/review`)
        .set('Authorization', `Bearer ${adminToken}`)
        .send({
          resolution: 'APPROVED',
          notes: 'Production manager confirmation received. Weather delay verified with location reports. Overtime approved.',
          adjustedHours: null
        })
        .expect(200);

      expect(adminReviewResponse.body.disputeStatus).toBe('RESOLVED');
      expect(adminReviewResponse.body.resolution).toBe('APPROVED');

      // Verify timesheet is updated
      const finalEntryResponse = await request(app)
        .get(`/api/time-entries/${entryId}`)
        .set('Authorization', `Bearer ${crewToken}`)
        .expect(200);

      expect(finalEntryResponse.body.status).toBe('APPROVED');
      expect(finalEntryResponse.body.overtimeApproved).toBe(true);
    });
  });
});