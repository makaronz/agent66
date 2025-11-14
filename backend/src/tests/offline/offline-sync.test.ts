import request from 'supertest';
import app from '../../server';
import { connectDB, closeDB, clearDB } from '../helpers/database';
import { createTestUserWithToken } from '../helpers/auth';

describe('Offline Sync Functionality Tests', () => {
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

    const user = await createTestUserWithToken({
      email: 'offline-test@filmcrew.com',
      firstName: 'Offline',
      lastName: 'Test',
      role: 'CREW',
      department: 'Camera'
    });

    authToken = user.token;
    userId = user.userId;
  });

  describe('Offline Timesheet Entry Queue', () => {
    it('should queue timesheet entries when offline', async () => {
      // Simulate offline mode by setting offline flag in user session
      await request(app)
        .post('/api/user/set-offline-mode')
        .set('Authorization', `Bearer ${authToken}`)
        .send({ offline: true })
        .expect(200);

      // Create timesheet entry while offline
      const timesheetData = {
        date: '2025-10-15',
        clockIn: '08:00',
        clockOut: '17:00',
        breakDuration: 60,
        projectId: 'proj-001',
        department: 'Camera',
        location: 'Studio A',
        notes: 'Created offline',
        clientTimestamp: new Date().toISOString(),
        deviceId: 'mobile-device-001'
      };

      const response = await request(app)
        .post('/api/time-entries/entry')
        .set('Authorization', `Bearer ${authToken}`)
        .send(timesheetData)
        .expect(202); // Accepted for sync

      expect(response.body).toHaveProperty('queued', true);
      expect(response.body).toHaveProperty('queueId');
      expect(response.body).toHaveProperty('clientTimestamp');

      // Verify entry is in sync queue
      const queueResponse = await request(app)
        .get('/api/sync/queue')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      expect(queueResponse.body.queuedItems).toHaveLength(1);
      expect(queueResponse.body.queuedItems[0]).toMatchObject({
        type: 'timesheet_entry',
        userId,
        data: expect.objectContaining({
          date: '2025-10-15',
          clockIn: '08:00',
          clockOut: '17:00'
        })
      });
    });

    it('should handle multiple offline operations in correct order', async () => {
      // Set offline mode
      await request(app)
        .post('/api/user/set-offline-mode')
        .set('Authorization', `Bearer ${authToken}`)
        .send({ offline: true })
        .expect(200);

      // Create multiple timesheet entries
      const entries = [
        { date: '2025-10-13', clockIn: '08:00', clockOut: '17:00', notes: 'Entry 1' },
        { date: '2025-10-14', clockIn: '08:00', clockOut: '17:00', notes: 'Entry 2' },
        { date: '2025-10-15', clockIn: '08:00', clockOut: '17:00', notes: 'Entry 3' }
      ];

      const queueIds = [];

      for (let i = 0; i < entries.length; i++) {
        const response = await request(app)
          .post('/api/time-entries/entry')
          .set('Authorization', `Bearer ${authToken}`)
          .send({
            ...entries[i],
            breakDuration: 60,
            projectId: 'proj-001',
            department: 'Camera',
            location: 'Studio A',
            clientTimestamp: new Date(Date.now() + i * 1000).toISOString(), // Sequential timestamps
            deviceId: 'mobile-device-001'
          })
          .expect(202);

        queueIds.push(response.body.queueId);
      }

      // Update one of the entries
      await request(app)
        .put(`/api/sync/queue/${queueIds[1]}`)
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          action: 'update',
          data: {
            notes: 'Entry 2 - Updated offline',
            clockOut: '18:00' // Extended hours
          }
        })
        .expect(200);

      // Delete one entry
      await request(app)
        .delete(`/api/sync/queue/${queueIds[2]}`)
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      // Verify queue state
      const queueResponse = await request(app)
        .get('/api/sync/queue')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      expect(queueResponse.body.queuedItems).toHaveLength(2); // One deleted

      // Verify order is maintained
      const firstItem = queueResponse.body.queuedItems[0];
      const secondItem = queueResponse.body.queuedItems[1];

      expect(new Date(firstItem.clientTimestamp)).toBeLessThan(new Date(secondItem.clientTimestamp));
      expect(firstItem.data.notes).toBe('Entry 1');
      expect(secondItem.data.notes).toBe('Entry 2 - Updated offline');
    });
  });

  describe('Sync Conflict Resolution', () => {
    let existingEntryId: string;

    beforeEach(async () => {
      // Create an existing timesheet entry
      const existingEntry = await request(app)
        .post('/api/time-entries/entry')
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          date: '2025-10-15',
          clockIn: '08:00',
          clockOut: '17:00',
          breakDuration: 60,
          projectId: 'proj-001',
          department: 'Camera',
          location: 'Studio A'
        })
        .expect(201);

      existingEntryId = existingEntry.body.id;
    });

    it('should detect conflicts during sync', async () => {
      // Go offline and modify existing entry
      await request(app)
        .post('/api/user/set-offline-mode')
        .set('Authorization', `Bearer ${authToken}`)
        .send({ offline: true })
        .expect(200);

      // Modify entry while offline
      await request(app)
        .put(`/api/time-entries/${existingEntryId}`)
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          notes: 'Modified offline',
          clockOut: '18:00'
        })
        .expect(202); // Queued for sync

      // Simulate another user modifying the same entry online
      await request(app)
        .put(`/api/time-entries/${existingEntryId}`)
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          notes: 'Modified by another user',
          clockOut: '19:00'
        })
        .expect(200);

      // Go back online and sync
      await request(app)
        .post('/api/user/set-offline-mode')
        .set('Authorization', `Bearer ${authToken}`)
        .send({ offline: false })
        .expect(200);

      // Initiate sync
      const syncResponse = await request(app)
        .post('/api/sync/process')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(207); // Multi-status with conflicts

      expect(syncResponse.body).toHaveProperty('conflicts');
      expect(syncResponse.body.conflicts).toHaveLength(1);

      const conflict = syncResponse.body.conflicts[0];
      expect(conflict).toMatchObject({
        type: 'UPDATE_CONFLICT',
        entityId: existingEntryId,
        entityType: 'timesheet_entry',
        localVersion: expect.objectContaining({
          notes: 'Modified offline',
          clockOut: '18:00'
        }),
        serverVersion: expect.objectContaining({
          notes: 'Modified by another user',
          clockOut: '19:00'
        })
      });
    });

    it('should resolve conflicts with user-selected strategy', async () => {
      // Create conflict scenario
      await request(app)
        .post('/api/user/set-offline-mode')
        .set('Authorization', `Bearer ${authToken}`)
        .send({ offline: true })
        .expect(200);

      await request(app)
        .put(`/api/time-entries/${existingEntryId}`)
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          notes: 'Offline modification',
          clockOut: '20:00'
        })
        .expect(202);

      await request(app)
        .post('/api/user/set-offline-mode')
        .set('Authorization', `Bearer ${authToken}`)
        .send({ offline: false })
        .expect(200);

      const syncResponse = await request(app)
        .post('/api/sync/process')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(207);

      const conflictId = syncResponse.body.conflicts[0].conflictId;

      // Resolve conflict by keeping local version
      const resolutionResponse = await request(app)
        .post(`/api/sync/conflicts/${conflictId}/resolve`)
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          strategy: 'USE_LOCAL',
          mergeFields: {
            notes: 'Resolved - kept offline changes but merged latest server timestamp'
          }
        })
        .expect(200);

      expect(resolution.body.status).toBe('RESOLVED');

      // Verify resolved entry
      const entryResponse = await request(app)
        .get(`/api/time-entries/${existingEntryId}`)
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      expect(entryResponse.body.notes).toBe('Resolved - kept offline changes but merged latest server timestamp');
      expect(entryResponse.body.clockOut).toBe('20:00'); // Local version kept
    });
  });

  describe('Incremental Sync and Delta Updates', () => {
    it('should support delta sync for large datasets', async () => {
      // Create initial dataset
      const initialEntries = [];
      for (let i = 0; i < 50; i++) {
        const entry = await request(app)
          .post('/api/time-entries/entry')
          .set('Authorization', `Bearer ${authToken}`)
          .send({
            date: `2025-10-${String(i + 1).padStart(2, '0')}`,
            clockIn: '08:00',
            clockOut: '17:00',
            breakDuration: 60,
            projectId: 'proj-001',
            department: 'Camera',
            location: 'Studio A'
          })
          .expect(201);

        initialEntries.push(entry.body);
      }

      // Get initial sync state
      const initialSyncResponse = await request(app)
        .get('/api/sync/state')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      const lastSyncToken = initialSyncResponse.body.syncToken;

      // Go offline and create new entries
      await request(app)
        .post('/api/user/set-offline-mode')
        .set('Authorization', `Bearer ${authToken}`)
        .send({ offline: true })
        .expect(200);

      const offlineEntries = [];
      for (let i = 50; i < 55; i++) {
        const response = await request(app)
          .post('/api/time-entries/entry')
          .set('Authorization', `Bearer ${authToken}`)
          .send({
            date: `2025-10-${String(i + 1).padStart(2, '0')}`,
            clockIn: '08:00',
            clockOut: '17:00',
            breakDuration: 60,
            projectId: 'proj-001',
            department: 'Camera',
            location: 'Studio A'
          })
          .expect(202);

        offlineEntries.push(response.body);
      }

      // Go back online and sync
      await request(app)
        .post('/api/user/set-offline-mode')
        .set('Authorization', `Bearer ${authToken}`)
        .send({ offline: false })
        .expect(200);

      // Perform delta sync
      const deltaSyncResponse = await request(app)
        .post('/api/sync/delta')
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          lastSyncToken,
          includeTypes: ['timesheet_entries', 'projects', 'user_profile']
        })
        .expect(200);

      expect(deltaSyncResponse.body).toHaveProperty('changes');
      expect(deltaSyncResponse.body.changes.timesheet_entries).toHaveLength(5);
      expect(deltaSyncResponse.body).toHaveProperty('newSyncToken');

      // Verify incremental updates only
      expect(deltaSyncResponse.body.changes.timesheet_entries).not.toContain(
        expect.objectContaining({ id: initialEntries[0].id })
      );
    });

    it('should handle sync resume after interruption', async () => {
      // Create large offline queue
      await request(app)
        .post('/api/user/set-offline-mode')
        .set('Authorization', `Bearer ${authToken}`)
        .send({ offline: true })
        .expect(200);

      // Create many entries to sync
      for (let i = 0; i < 100; i++) {
        await request(app)
          .post('/api/time-entries/entry')
          .set('Authorization', `Bearer ${authToken}`)
          .send({
            date: `2025-10-${String(i + 1).padStart(3, '0')}`,
            clockIn: '08:00',
            clockOut: '17:00',
            breakDuration: 60,
            projectId: 'proj-001',
            department: 'Camera',
            location: 'Studio A',
            notes: `Entry ${i + 1} - created offline`
          })
          .expect(202);
      }

      // Go back online
      await request(app)
        .post('/api/user/set-offline-mode')
        .set('Authorization', `Bearer ${authToken}`)
        .send({ offline: false })
        .expect(200);

      // Start sync with batch size limit
      const syncStartResponse = await request(app)
        .post('/api/sync/process')
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          batchSize: 25,
          timeout: 1000 // Short timeout to simulate interruption
        })
        .expect(202); // Partial completion

      expect(syncStartResponse.body).toHaveProperty('syncSessionId');
      expect(syncStartResponse.body).toHaveProperty('processedCount');
      expect(syncStartResponse.body).toHaveProperty('remainingCount');
      expect(syncStartResponse.body.processedCount).toBeLessThan(100);

      // Resume sync
      const resumeResponse = await request(app)
        .post(`/api/sync/resume/${syncStartResponse.body.syncSessionId}`)
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      expect(resumeResponse.body).toHaveProperty('status', 'COMPLETED');
      expect(resumeResponse.body).toHaveProperty('totalProcessed', 100);

      // Verify all entries were synced
      const queueResponse = await request(app)
        .get('/api/sync/queue')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      expect(queueResponse.body.queuedItems).toHaveLength(0);
    });
  });

  describe('Data Integrity and Validation', () => {
    it('should validate data integrity during sync', async () => {
      // Go offline and create entry with invalid data
      await request(app)
        .post('/api/user/set-offline-mode')
        .set('Authorization', `Bearer ${authToken}`)
        .send({ offline: true })
        .expect(200);

      const invalidEntry = {
        date: '2025-10-15',
        clockIn: '17:00', // After clock out
        clockOut: '08:00',
        breakDuration: 300, // Longer than work time
        projectId: 'invalid-project-id',
        department: 'Camera',
        location: 'Studio A'
      };

      const response = await request(app)
        .post('/api/time-entries/entry')
        .set('Authorization', `Bearer ${authToken}`)
        .send(invalidEntry)
        .expect(202); // Accepted offline, will validate on sync

      // Go back online and sync
      await request(app)
        .post('/api/user/set-offline-mode')
        .set('Authorization', `Bearer ${authToken}`)
        .send({ offline: false })
        .expect(200);

      const syncResponse = await request(app)
        .post('/api/sync/process')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(207); // Multi-status with validation errors

      expect(syncResponse.body).toHaveProperty('validationErrors');
      expect(syncResponse.body.validationErrors).toHaveLength(1);

      const validationError = syncResponse.body.validationErrors[0];
      expect(validationError).toMatchObject({
        type: 'VALIDATION_ERROR',
        entityId: response.body.queueId,
        errors: expect.arrayContaining([
          expect.objectContaining({
            field: 'clockIn',
            message: expect.stringContaining('must be before clock out')
          }),
          expect.objectContaining({
            field: 'breakDuration',
            message: expect.stringContaining('cannot exceed work duration')
          })
        ])
      });
    });

    it('should preserve audit trail during sync', async () => {
      // Go offline and create entry
      await request(app)
        .post('/api/user/set-offline-mode')
        .set('Authorization', `Bearer ${authToken}`)
        .send({ offline: true })
        .expect(200);

      const offlineEntry = {
        date: '2025-10-15',
        clockIn: '08:00',
        clockOut: '17:00',
        breakDuration: 60,
        projectId: 'proj-001',
        department: 'Camera',
        location: 'Studio A',
        clientTimestamp: new Date('2025-10-15T17:30:00Z').toISOString(),
        deviceId: 'mobile-device-001',
        appVersion: '2.1.0'
      };

      const createResponse = await request(app)
        .post('/api/time-entries/entry')
        .set('Authorization', `Bearer ${authToken}`)
        .send(offlineEntry)
        .expect(202);

      // Update entry offline
      await request(app)
        .put(`/api/sync/queue/${createResponse.body.queueId}`)
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          action: 'update',
          data: {
            notes: 'Updated offline at 18:00',
            clientTimestamp: new Date('2025-10-15T18:00:00Z').toISOString()
          }
        })
        .expect(200);

      // Sync to server
      await request(app)
        .post('/api/user/set-offline-mode')
        .set('Authorization', `Bearer ${authToken}`)
        .send({ offline: false })
        .expect(200);

      await request(app)
        .post('/api/sync/process')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      // Verify audit trail
      const entryResponse = await request(app)
        .get('/api/time-entries')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      const syncedEntry = entryResponse.body.entries[0];

      expect(syncedEntry).toMatchObject({
        createdAt: expect.any(String),
        updatedAt: expect.any(String),
        clientCreatedAt: '2025-10-15T17:30:00.000Z',
        clientUpdatedAt: '2025-10-15T18:00:00.000Z',
        deviceId: 'mobile-device-001',
        appVersion: '2.1.0',
        syncMetadata: expect.objectContaining({
          syncedAt: expect.any(String),
          syncSessionId: expect.any(String),
          conflicts: expect.arrayContaining([]),
          validationHistory: expect.arrayContaining([])
        })
      });
    });
  });
});