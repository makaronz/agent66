import supabase from '../lib/supabase.js';

export interface MFAAction {
  user_id: string;
  action: 'setup' | 'verify' | 'disable' | 'backup_used';
  method: 'totp' | 'webauthn' | 'sms' | 'backup_code';
  success: boolean;
  ip_address?: string;
  user_agent?: string;
}

export async function logMFAAction(
  userId: string | undefined,
  action: MFAAction['action'],
  method: MFAAction['method'],
  success: boolean,
  ipAddress?: string,
  userAgent?: string
): Promise<void> {
  if (!userId) return;

  try {
    const { error } = await supabase
      .from('mfa_audit_log')
      .insert({
        user_id: userId,
        action,
        method,
        success,
        ip_address: ipAddress,
        user_agent: userAgent
      });

    if (error) {
      console.error('Error logging MFA action:', error);
    }
  } catch (error) {
    console.error('MFA audit logging error:', error);
  }
}

export async function getMFAAuditLog(
  userId: string,
  limit: number = 50,
  offset: number = 0
) {
  try {
    const { data, error } = await supabase
      .from('mfa_audit_log')
      .select('*')
      .eq('user_id', userId)
      .order('created_at', { ascending: false })
      .range(offset, offset + limit - 1);

    if (error) {
      console.error('Error fetching MFA audit log:', error);
      return null;
    }

    return data;
  } catch (error) {
    console.error('MFA audit log fetch error:', error);
    return null;
  }
}

export async function getMFAComplianceReport() {
  try {
    // Get users without any MFA enabled
    const { data: usersWithoutMFA, error: noMFAError } = await supabase
      .from('user_mfa_methods')
      .select('user_id')
      .eq('totp_enabled', false)
      .eq('webauthn_enabled', false)
      .eq('sms_enabled', false);

    if (noMFAError) {
      console.error('Error fetching users without MFA:', noMFAError);
      return null;
    }

    // Get total user count
    const { count: totalUsers, error: countError } = await supabase
      .from('user_mfa_methods')
      .select('*', { count: 'exact', head: true });

    if (countError) {
      console.error('Error counting total users:', countError);
      return null;
    }

    // Get MFA method statistics
    const { data: mfaStats, error: statsError } = await supabase
      .from('user_mfa_methods')
      .select('totp_enabled, webauthn_enabled, sms_enabled, backup_codes_enabled');

    if (statsError) {
      console.error('Error fetching MFA stats:', statsError);
      return null;
    }

    const stats = mfaStats?.reduce(
      (acc, user) => {
        if (user.totp_enabled) acc.totp++;
        if (user.webauthn_enabled) acc.webauthn++;
        if (user.sms_enabled) acc.sms++;
        if (user.backup_codes_enabled) acc.backupCodes++;
        return acc;
      },
      { totp: 0, webauthn: 0, sms: 0, backupCodes: 0 }
    ) || { totp: 0, webauthn: 0, sms: 0, backupCodes: 0 };

    return {
      totalUsers: totalUsers || 0,
      usersWithoutMFA: usersWithoutMFA?.length || 0,
      complianceRate: totalUsers ? ((totalUsers - (usersWithoutMFA?.length || 0)) / totalUsers) * 100 : 0,
      methodStats: stats
    };
  } catch (error) {
    console.error('MFA compliance report error:', error);
    return null;
  }
}