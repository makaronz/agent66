import { Server as HTTPServer } from 'http';
import { Server as SocketIOServer } from 'socket.io';
import { WebSocketServer } from '../../websocket/server';
import { connectDB, closeDB, clearDB, createTestUser } from '../helpers/database';

describe('WebSocket Server', () => {
  let httpServer: HTTPServer;
  let wsServer: WebSocketServer;
  let io: SocketIOServer;
  let clientSocket: any;
  let serverSocket: any;

  beforeAll(async () => {
    await connectDB();

    // Create test HTTP server
    httpServer = new HTTPServer();
    wsServer = new WebSocketServer(httpServer);
    io = wsServer.getIO();

    // Start server on random port
    await new Promise<void>((resolve) => {
      httpServer.listen(() => {
        resolve();
      });
    });
  });

  afterAll(async () => {
    if (clientSocket) {
      clientSocket.disconnect();
    }
    if (serverSocket) {
      serverSocket.disconnect();
    }
    httpServer.close();
    await closeDB();
  });

  beforeEach(async () => {
    await clearDB();

    // Setup client connection
    clientSocket = require('socket.io-client')(`http://localhost:${(httpServer.address() as any).port}`, {
      auth: {
        token: 'test-token'
      }
    });

    await new Promise<void>((resolve) => {
      io.on('connection', (socket) => {
        serverSocket = socket;
        resolve();
      });
    });

    await new Promise<void>((resolve) => {
      clientSocket.on('connect', () => {
        resolve();
      });
    });
  });

  afterEach(() => {
    if (clientSocket && clientSocket.connected) {
      clientSocket.disconnect();
    }
    if (serverSocket && serverSocket.connected) {
      serverSocket.disconnect();
    }
  });

  describe('Connection Handling', () => {
    it('should establish WebSocket connection', () => {
      expect(clientSocket.connected).toBe(true);
      expect(serverSocket.connected).toBe(true);
    });

    it('should handle connection authentication', async () => {
      const authenticatedClient = require('socket.io-client')(
        `http://localhost:${(httpServer.address() as any).port}`,
        {
          auth: {
            token: 'valid-auth-token'
          }
        }
      );

      await new Promise<void>((resolve) => {
        authenticatedClient.on('authenticated', (data: any) => {
          expect(data).toHaveProperty('userId');
          expect(data).toHaveProperty('role');
          authenticatedClient.disconnect();
          resolve();
        });
      });
    });

    it('should reject connections without valid token', async () => {
      const unauthenticatedClient = require('socket.io-client')(
        `http://localhost:${(httpServer.address() as any).port}`,
        {
          auth: {
            token: 'invalid-token'
          }
        }
      );

      await new Promise<void>((resolve) => {
        unauthenticatedClient.on('connect_error', (error: any) => {
          expect(error.message).toContain('Authentication failed');
          unauthenticatedClient.disconnect();
          resolve();
        });
      });
    });

    it('should handle disconnection gracefully', () => {
      const disconnectSpy = jest.fn();
      serverSocket.on('disconnect', disconnectSpy);

      clientSocket.disconnect();

      // Allow time for disconnection to propagate
      setTimeout(() => {
        expect(disconnectSpy).toHaveBeenCalled();
      }, 100);
    });
  });

  describe('Room Management', () => {
    it('should allow users to join project rooms', async () => {
      const projectId = 'project-123';

      clientSocket.emit('join_project', { projectId });

      await new Promise<void>((resolve) => {
        clientSocket.on('joined_project', (data: any) => {
          expect(data.projectId).toBe(projectId);
          expect(data.message).toContain('joined project');
          resolve();
        });
      });

      expect(serverSocket.rooms.has(projectId)).toBe(true);
    });

    it('should allow users to leave project rooms', async () => {
      const projectId = 'project-123';

      // First join the room
      clientSocket.emit('join_project', { projectId });

      await new Promise<void>((resolve) => {
        clientSocket.on('joined_project', () => {
          // Then leave the room
          clientSocket.emit('leave_project', { projectId });
          resolve();
        });
      });

      await new Promise<void>((resolve) => {
        clientSocket.on('left_project', (data: any) => {
          expect(data.projectId).toBe(projectId);
          expect(data.message).toContain('left project');
          resolve();
        });
      });
    });

    it('should broadcast messages to project room members', async () => {
      const projectId = 'project-room-test';
      const message = 'Hello project team!';

      // Join project room
      clientSocket.emit('join_project', { projectId });

      await new Promise<void>((resolve) => {
        clientSocket.on('joined_project', () => {
          // Send message to room
          clientSocket.emit('project_message', {
            projectId,
            message,
            type: 'text'
          });

          resolve();
        });
      });

      await new Promise<void>((resolve) => {
        clientSocket.on('project_message_broadcast', (data: any) => {
          expect(data.message).toBe(message);
          expect(data.projectId).toBe(projectId);
          expect(data.type).toBe('text');
          resolve();
        });
      });
    });
  });

  describe('Real-time Updates', () => {
    it('should broadcast time entry updates', async () => {
      const timeEntry = {
        id: 'time-entry-123',
        userId: 'user-123',
        projectId: 'project-123',
        startTime: '09:00',
        endTime: '17:00',
        status: 'submitted'
      };

      clientSocket.emit('time_entry_update', timeEntry);

      await new Promise<void>((resolve) => {
        clientSocket.on('time_entry_updated', (data: any) => {
          expect(data.id).toBe(timeEntry.id);
          expect(data.status).toBe(timeEntry.status);
          resolve();
        });
      });
    });

    it('should broadcast project status changes', async () => {
      const projectUpdate = {
        projectId: 'project-123',
        status: 'completed',
        completionPercentage: 100
      };

      clientSocket.emit('project_status_update', projectUpdate);

      await new Promise<void>((resolve) => {
        clientSocket.on('project_status_updated', (data: any) => {
          expect(data.projectId).toBe(projectUpdate.projectId);
          expect(data.status).toBe(projectUpdate.status);
          expect(data.completionPercentage).toBe(projectUpdate.completionPercentage);
          resolve();
        });
      });
    });

    it('should handle crew location updates', async () => {
      const locationUpdate = {
        userId: 'user-123',
        latitude: 40.7128,
        longitude: -74.0060,
        timestamp: new Date().toISOString()
      };

      clientSocket.emit('location_update', locationUpdate);

      await new Promise<void>((resolve) => {
        clientSocket.on('location_updated', (data: any) => {
          expect(data.userId).toBe(locationUpdate.userId);
          expect(data.latitude).toBe(locationUpdate.latitude);
          expect(data.longitude).toBe(locationUpdate.longitude);
          resolve();
        });
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle malformed messages gracefully', () => {
      const errorHandlerSpy = jest.fn();
      serverSocket.on('error', errorHandlerSpy);

      // Send malformed data
      clientSocket.emit('invalid_event', { invalid: 'data' });

      setTimeout(() => {
        expect(errorHandlerSpy).toHaveBeenCalled();
      }, 100);
    });

    it('should validate required fields in messages', async () => {
      const invalidMessage = {
        // Missing required fields
        type: 'invalid'
      };

      clientSocket.emit('project_message', invalidMessage);

      await new Promise<void>((resolve) => {
        clientSocket.on('error', (error: any) => {
          expect(error.message).toContain('validation');
          resolve();
        });
      });
    });
  });

  describe('Performance', () => {
    it('should handle high-frequency messages', async () => {
      const messageCount = 100;
      const receivedMessages: any[] = [];

      clientSocket.on('high_frequency_test', (data: any) => {
        receivedMessages.push(data);
      });

      const startTime = Date.now();

      for (let i = 0; i < messageCount; i++) {
        clientSocket.emit('high_frequency_test', {
          index: i,
          timestamp: Date.now()
        });
      }

      await new Promise<void>((resolve) => {
        const checkInterval = setInterval(() => {
          if (receivedMessages.length === messageCount) {
            clearInterval(checkInterval);
            const endTime = Date.now();
            const duration = endTime - startTime;

            expect(duration).toBeLessThan(1000); // Should complete within 1 second
            expect(receivedMessages.length).toBe(messageCount);
            resolve();
          }
        }, 10);
      });
    });

    it('should handle multiple concurrent connections', async () => {
      const connectionCount = 10;
      const clients: any[] = [];

      // Create multiple connections
      for (let i = 0; i < connectionCount; i++) {
        const client = require('socket.io-client')(
          `http://localhost:${(httpServer.address() as any).port}`,
          {
            auth: {
              token: `test-token-${i}`
            }
          }
        );

        clients.push(client);
      }

      // Wait for all connections to establish
      await new Promise<void>((resolve) => {
        let connectedCount = 0;

        clients.forEach((client, index) => {
          client.on('connect', () => {
            connectedCount++;
            if (connectedCount === connectionCount) {
              resolve();
            }
          });
        });
      });

      // All connections should be established
      clients.forEach(client => {
        expect(client.connected).toBe(true);
        client.disconnect();
      });
    });
  });

  describe('Security', () => {
    it('should rate limit WebSocket connections', async () => {
      const rapidConnections = 20;
      const rejectedConnections = [];

      for (let i = 0; i < rapidConnections; i++) {
        const client = require('socket.io-client')(
          `http://localhost:${(httpServer.address() as any).port}`,
          {
            auth: {
              token: `rapid-test-${i}`
            }
          }
        );

        client.on('connect_error', (error: any) => {
          rejectedConnections.push(error);
        });
      }

      // Allow time for connection attempts
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Some connections should be rejected due to rate limiting
      expect(rejectedConnections.length).toBeGreaterThan(0);
    });

    it('should validate message origins', async () => {
      const maliciousClient = require('socket.io-client')(
        `http://localhost:${(httpServer.address() as any).port}`,
        {
          auth: {
            token: 'malicious-token'
          },
          extraHeaders: {
            'x-forwarded-for': 'suspicious-ip-address'
          }
        }
      );

      await new Promise<void>((resolve) => {
        maliciousClient.on('connect_error', (error: any) => {
          expect(error.message).toContain('rejected');
          maliciousClient.disconnect();
          resolve();
        });
      });
    });
  });
});