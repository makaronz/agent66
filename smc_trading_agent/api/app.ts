/**
 * This is a API server
 */

import express, { type Request, type Response, type NextFunction } from 'express';
import cors from 'cors';
import dotenv from 'dotenv';

// load env
dotenv.config();


const app: express.Application = express();

app.use(cors({
  origin: ['http://localhost:3000', 'http://localhost:5173'],
  credentials: true
}));
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

/**
 * Import trading routes
 */
import tradingRoutes from './routes/trading';
import spawnRoutes from './routes/spawn';
import serenaSpawnRoutes from './routes/serenaSpawn';

/**
 * API Routes
 */
app.use('/api/trading', tradingRoutes);
app.use('/api/spawn', spawnRoutes);
app.use('/api/serena-spawn', serenaSpawnRoutes);

app.use('/api/auth', (req, res) => {
  console.log('Auth route accessed');
  res.json({ message: 'Auth endpoint' });
});

/**
 * health
 */
app.use('/api/health', (req: Request, res: Response): void => {
  res.status(200).json({
    success: true,
    message: 'ok'
  });
});

/**
 * error handler middleware
 */
app.use((error: Error, req: Request, res: Response, next: NextFunction) => {
  res.status(500).json({
    success: false,
    error: 'Server internal error'
  });
});

/**
 * 404 handler
 */
app.use((req: Request, res: Response) => {
  res.status(404).json({
    success: false,
    error: 'API not found'
  });
});

export default app;