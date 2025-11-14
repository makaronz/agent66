import React, { useState, useEffect } from 'react';
import { QrCode, Smartphone, Copy, Check, AlertCircle } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { supabase } from '../../supabase';
import LazyImage from '../LazyImage';

interface TOTPSetupProps {
  enabled: boolean;
  onStatusChange: () => void;
}

interface TOTPSetupData {
  secret: string;
  qrCodeUrl: string;
  backupCodes: string[];
}

const TOTPSetup: React.FC<TOTPSetupProps> = ({ enabled, onStatusChange }) => {
  const [setupData, setSetupData] = useState<TOTPSetupData | null>(null);
  const [verificationCode, setVerificationCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<'initial' | 'setup' | 'verify'>('initial');
  const [copied, setCopied] = useState(false);

  const startSetup = async () => {
    setLoading(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        toast.error('Please log in to set up TOTP');
        return;
      }

      const response = await fetch('/api/mfa/totp/setup', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        setSetupData(data);
        setStep('setup');
      } else {
        const error = await response.json();
        toast.error(error.message || 'Failed to start TOTP setup');
      }
    } catch (error) {
      console.error('Error starting TOTP setup:', error);
      toast.error('Error starting TOTP setup');
    } finally {
      setLoading(false);
    }
  };

  const verifySetup = async () => {
    if (!verificationCode || verificationCode.length !== 6) {
      toast.error('Please enter a valid 6-digit code');
      return;
    }

    setLoading(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        toast.error('Please log in to verify TOTP');
        return;
      }

      const response = await fetch('/api/mfa/totp/verify', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ token: verificationCode })
      });

      if (response.ok) {
        toast.success('TOTP authentication enabled successfully!');
        setStep('initial');
        setSetupData(null);
        setVerificationCode('');
        onStatusChange();
      } else {
        const error = await response.json();
        toast.error(error.message || 'Invalid verification code');
      }
    } catch (error) {
      console.error('Error verifying TOTP:', error);
      toast.error('Error verifying TOTP code');
    } finally {
      setLoading(false);
    }
  };

  const disableTOTP = async () => {
    if (!confirm('Are you sure you want to disable TOTP authentication? This will reduce your account security.')) {
      return;
    }

    setLoading(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        toast.error('Please log in to disable TOTP');
        return;
      }

      const response = await fetch('/api/mfa/totp/disable', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`
        }
      });

      if (response.ok) {
        toast.success('TOTP authentication disabled');
        onStatusChange();
      } else {
        const error = await response.json();
        toast.error(error.message || 'Failed to disable TOTP');
      }
    } catch (error) {
      console.error('Error disabling TOTP:', error);
      toast.error('Error disabling TOTP');
    } finally {
      setLoading(false);
    }
  };

  const copySecret = async () => {
    if (setupData?.secret) {
      await navigator.clipboard.writeText(setupData.secret);
      setCopied(true);
      toast.success('Secret key copied to clipboard');
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleCodeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.replace(/\D/g, '').slice(0, 6);
    setVerificationCode(value);
  };

  if (step === 'setup' && setupData) {
    return (
      <div className="space-y-6">
        <div className="text-center">
          <Smartphone className="h-12 w-12 text-blue-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Set up Authenticator App</h3>
          <p className="text-gray-600">Scan the QR code or enter the secret key manually</p>
        </div>

        <div className="bg-gray-50 rounded-lg p-6">
          <div className="text-center mb-4">
            <div className="bg-white p-4 rounded-lg inline-block">
              <LazyImage 
                src={setupData.qrCodeUrl} 
                alt="TOTP QR Code" 
                className="w-48 h-48 mx-auto"
              />
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Or enter this secret key manually:
              </label>
              <div className="flex items-center space-x-2">
                <input
                  type="text"
                  value={setupData.secret}
                  readOnly
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md bg-gray-50 text-sm font-mono"
                />
                <button
                  onClick={copySecret}
                  className="px-3 py-2 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
                >
                  {copied ? <Check className="h-4 w-4 text-green-600" /> : <Copy className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-start space-x-3">
                <AlertCircle className="h-5 w-5 text-blue-600 mt-0.5" />
                <div className="text-sm text-blue-800">
                  <p className="font-medium mb-1">Instructions:</p>
                  <ol className="list-decimal list-inside space-y-1">
                    <li>Install an authenticator app (Google Authenticator, Authy, etc.)</li>
                    <li>Scan the QR code or enter the secret key</li>
                    <li>Enter the 6-digit code from your app below</li>
                  </ol>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Enter verification code from your authenticator app:
            </label>
            <input
              type="text"
              value={verificationCode}
              onChange={handleCodeChange}
              placeholder="000000"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-center text-lg font-mono tracking-widest"
              maxLength={6}
            />
          </div>

          <div className="flex space-x-3">
            <button
              onClick={() => {
                setStep('initial');
                setSetupData(null);
                setVerificationCode('');
              }}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={verifySetup}
              disabled={loading || verificationCode.length !== 6}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? 'Verifying...' : 'Verify & Enable'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <QrCode className="h-12 w-12 text-blue-600 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">Authenticator App (TOTP)</h3>
        <p className="text-gray-600">
          Use an authenticator app to generate time-based verification codes
        </p>
      </div>

      {enabled ? (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-center space-x-3">
            <Check className="h-5 w-5 text-green-600" />
            <div>
              <h4 className="text-sm font-medium text-green-800">TOTP Authentication Enabled</h4>
              <p className="text-sm text-green-700">Your account is protected with authenticator app codes</p>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-center space-x-3">
            <AlertCircle className="h-5 w-5 text-yellow-600" />
            <div>
              <h4 className="text-sm font-medium text-yellow-800">TOTP Authentication Disabled</h4>
              <p className="text-sm text-yellow-700">Enable TOTP for enhanced account security</p>
            </div>
          </div>
        </div>
      )}

      <div className="space-y-4">
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="font-medium text-gray-900 mb-2">How it works:</h4>
          <ul className="text-sm text-gray-600 space-y-1">
            <li>• Install an authenticator app on your phone</li>
            <li>• Scan a QR code to link your account</li>
            <li>• Enter 6-digit codes when logging in</li>
            <li>• Works offline and is very secure</li>
          </ul>
        </div>

        <div className="flex space-x-3">
          {enabled ? (
            <button
              onClick={disableTOTP}
              disabled={loading}
              className="flex-1 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? 'Disabling...' : 'Disable TOTP'}
            </button>
          ) : (
            <button
              onClick={startSetup}
              disabled={loading}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? 'Setting up...' : 'Set up TOTP'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default TOTPSetup;