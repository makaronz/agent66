import { Server as SocketIOServer } from 'socket.io';
import { Server as HTTPServer } from 'http';
import { logger } from '../utils/logger';
import jwt from 'jsonwebtoken';
import { config } from '../config/env-validation';

interface AuthenticatedSocket {
  userId: string;
  email: string;
}

export class WebSocketServer {
  private io: SocketIOServer;
  private connectedClients: Map<string, AuthenticatedSocket> = new Map();

  constructor(httpServer: HTTPServer) {
    this.io = new SocketIOServer(httpServer, {
      cors: {
        origin: config.cors.origin,
        methods: ['GET', 'POST'],
        credentials: true
      },
      transports: ['websocket', 'polling']
    });

    this.initializeMiddleware();
    this.initializeEventHandlers();
    logger.info('🔌 WebSocket server initialized');
  }

  private initializeMiddleware(): void {
    // Authentication middleware
    this.io.use(async (socket, next) => {
      try {
        const token = socket.handshake.auth.token || socket.handshake.headers.authorization?.replace('Bearer ', '');

        if (!token) {
          return next(new Error('Authentication token required'));
        }

        const decoded = jwt.verify(token, config.jwt.secret) as any;
        socket.userId = decoded.userId;
        socket.email = decoded.email;

        next();
      } catch (error) {
        logger.error('WebSocket authentication failed:', error);
        next(new Error('Invalid authentication token'));
      }
    });
  }

  private initializeEventHandlers(): void {
    this.io.on('connection', (socket) => {
      const clientInfo: AuthenticatedSocket = {
        userId: socket.userId,
        email: socket.email
      };

      this.connectedClients.set(socket.id, clientInfo);
      logger.info(`👤 Client connected: ${clientInfo.email} (${socket.id})`);

      // Join user-specific room
      socket.join(`user_${clientInfo.userId}`);

      // Handle time entry updates
      socket.on('time_entry:start', (data) => {
        socket.broadcast.emit('time_entry:started', {
          userId: clientInfo.userId,
          ...data,
          timestamp: new Date().toISOString()
        });
      });

      socket.on('time_entry:stop', (data) => {
        socket.broadcast.emit('time_entry:stopped', {
          userId: clientInfo.userId,
          ...data,
          timestamp: new Date().toISOString()
        });
      });

      // Handle project updates
      socket.on('project:update', (data) => {
        socket.to(`project_${data.projectId}`).emit('project:updated', {
          ...data,
          updatedBy: clientInfo.userId,
          timestamp: new Date().toISOString()
        });
      });

      // Handle location updates (for GPS tracking)
      socket.on('location:update', (data) => {
        socket.to(`crew_${data.crewId}`).emit('location:updated', {
          userId: clientInfo.userId,
          ...data,
          timestamp: new Date().toISOString()
        });
      });

      // Handle disconnection
      socket.on('disconnect', (reason) => {
        this.connectedClients.delete(socket.id);
        logger.info(`👤 Client disconnected: ${clientInfo.email} (${socket.id}) - ${reason}`);
      });

      // Error handling
      socket.on('error', (error) => {
        logger.error(`Socket error for ${clientInfo.email}:`, error);
      });
    });
  }

  // Public methods for broadcasting
  public broadcastToUser(userId: string, event: string, data: any): void {
    this.io.to(`user_${userId}`).emit(event, data);
  }

  public broadcastToProject(projectId: string, event: string, data: any): void {
    this.io.to(`project_${projectId}`).emit(event, data);
  }

  public broadcastToCrew(crewId: string, event: string, data: any): void {
    this.io.to(`crew_${crewId}`).emit(event, data);
  }

  public getConnectedClients(): Map<string, AuthenticatedSocket> {
    return new Map(this.connectedClients);
  }

  public async close(): Promise<void> {
    return new Promise((resolve) => {
      this.io.close(() => {
        logger.info('🔌 WebSocket server closed');
        resolve();
      });
    });
  }
}