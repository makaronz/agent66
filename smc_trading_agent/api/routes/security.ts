import express from 'express';
import supabase from '../lib/supabase.js';
import { authenticateToken } from '../middleware/auth.js';
import { logMFAAction } from '../services/mfaAuditService.js';

const router = express.Router();

// Get MFA compliance report
router.get('/mfa-compliance', authenticateToken, async (req, res) => {
  try {
    const userId = req.user?.id;
    if (!userId) {
      return res.status(401).json({ message: 'User not authenticated' });
    }

    // Get user's MFA methods
    const { data: mfaMethods, error: mfaError } = await supabase
      .from('user_mfa_methods')
      .select('*')
      .eq('user_id', userId)
      .single();

    if (mfaError && mfaError.code !== 'PGRST116') {
      console.error('Error fetching MFA methods:', mfaError);
      return res.status(500).json({ message: 'Failed to fetch MFA status' });
    }

    // Count enabled methods
    const enabledMethods = [];
    if (mfaMethods?.totp_enabled) enabledMethods.push('TOTP');
    if (mfaMethods?.webauthn_enabled) enabledMethods.push('WebAuthn');
    if (mfaMethods?.sms_enabled) enabledMethods.push('SMS');
    if (mfaMethods?.backup_codes_enabled) enabledMethods.push('Backup Codes');

    // Determine compliance level
    let complianceLevel = 'low';
    let recommendations = [];

    if (enabledMethods.length === 0) {
      complianceLevel = 'critical';
      recommendations = [
        'Enable at least one MFA method immediately',
        'Start with an authenticator app (TOTP)',
        'Generate backup recovery codes',
        'Consider adding a hardware security key'
      ];
    } else if (enabledMethods.length === 1) {
      complianceLevel = 'medium';
      recommendations = [
        'Add a second MFA method for redundancy',
        'Generate backup recovery codes if not done',
        'Consider upgrading to hardware security keys'
      ];
    } else {
      complianceLevel = 'high';
      recommendations = [
        'Excellent security posture!',
        'Regularly test your MFA methods',
        'Keep backup codes in a secure location'
      ];
    }

    // Get recent MFA activity
    const { data: recentActivity, error: activityError } = await supabase
      .from('mfa_audit_log')
      .select('action, method_type, success, created_at')
      .eq('user_id', userId)
      .order('created_at', { ascending: false })
      .limit(10);

    if (activityError) {
      console.error('Error fetching MFA activity:', activityError);
    }

    res.json({
      complianceLevel,
      enabledMethods,
      methodCount: enabledMethods.length,
      recommendations,
      recentActivity: recentActivity || [],
      lastUpdated: mfaMethods?.last_mfa_update || null
    });

  } catch (error) {
    console.error('Error generating compliance report:', error);
    res.status(500).json({ message: 'Internal server error' });
  }
});

// Get security alerts
router.get('/alerts', authenticateToken, async (req, res) => {
  try {
    const userId = req.user?.id;
    if (!userId) {
      return res.status(401).json({ message: 'User not authenticated' });
    }

    const alerts = [];

    // Check for failed MFA attempts
    const { data: failedAttempts, error: failedError } = await supabase
      .from('mfa_audit_log')
      .select('action, method_type, created_at')
      .eq('user_id', userId)
      .eq('success', false)
      .gte('created_at', new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString())
      .order('created_at', { ascending: false });

    if (!failedError && failedAttempts && failedAttempts.length > 0) {
      alerts.push({
        type: 'warning',
        title: 'Failed MFA Attempts',
        message: `${failedAttempts.length} failed MFA attempt(s) in the last 24 hours`,
        timestamp: failedAttempts[0].created_at,
        severity: failedAttempts.length > 5 ? 'high' : 'medium'
      });
    }

    // Check MFA method status
    const { data: mfaMethods, error: mfaError } = await supabase
      .from('user_mfa_methods')
      .select('*')
      .eq('user_id', userId)
      .single();

    if (!mfaError && mfaMethods) {
      const enabledCount = [
        mfaMethods.totp_enabled,
        mfaMethods.webauthn_enabled,
        mfaMethods.sms_enabled
      ].filter(Boolean).length;

      if (enabledCount === 0) {
        alerts.push({
          type: 'error',
          title: 'No MFA Methods Enabled',
          message: 'Your account is not protected by multi-factor authentication',
          timestamp: new Date().toISOString(),
          severity: 'critical'
        });
      } else if (enabledCount === 1) {
        alerts.push({
          type: 'warning',
          title: 'Single MFA Method',
          message: 'Consider enabling additional MFA methods for better security',
          timestamp: new Date().toISOString(),
          severity: 'medium'
        });
      }

      // Check backup codes
      if (!mfaMethods.backup_codes_enabled) {
        alerts.push({
          type: 'info',
          title: 'No Backup Codes',
          message: 'Generate backup recovery codes for emergency access',
          timestamp: new Date().toISOString(),
          severity: 'low'
        });
      }
    }

    res.json({ alerts });

  } catch (error) {
    console.error('Error fetching security alerts:', error);
    res.status(500).json({ message: 'Internal server error' });
  }
});

// Acknowledge security alert
router.post('/alerts/:alertId/acknowledge', authenticateToken, async (req, res) => {
  try {
    const userId = req.user?.id;
    const { alertId } = req.params;

    if (!userId) {
      return res.status(401).json({ message: 'User not authenticated' });
    }

    // Log the acknowledgment
    await logMFAAction(userId, 'setup', 'totp', true, req.ip, req.get('User-Agent'));

    res.json({ message: 'Alert acknowledged' });

  } catch (error) {
    console.error('Error acknowledging alert:', error);
    res.status(500).json({ message: 'Internal server error' });
  }
});

// Get MFA usage statistics
router.get('/stats', authenticateToken, async (req, res) => {
  try {
    const userId = req.user?.id;
    if (!userId) {
      return res.status(401).json({ message: 'User not authenticated' });
    }

    const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString();

    // Get MFA usage stats for the last 30 days
    const { data: usageStats, error: statsError } = await supabase
      .from('mfa_audit_log')
      .select('method_type, success, created_at')
      .eq('user_id', userId)
      .gte('created_at', thirtyDaysAgo)
      .order('created_at', { ascending: false });

    if (statsError) {
      console.error('Error fetching usage stats:', statsError);
      return res.status(500).json({ message: 'Failed to fetch usage statistics' });
    }

    // Process statistics
    const stats = {
      totalAttempts: usageStats?.length || 0,
      successfulAttempts: usageStats?.filter(s => s.success).length || 0,
      failedAttempts: usageStats?.filter(s => !s.success).length || 0,
      methodUsage: {} as Record<string, number>,
      dailyUsage: {} as Record<string, number>
    };

    // Calculate method usage
    usageStats?.forEach(stat => {
      if (stat.method_type) {
        stats.methodUsage[stat.method_type] = (stats.methodUsage[stat.method_type] || 0) + 1;
      }

      // Calculate daily usage
      const date = new Date(stat.created_at).toISOString().split('T')[0];
      stats.dailyUsage[date] = (stats.dailyUsage[date] || 0) + 1;
    });

    res.json(stats);

  } catch (error) {
    console.error('Error fetching MFA statistics:', error);
    res.status(500).json({ message: 'Internal server error' });
  }
});

export default router;