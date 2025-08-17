import jwt from 'jsonwebtoken';
import { Request, Response, NextFunction } from 'express';
import { getSupabaseAdmin } from '../supabase';
import { getVaultClient, getJwtSecret } from '../lib/vault-client';
import { auditAuth } from './audit';

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
      await auditAuth.loginFailure(req, 'No token provided');
      res.status(401).json({ error: 'Access token required' });
      return;
    }

    try {
      // First try Supabase authentication
      const supabaseAdmin = await getSupabaseAdmin();
      const { data: { user }, error } = await supabaseAdmin.auth.getUser(token);

      if (!error && user) {
        // Add user info to request
        req.user = {
          id: user.id,
          email: user.email || '',
          role: user.role
        };

        await auditAuth.loginSuccess(req);
        next();
        return;
      }
    } catch (supabaseError) {
      console.warn('Supabase authentication failed, trying JWT fallback:', supabaseError);
    }

    // Fallback to JWT verification using Vault secret
    try {
      const jwtSecret = await getJwtSecret();
      const decoded = jwt.verify(token, jwtSecret) as any;

      // Add user info to request from JWT payload
      req.user = {
        id: decoded.sub || decoded.userId,
        email: decoded.email,
        role: decoded.role
      };

      await auditAuth.loginSuccess(req);
      next();
    } catch (jwtError) {
      console.error('JWT verification failed:', jwtError);
      await auditAuth.loginFailure(req, 'Invalid token');
      res.status(403).json({ error: 'Invalid or expired token' });
    }

  } catch (error) {
    console.error('Authentication error:', error);
    await auditAuth.loginFailure(req, 'Authentication system error');
    res.status(500).json({ error: 'Authentication system error' });
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
    const supabaseAdmin = await getSupabaseAdmin();
    const { data: mfaData, error } = await supabaseAdmin
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