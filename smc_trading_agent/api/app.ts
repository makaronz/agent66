/**
 * This is a API server
 */

import express, { type Request, type Response } from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import binanceRoutes from './routes/binance.js';
import userRoutes from './routes/users.js';
import mfaRoutes from './routes/mfa.js';
import webauthnRoutes from './routes/webauthn.js';
import smsRoutes from './routes/sms.js';
import securityRoutes from './routes/security.js';

// load env
dotenv.config();


const app: express.Application = express();

app.use(cors());
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

/**
 * API Routes
 */
app.use('/api/auth', (req, res) => {
  console.log('Auth route accessed');
  res.json({ message: 'Auth endpoint' });
});

app.use('/api/binance', binanceRoutes);
app.use('/api/users', userRoutes);
app.use('/api/mfa', mfaRoutes);
app.use('/api/webauthn', webauthnRoutes);
app.use('/api/sms', smsRoutes);
app.use('/api/security', securityRoutes);

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
app.use((error: Error, req: Request, res: Response) => {
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