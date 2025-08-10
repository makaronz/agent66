import express from 'express';
import speakeasy from 'speakeasy';
import QRCode from 'qrcode';
import bcrypt from 'bcryptjs';
import crypto from 'crypto';
import supabase from '../lib/supabase.js';
import { authenticateToken } from '../middleware/auth.js';
import { logMFAAction } from '../services/mfaAuditService.js';

const router = express.Router();

// Generate TOTP secret and QR code
router.post('/totp/setup', authenticateToken, async (req, res) => {
  try {
    const userId = req.user?.id;
    if (!userId) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    // Generate TOTP secret
    const secret = speakeasy.generateSecret({
      name: `SMC Trading Agent (${req.user.email})`,
      issuer: 'SMC Trading Agent',
      length: 32
    });

    // Generate QR code
    const qrCodeUrl = await QRCode.toDataURL(secret.otpauth_url!);

    // Store the secret temporarily (not enabled yet)
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

    await logMFAAction(userId, 'setup', 'totp', true, req.ip, req.get('User-Agent'));

    res.json({
      secret: secret.base32,
      qrCode: qrCodeUrl,
      manualEntryKey: secret.base32
    });
  } catch (error) {
    console.error('TOTP setup error:', error);
    await logMFAAction(req.user?.id, 'setup', 'totp', false, req.ip, req.get('User-Agent'));
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

    // Get the stored secret
    const { data: mfaData, error: fetchError } = await supabase
      .from('user_mfa_methods')
      .select('totp_secret')
      .eq('user_id', userId)
      .single();

    if (fetchError || !mfaData?.totp_secret) {
      await logMFAAction(userId, 'verify', 'totp', false, req.ip, req.get('User-Agent'));
      return res.status(400).json({ error: 'TOTP not set up' });
    }

    // Verify the token
    const verified = speakeasy.totp.verify({
      secret: mfaData.totp_secret,
      encoding: 'base32',
      token: token,
      window: 2 // Allow 2 time steps before/after
    });

    if (!verified) {
      await logMFAAction(userId, 'verify', 'totp', false, req.ip, req.get('User-Agent'));
      return res.status(400).json({ error: 'Invalid TOTP token' });
    }

    // Enable TOTP
    const { error: updateError } = await supabase
      .from('user_mfa_methods')
      .update({ totp_enabled: true })
      .eq('user_id', userId);

    if (updateError) {
      console.error('Error enabling TOTP:', updateError);
      await logMFAAction(userId, 'verify', 'totp', false, req.ip, req.get('User-Agent'));
      return res.status(500).json({ error: 'Failed to enable TOTP' });
    }

    await logMFAAction(userId, 'verify', 'totp', true, req.ip, req.get('User-Agent'));
    res.json({ success: true, message: 'TOTP enabled successfully' });
  } catch (error) {
    console.error('TOTP verification error:', error);
    await logMFAAction(req.user?.id, 'verify', 'totp', false, req.ip, req.get('User-Agent'));
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Disable TOTP
router.post('/totp/disable', authenticateToken, async (req, res) => {
  try {
    const { token } = req.body;
    const userId = req.user?.id;

    if (!userId || !token) {
      return res.status(400).json({ error: 'Missing required fields' });
    }

    // Get the stored secret
    const { data: mfaData, error: fetchError } = await supabase
      .from('user_mfa_methods')
      .select('totp_secret, totp_enabled')
      .eq('user_id', userId)
      .single();

    if (fetchError || !mfaData?.totp_secret || !mfaData.totp_enabled) {
      return res.status(400).json({ error: 'TOTP not enabled' });
    }

    // Verify the token before disabling
    const verified = speakeasy.totp.verify({
      secret: mfaData.totp_secret,
      encoding: 'base32',
      token: token,
      window: 2
    });

    if (!verified) {
      await logMFAAction(userId, 'disable', 'totp', false, req.ip, req.get('User-Agent'));
      return res.status(400).json({ error: 'Invalid TOTP token' });
    }

    // Disable TOTP
    const { error: updateError } = await supabase
      .from('user_mfa_methods')
      .update({ 
        totp_enabled: false,
        totp_secret: null
      })
      .eq('user_id', userId);

    if (updateError) {
      console.error('Error disabling TOTP:', updateError);
      await logMFAAction(userId, 'disable', 'totp', false, req.ip, req.get('User-Agent'));
      return res.status(500).json({ error: 'Failed to disable TOTP' });
    }

    await logMFAAction(userId, 'disable', 'totp', true, req.ip, req.get('User-Agent'));
    res.json({ success: true, message: 'TOTP disabled successfully' });
  } catch (error) {
    console.error('TOTP disable error:', error);
    await logMFAAction(req.user?.id, 'disable', 'totp', false, req.ip, req.get('User-Agent'));
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Generate backup codes
router.post('/backup-codes/generate', authenticateToken, async (req, res) => {
  try {
    const userId = req.user?.id;
    if (!userId) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    // Generate 8 backup codes
    const backupCodes = [];
    const hashedCodes = [];

    for (let i = 0; i < 8; i++) {
      const code = crypto.randomBytes(4).toString('hex').toUpperCase();
      const hashedCode = await bcrypt.hash(code, 12);
      backupCodes.push(code);
      hashedCodes.push({
        user_id: userId,
        code_hash: hashedCode
      });
    }

    // Delete existing backup codes
    await supabase
      .from('user_backup_codes')
      .delete()
      .eq('user_id', userId);

    // Insert new backup codes
    const { error: insertError } = await supabase
      .from('user_backup_codes')
      .insert(hashedCodes);

    if (insertError) {
      console.error('Error storing backup codes:', insertError);
      return res.status(500).json({ error: 'Failed to generate backup codes' });
    }

    // Update MFA methods table
    const { error: updateError } = await supabase
      .from('user_mfa_methods')
      .upsert({
        user_id: userId,
        backup_codes_enabled: true
      });

    if (updateError) {
      console.error('Error updating MFA methods:', updateError);
    }

    await logMFAAction(userId, 'setup', 'backup_code', true, req.ip, req.get('User-Agent'));
    res.json({ backupCodes });
  } catch (error) {
    console.error('Backup codes generation error:', error);
    await logMFAAction(req.user?.id, 'setup', 'backup_code', false, req.ip, req.get('User-Agent'));
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Verify backup code
router.post('/backup-codes/verify', authenticateToken, async (req, res) => {
  try {
    const { code } = req.body;
    const userId = req.user?.id;

    if (!userId || !code) {
      return res.status(400).json({ error: 'Missing required fields' });
    }

    // Get all unused backup codes for the user
    const { data: backupCodes, error: fetchError } = await supabase
      .from('user_backup_codes')
      .select('id, code_hash')
      .eq('user_id', userId)
      .eq('used', false)
      .gt('expires_at', new Date().toISOString());

    if (fetchError || !backupCodes?.length) {
      await logMFAAction(userId, 'verify', 'backup_code', false, req.ip, req.get('User-Agent'));
      return res.status(400).json({ error: 'No valid backup codes found' });
    }

    // Check if the provided code matches any of the stored hashes
    let matchedCodeId = null;
    for (const backupCode of backupCodes) {
      const isMatch = await bcrypt.compare(code, backupCode.code_hash);
      if (isMatch) {
        matchedCodeId = backupCode.id;
        break;
      }
    }

    if (!matchedCodeId) {
      await logMFAAction(userId, 'verify', 'backup_code', false, req.ip, req.get('User-Agent'));
      return res.status(400).json({ error: 'Invalid backup code' });
    }

    // Mark the backup code as used
    const { error: updateError } = await supabase
      .from('user_backup_codes')
      .update({ 
        used: true,
        used_at: new Date().toISOString()
      })
      .eq('id', matchedCodeId);

    if (updateError) {
      console.error('Error marking backup code as used:', updateError);
      await logMFAAction(userId, 'verify', 'backup_code', false, req.ip, req.get('User-Agent'));
      return res.status(500).json({ error: 'Failed to verify backup code' });
    }

    await logMFAAction(userId, 'backup_used', 'backup_code', true, req.ip, req.get('User-Agent'));
    res.json({ success: true, message: 'Backup code verified successfully' });
  } catch (error) {
    console.error('Backup code verification error:', error);
    await logMFAAction(req.user?.id, 'verify', 'backup_code', false, req.ip, req.get('User-Agent'));
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get MFA status
router.get('/status', authenticateToken, async (req, res) => {
  try {
    const userId = req.user?.id;
    if (!userId) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { data: mfaData, error } = await supabase
      .from('user_mfa_methods')
      .select('totp_enabled, webauthn_enabled, backup_codes_enabled, sms_enabled')
      .eq('user_id', userId)
      .single();

    if (error && error.code !== 'PGRST116') { // PGRST116 = no rows returned
      console.error('Error fetching MFA status:', error);
      return res.status(500).json({ error: 'Failed to fetch MFA status' });
    }

    const status = mfaData || {
      totp_enabled: false,
      webauthn_enabled: false,
      backup_codes_enabled: false,
      sms_enabled: false
    };

    // Count remaining backup codes
    const { count: remainingBackupCodes } = await supabase
      .from('user_backup_codes')
      .select('*', { count: 'exact', head: true })
      .eq('user_id', userId)
      .eq('used', false)
      .gt('expires_at', new Date().toISOString());

    res.json({
      ...status,
      remainingBackupCodes: remainingBackupCodes || 0
    });
  } catch (error) {
    console.error('MFA status error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;