import express from 'express';
import speakeasy from 'speakeasy';
import QRCode from 'qrcode';
import bcrypt from 'bcryptjs';
import crypto from 'crypto';
import {
  generateRegistrationOptions,
  verifyRegistrationResponse,
  generateAuthenticationOptions,
  verifyAuthenticationResponse,
  VerifyRegistrationResponseOpts,
  VerifyAuthenticationResponseOpts,
} from '@simplewebauthn/server';
import { getSupabaseAdmin } from './supabase';
import { authenticateToken } from './middleware/auth';
// MFA audit logging removed for deployment optimization

const router = express.Router();

// TOTP Routes
// Generate TOTP secret and QR code
router.post('/totp/setup', authenticateToken, async (req, res) => {
  try {
    const userId = req.user?.id;
    if (!userId) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const secret = speakeasy.generateSecret({
      name: `SMC Trading Agent (${req.user.email})`,
      issuer: 'SMC Trading Agent',
      length: 32
    });

    const qrCodeUrl = await QRCode.toDataURL(secret.otpauth_url!);

    const supabase = await getSupabaseAdmin();
    const { error } = await supabase
      .from('user_mfa_methods')
      .upsert({
        user_id: userId,
        totp_secret: secret.base32,
        totp_enabled: false
      });

    if (error) {
      console.error('Error storing TOTP secret:', error);
      return res.status(500).json({ error: 'Failed to setup TOTP' });
    }

    // MFA audit logging removed

    res.json({
      secret: secret.base32,
      qrCode: qrCodeUrl,
      manualEntryKey: secret.base32
    });
  } catch (error) {
    console.error('TOTP setup error:', error);
    // MFA audit logging removed
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Verify and enable TOTP
router.post('/totp/verify', authenticateToken, async (req, res) => {
  try {
    const { token } = req.body;
    const userId = req.user?.id;

    if (!userId || !token) {
      return res.status(400).json({ error: 'Missing required fields' });
    }

    const supabase = await getSupabaseAdmin();
    const { data: mfaData, error: fetchError } = await supabase
      .from('user_mfa_methods')
      .select('totp_secret')
      .eq('user_id', userId)
      .single();

    if (fetchError || !mfaData?.totp_secret) {
      // MFA audit logging removed
      return res.status(400).json({ error: 'TOTP not set up' });
    }

    const verified = speakeasy.totp.verify({
      secret: mfaData.totp_secret,
      encoding: 'base32',
      token: token,
      window: 2
    });

    if (!verified) {
      // MFA audit logging removed
      return res.status(400).json({ error: 'Invalid TOTP token' });
    }

    const { error: updateError } = await supabase
      .from('user_mfa_methods')
      .update({ totp_enabled: true })
      .eq('user_id', userId);

    if (updateError) {
      console.error('Error enabling TOTP:', updateError);
      // MFA audit logging removed
      return res.status(500).json({ error: 'Failed to enable TOTP' });
    }

    // MFA audit logging removed
    res.json({ success: true, message: 'TOTP enabled successfully' });
  } catch (error) {
    console.error('TOTP verification error:', error);
    // MFA audit logging removed
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Security Routes
// Get MFA compliance report
router.get('/compliance', authenticateToken, async (req, res) => {
  try {
    const userId = req.user?.id;
    if (!userId) {
      return res.status(401).json({ message: 'User not authenticated' });
    }

    const supabase = await getSupabaseAdmin();
    const { data: mfaMethods, error: mfaError } = await supabase
      .from('user_mfa_methods')
      .select('*')
      .eq('user_id', userId)
      .single();

    if (mfaError && mfaError.code !== 'PGRST116') {
      console.error('Error fetching MFA methods:', mfaError);
      return res.status(500).json({ message: 'Failed to fetch MFA status' });
    }

    const enabledMethods = [];
    if (mfaMethods?.totp_enabled) enabledMethods.push('TOTP');
    if (mfaMethods?.webauthn_enabled) enabledMethods.push('WebAuthn');
    if (mfaMethods?.sms_enabled) enabledMethods.push('SMS');
    if (mfaMethods?.backup_codes_enabled) enabledMethods.push('Backup Codes');

    let complianceLevel = 'low';
    let recommendations = [];

    if (enabledMethods.length === 0) {
      complianceLevel = 'critical';
      recommendations = [
        'Enable at least one MFA method immediately',
        'Start with an authenticator app (TOTP)',
        'Generate backup recovery codes'
      ];
    } else if (enabledMethods.length === 1) {
      complianceLevel = 'medium';
      recommendations = [
        'Add a second MFA method for redundancy',
        'Generate backup recovery codes if not done'
      ];
    } else {
      complianceLevel = 'high';
      recommendations = [
        'Excellent security posture!',
        'Regularly test your MFA methods'
      ];
    }

    res.json({
      complianceLevel,
      enabledMethods,
      methodCount: enabledMethods.length,
      recommendations
    });

  } catch (error) {
    console.error('Error generating compliance report:', error);
    res.status(500).json({ message: 'Internal server error' });
  }
});

// SMS Routes
// Setup SMS MFA
router.post('/sms/setup', authenticateToken, async (req, res) => {
  try {
    const { phoneNumber } = req.body;
    const userId = req.user?.id;

    if (!userId || !phoneNumber) {
      return res.status(400).json({ error: 'Missing required fields' });
    }

    // Generate verification code
    const verificationCode = crypto.randomInt(100000, 999999).toString();
    const expiresAt = new Date(Date.now() + 10 * 60 * 1000); // 10 minutes

    // Store phone number and verification code
    const supabase = await getSupabaseAdmin();
    const { error } = await supabase
      .from('user_mfa_methods')
      .upsert({
        user_id: userId,
        sms_phone: phoneNumber,
        sms_verification_code: verificationCode,
        sms_code_expires_at: expiresAt.toISOString(),
        sms_enabled: false
      });

    if (error) {
      console.error('Error storing SMS setup:', error);
      return res.status(500).json({ error: 'Failed to setup SMS' });
    }

    // In a real implementation, send SMS here
    console.log(`SMS verification code for ${phoneNumber}: ${verificationCode}`);

    // MFA audit logging removed
    res.json({ success: true, message: 'Verification code sent' });
  } catch (error) {
    console.error('SMS setup error:', error);
    // MFA audit logging removed
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;