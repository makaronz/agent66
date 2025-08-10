import jwt from 'jsonwebtoken';
import { Request, Response, NextFunction } from 'express';
import supabase from '../lib/supabase.js';

export interface AuthenticatedRequest extends Request {
  user?: {
    id: string;
    email: string;
    role?: string;
  };
}

export async function authenticateToken(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const authHeader = req.headers.authorization;
    const token = authHeader && authHeader.split(' ')[1]; // Bearer TOKEN

    if (!token) {
      res.status(401).json({ error: 'Access token required' });
      return;
    }

    // Verify the token with Supabase
    const { data: { user }, error } = await supabase.auth.getUser(token);

    if (error || !user) {
      res.status(403).json({ error: 'Invalid or expired token' });
      return;
    }

    // Add user info to request
    req.user = {
      id: user.id,
      email: user.email || '',
      role: user.role
    };

    next();
  } catch (error) {
    console.error('Authentication error:', error);
    res.status(403).json({ error: 'Invalid token' });
  }
}

export async function requireMFA(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const userId = req.user?.id;
    if (!userId) {
      res.status(401).json({ error: 'Unauthorized' });
      return;
    }

    // Check if user has any MFA method enabled
    const { data: mfaData, error } = await supabase
      .from('user_mfa_methods')
      .select('totp_enabled, webauthn_enabled, sms_enabled')
      .eq('user_id', userId)
      .single();

    if (error && error.code !== 'PGRST116') {
      console.error('Error checking MFA status:', error);
      res.status(500).json({ error: 'Failed to verify MFA status' });
      return;
    }

    const hasMFA = mfaData && (
      mfaData.totp_enabled ||
      mfaData.webauthn_enabled ||
      mfaData.sms_enabled
    );

    if (!hasMFA) {
      res.status(403).json({ 
        error: 'MFA required',
        message: 'Multi-factor authentication must be enabled to access this resource'
      });
      return;
    }

    next();
  } catch (error) {
    console.error('MFA check error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
}

export async function verifyMFAToken(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const { mfaToken, mfaMethod } = req.body;
    const userId = req.user?.id;

    if (!userId || !mfaToken || !mfaMethod) {
      res.status(400).json({ error: 'MFA token and method required' });
      return;
    }

    // This middleware can be used to verify MFA tokens for sensitive operations
    // The actual verification logic would depend on the MFA method
    // For now, we'll just pass through - specific verification should be done in route handlers
    
    next();
  } catch (error) {
    console.error('MFA token verification error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
}