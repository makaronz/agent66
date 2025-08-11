import React, { useState, useEffect } from 'react';
import { Shield, Smartphone, Key, MessageSquare, FileText, BookOpen, Activity, CheckCircle, AlertTriangle, Clock } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { supabase } from '../supabase';
import TOTPSetup from '../components/mfa/TOTPSetup';
import WebAuthnSetup from '../components/mfa/WebAuthnSetup';
import SMSSetup from '../components/mfa/SMSSetup';
import BackupCodes from '../components/mfa/BackupCodes';
import MFAEducation from '../components/mfa/MFAEducation';
import SecurityDashboard from '../components/mfa/SecurityDashboard';

interface MFAStatus {
  totp_enabled: boolean;
  webauthn_enabled: boolean;
  sms_enabled: boolean;
  backup_codes_enabled: boolean;
  remainingBackupCodes: number;
}

const MFASettings: React.FC = () => {
  const [mfaStatus, setMFAStatus] = useState<MFAStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'totp' | 'webauthn' | 'sms' | 'backup' | 'security' | 'education'>('totp');

  useEffect(() => {
    fetchMFAStatus();
  }, []);

  const fetchMFAStatus = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        toast.error('Please log in to access MFA settings');
        return;
      }

      const response = await fetch('/api/mfa/status', {
        headers: {
          'Authorization': `Bearer ${session.access_token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setMFAStatus(data);
      } else {
        toast.error('Failed to fetch MFA status');
      }
    } catch (error) {
      console.error('Error fetching MFA status:', error);
      toast.error('Error loading MFA settings');
    } finally {
      setLoading(false);
    }
  };

  const refreshMFAStatus = () => {
    fetchMFAStatus();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const enabledMethods = mfaStatus ? [
    mfaStatus.totp_enabled && 'Authenticator App',
    mfaStatus.webauthn_enabled && 'Hardware Key',
    mfaStatus.sms_enabled && 'SMS',
    mfaStatus.backup_codes_enabled && 'Backup Codes'
  ].filter(Boolean).length : 0;

  const securityLevel = enabledMethods === 0 ? 'Low' : enabledMethods === 1 ? 'Medium' : 'High';
  const securityColor = enabledMethods === 0 ? 'text-red-600' : enabledMethods === 1 ? 'text-yellow-600' : 'text-green-600';

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Shield className="h-8 w-8 text-blue-600" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Multi-Factor Authentication</h1>
                <p className="text-gray-600">Secure your account with additional verification methods</p>
              </div>
            </div>
            <div className="text-right">
              <div className="text-sm text-gray-500">Security Level</div>
              <div className={`text-lg font-semibold ${securityColor}`}>{securityLevel}</div>
              <div className="text-xs text-gray-400">{enabledMethods} method{enabledMethods !== 1 ? 's' : ''} enabled</div>
            </div>
          </div>
        </div>

        {/* Security Alert */}
        {enabledMethods === 0 && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <div className="flex items-start space-x-3">
              <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5" />
              <div>
                <h3 className="text-sm font-medium text-red-800">Security Warning</h3>
                <p className="text-sm text-red-700 mt-1">
                  Your account is not protected by multi-factor authentication. Enable at least one MFA method to secure your trading account.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* MFA Methods Overview */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className={`bg-white rounded-lg p-4 border-2 ${mfaStatus?.totp_enabled ? 'border-green-200 bg-green-50' : 'border-gray-200'}`}>
            <div className="flex items-center justify-between">
              <Smartphone className="h-6 w-6 text-blue-600" />
              {mfaStatus?.totp_enabled && <CheckCircle className="h-5 w-5 text-green-600" />}
            </div>
            <h3 className="font-medium text-gray-900 mt-2">Authenticator App</h3>
            <p className="text-sm text-gray-600">TOTP codes from your phone</p>
          </div>

          <div className={`bg-white rounded-lg p-4 border-2 ${mfaStatus?.webauthn_enabled ? 'border-green-200 bg-green-50' : 'border-gray-200'}`}>
            <div className="flex items-center justify-between">
              <Key className="h-6 w-6 text-blue-600" />
              {mfaStatus?.webauthn_enabled && <CheckCircle className="h-5 w-5 text-green-600" />}
            </div>
            <h3 className="font-medium text-gray-900 mt-2">Hardware Key</h3>
            <p className="text-sm text-gray-600">WebAuthn/FIDO2 devices</p>
          </div>

          <div className={`bg-white rounded-lg p-4 border-2 ${mfaStatus?.sms_enabled ? 'border-green-200 bg-green-50' : 'border-gray-200'}`}>
            <div className="flex items-center justify-between">
              <Smartphone className="h-6 w-6 text-blue-600" />
              {mfaStatus?.sms_enabled && <CheckCircle className="h-5 w-5 text-green-600" />}
            </div>
            <h3 className="font-medium text-gray-900 mt-2">SMS Verification</h3>
            <p className="text-sm text-gray-600">Codes sent to your phone</p>
          </div>

          <div className={`bg-white rounded-lg p-4 border-2 ${mfaStatus?.backup_codes_enabled ? 'border-green-200 bg-green-50' : 'border-gray-200'}`}>
            <div className="flex items-center justify-between">
              <FileText className="h-6 w-6 text-blue-600" />
              {mfaStatus?.backup_codes_enabled && <CheckCircle className="h-5 w-5 text-green-600" />}
            </div>
            <h3 className="font-medium text-gray-900 mt-2">Backup Codes</h3>
            <p className="text-sm text-gray-600">
              {mfaStatus?.remainingBackupCodes || 0} codes remaining
            </p>
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-lg shadow-sm">
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8 px-6">
              {[
                { id: 'totp', label: 'Authenticator App', icon: Smartphone },
                { id: 'webauthn', label: 'Hardware Key', icon: Key },
                { id: 'sms', label: 'SMS', icon: MessageSquare },
                { id: 'backup', label: 'Backup Codes', icon: FileText },
                { id: 'security', label: 'Security Dashboard', icon: Activity },
                { id: 'education', label: 'Learn More', icon: BookOpen }
              ].map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => setActiveTab(id as any)}
                  className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 ${
                    activeTab === id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{label}</span>
                </button>
              ))}
            </nav>
          </div>

          <div className="p-6">
            {activeTab === 'totp' && (
              <TOTPSetup 
                enabled={mfaStatus?.totp_enabled || false}
                onStatusChange={refreshMFAStatus}
              />
            )}
            {activeTab === 'webauthn' && (
              <WebAuthnSetup 
                enabled={mfaStatus?.webauthn_enabled || false}
                onStatusChange={refreshMFAStatus}
              />
            )}
            {activeTab === 'sms' && (
              <SMSSetup 
                enabled={mfaStatus?.sms_enabled || false}
                onStatusChange={refreshMFAStatus}
              />
            )}
            {activeTab === 'backup' && (
              <BackupCodes 
                enabled={mfaStatus?.backup_codes_enabled || false}
                remainingCodes={mfaStatus?.remainingBackupCodes || 0}
                onStatusChange={refreshMFAStatus}
              />
            )}
            {activeTab === 'security' && <SecurityDashboard />}
            {activeTab === 'education' && <MFAEducation />}
          </div>
        </div>
      </div>
    </div>
  );
};

export default MFASettings;