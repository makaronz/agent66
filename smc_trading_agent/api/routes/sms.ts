import express from 'express';
import crypto from 'crypto';
import supabase from '../lib/supabase.js';
import { authenticateToken } from '../middleware/auth.js';
import { logMFAAction } from '../services/mfaAuditService.js';

const router = express.Router();

// Twilio configuration (optional - can be replaced with other SMS providers)
let twilioClient: any = null;
if (process.env.TWILIO_ACCOUNT_SID && process.env.TWILIO_AUTH_TOKEN) {
  try {
    const twilio = require('twilio');
    twilioClient = twilio(process.env.TWILIO_ACCOUNT_SID, process.env.TWILIO_AUTH_TOKEN);
  } catch (error) {
    console.warn('Twilio not configured or not available:', error.message);
  }
}

// Store SMS codes temporarily (in production, use Redis or similar)
const smsCodeStore = new Map<string, { code: string; expires: number; phone: string }>();

// Clean up expired codes every 5 minutes
setInterval(() => {
  const now = Date.now();
  for (const [key, value] of smsCodeStore.entries()) {
    if (value.expires < now) {
      smsCodeStore.delete(key);
    }
  }
}, 5 * 60 * 1000);

// Setup SMS MFA
router.post('/setup', authenticateToken, async (req, res) => {
  try {
    const { phoneNumber } = req.body;
    const userId = req.user?.id;

    if (!userId || !phoneNumber) {
      return res.status(400).json({ error: 'Missing required fields' });
    }

    // Validate phone number format (basic validation)
    const phoneRegex = /^\+[1-9]\d{1,14}$/;
    if (!phoneRegex.test(phoneNumber)) {
      return res.status(400).json({ error: 'Invalid phone number format. Use international format (+1234567890)' });
    }

    // Generate verification code
    const verificationCode = crypto.randomInt(100000, 999999).toString();
    const codeKey = `${userId}-setup`;
    const expires = Date.now() + (10 * 60 * 1000); // 10 minutes

    // Store the code temporarily
    smsCodeStore.set(codeKey, {
      code: verificationCode,
      expires,
      phone: phoneNumber
    });

    // Send SMS (if Twilio is configured)
    let smsSent = false;
    if (twilioClient && process.env.TWILIO_PHONE_NUMBER) {
      try {
        await twilioClient.messages.create({
          body: `Your SMC Trading Agent verification code is: ${verificationCode}. This code expires in 10 minutes.`,
          from: process.env.TWILIO_PHONE_NUMBER,
          to: phoneNumber
        });
        smsSent = true;
      } catch (error) {
        console.error('SMS sending error:', error);
        await logMFAAction(userId, 'setup', 'sms', false, req.ip, req.get('User-Agent'));
        return res.status(500).json({ error: 'Failed to send SMS verification code' });
      }
    }

    if (!smsSent) {
      // For development/testing - return the code in response
      console.log(`SMS verification code for ${phoneNumber}: ${verificationCode}`);
      return res.json({ 
        message: 'SMS MFA setup initiated',
        developmentCode: process.env.NODE_ENV === 'development' ? verificationCode : undefined
      });
    }

    res.json({ message: 'Verification code sent to your phone' });
  } catch (error) {
    console.error('SMS MFA setup error:', error);
    await logMFAAction(req.user?.id, 'setup', 'sms', false, req.ip, req.get('User-Agent'));
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Verify SMS setup
router.post('/verify-setup', authenticateToken, async (req, res) => {
  try {
    const { code } = req.body;
    const userId = req.user?.id;

    if (!userId || !code) {
      return res.status(400).json({ error: 'Missing required fields' });
    }

    const codeKey = `${userId}-setup`;
    const storedData = smsCodeStore.get(codeKey);

    if (!storedData) {
      await logMFAAction(userId, 'verify', 'sms', false, req.ip, req.get('User-Agent'));
      return res.status(400).json({ error: 'No verification code found or code expired' });
    }

    if (storedData.expires < Date.now()) {
      smsCodeStore.delete(codeKey);
      await logMFAAction(userId, 'verify', 'sms', false, req.ip, req.get('User-Agent'));
      return res.status(400).json({ error: 'Verification code expired' });
    }

    if (storedData.code !== code) {
      await logMFAAction(userId, 'verify', 'sms', false, req.ip, req.get('User-Agent'));
      return res.status(400).json({ error: 'Invalid verification code' });
    }

    // Enable SMS MFA
    const { error } = await supabase
      .from('user_mfa_methods')
      .upsert({
        user_id: userId,
        sms_enabled: true,
        sms_phone_number: storedData.phone
      });

    if (error) {
      console.error('Error enabling SMS MFA:', error);
      await logMFAAction(userId, 'verify', 'sms', false, req.ip, req.get('User-Agent'));
      return res.status(500).json({ error: 'Failed to enable SMS MFA' });
    }

    // Clean up the verification code
    smsCodeStore.delete(codeKey);

    await logMFAAction(userId, 'verify', 'sms', true, req.ip, req.get('User-Agent'));
    res.json({ success: true, message: 'SMS MFA enabled successfully' });
  } catch (error) {
    console.error('SMS MFA verification error:', error);
    await logMFAAction(req.user?.id, 'verify', 'sms', false, req.ip, req.get('User-Agent'));
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Send SMS verification code for authentication
router.post('/send-code', authenticateToken, async (req, res) => {
  try {
    const userId = req.user?.id;

    if (!userId) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    // Get user's phone number
    const { data: mfaData, error: fetchError } = await supabase
      .from('user_mfa_methods')
      .select('sms_enabled, sms_phone_number')
      .eq('user_id', userId)
      .single();

    if (fetchError || !mfaData?.sms_enabled || !mfaData?.sms_phone_number) {
      return res.status(400).json({ error: 'SMS MFA not enabled' });
    }

    // Generate verification code
    const verificationCode = crypto.randomInt(100000, 999999).toString();
    const codeKey = `${userId}-auth`;
    const expires = Date.now() + (5 * 60 * 1000); // 5 minutes for auth codes

    // Store the code temporarily
    smsCodeStore.set(codeKey, {
      code: verificationCode,
      expires,
      phone: mfaData.sms_phone_number
    });

    // Send SMS (if Twilio is configured)
    let smsSent = false;
    if (twilioClient && process.env.TWILIO_PHONE_NUMBER) {
      try {
        await twilioClient.messages.create({
          body: `Your SMC Trading Agent login code is: ${verificationCode}. This code expires in 5 minutes.`,
          from: process.env.TWILIO_PHONE_NUMBER,
          to: mfaData.sms_phone_number
        });
        smsSent = true;
      } catch (error) {
        console.error('SMS sending error:', error);
        return res.status(500).json({ error: 'Failed to send SMS verification code' });
      }
    }

    if (!smsSent) {
      // For development/testing - return the code in response
      console.log(`SMS auth code for ${mfaData.sms_phone_number}: ${verificationCode}`);
      return res.json({ 
        message: 'SMS verification code sent',
        developmentCode: process.env.NODE_ENV === 'development' ? verificationCode : undefined
      });
    }

    res.json({ message: 'Verification code sent to your phone' });
  } catch (error) {
    console.error('SMS code sending error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Verify SMS authentication code
router.post('/verify-code', authenticateToken, async (req, res) => {
  try {
    const { code } = req.body;
    const userId = req.user?.id;

    if (!userId || !code) {
      return res.status(400).json({ error: 'Missing required fields' });
    }

    const codeKey = `${userId}-auth`;
    const storedData = smsCodeStore.get(codeKey);

    if (!storedData) {
      await logMFAAction(userId, 'verify', 'sms', false, req.ip, req.get('User-Agent'));
      return res.status(400).json({ error: 'No verification code found or code expired' });
    }

    if (storedData.expires < Date.now()) {
      smsCodeStore.delete(codeKey);
      await logMFAAction(userId, 'verify', 'sms', false, req.ip, req.get('User-Agent'));
      return res.status(400).json({ error: 'Verification code expired' });
    }

    if (storedData.code !== code) {
      await logMFAAction(userId, 'verify', 'sms', false, req.ip, req.get('User-Agent'));
      return res.status(400).json({ error: 'Invalid verification code' });
    }

    // Clean up the verification code
    smsCodeStore.delete(codeKey);

    await logMFAAction(userId, 'verify', 'sms', true, req.ip, req.get('User-Agent'));
    res.json({ success: true, message: 'SMS verification successful' });
  } catch (error) {
    console.error('SMS verification error:', error);
    await logMFAAction(req.user?.id, 'verify', 'sms', false, req.ip, req.get('User-Agent'));
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Disable SMS MFA
router.post('/disable', authenticateToken, async (req, res) => {
  try {
    const { code } = req.body;
    const userId = req.user?.id;

    if (!userId || !code) {
      return res.status(400).json({ error: 'Missing required fields' });
    }

    // Verify the code before disabling
    const codeKey = `${userId}-auth`;
    const storedData = smsCodeStore.get(codeKey);

    if (!storedData || storedData.code !== code || storedData.expires < Date.now()) {
      await logMFAAction(userId, 'disable', 'sms', false, req.ip, req.get('User-Agent'));
      return res.status(400).json({ error: 'Invalid or expired verification code' });
    }

    // Disable SMS MFA
    const { error } = await supabase
      .from('user_mfa_methods')
      .update({
        sms_enabled: false,
        sms_phone_number: null
      })
      .eq('user_id', userId);

    if (error) {
      console.error('Error disabling SMS MFA:', error);
      await logMFAAction(userId, 'disable', 'sms', false, req.ip, req.get('User-Agent'));
      return res.status(500).json({ error: 'Failed to disable SMS MFA' });
    }

    // Clean up the verification code
    smsCodeStore.delete(codeKey);

    await logMFAAction(userId, 'disable', 'sms', true, req.ip, req.get('User-Agent'));
    res.json({ success: true, message: 'SMS MFA disabled successfully' });
  } catch (error) {
    console.error('SMS MFA disable error:', error);
    await logMFAAction(req.user?.id, 'disable', 'sms', false, req.ip, req.get('User-Agent'));
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;