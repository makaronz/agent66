import React, { useState } from 'react';
import { Smartphone, AlertCircle, Check, Phone } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { supabase } from '../../lib/supabase';

interface SMSSetupProps {
  enabled: boolean;
  onStatusChange: () => void;
}

const SMSSetup: React.FC<SMSSetupProps> = ({ enabled, onStatusChange }) => {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [verificationCode, setVerificationCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<'initial' | 'setup' | 'verify'>('initial');
  const [maskedPhone, setMaskedPhone] = useState('');

  const formatPhoneNumber = (value: string) => {
    // Remove all non-digits
    const digits = value.replace(/\D/g, '');
    
    // Format as +1 (XXX) XXX-XXXX for US numbers
    if (digits.length <= 10) {
      if (digits.length >= 6) {
        return `+1 (${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
      } else if (digits.length >= 3) {
        return `+1 (${digits.slice(0, 3)}) ${digits.slice(3)}`;
      } else {
        return `+1 (${digits}`;
      }
    }
    return `+1 (${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6, 10)}`;
  };

  const startSetup = async () => {
    const digits = phoneNumber.replace(/\D/g, '');
    if (digits.length !== 10) {
      toast.error('Please enter a valid 10-digit phone number');
      return;
    }

    setLoading(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        toast.error('Please log in to set up SMS verification');
        return;
      }

      const response = await fetch('/api/sms/setup', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ phoneNumber: `+1${digits}` })
      });

      if (response.ok) {
        const data = await response.json();
        setMaskedPhone(data.maskedPhone);
        setStep('verify');
        toast.success('Verification code sent to your phone');
      } else {
        const error = await response.json();
        toast.error(error.message || 'Failed to send verification code');
      }
    } catch (error) {
      console.error('Error starting SMS setup:', error);
      toast.error('Error sending verification code');
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
        toast.error('Please log in to verify SMS');
        return;
      }

      const response = await fetch('/api/sms/verify-setup', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ code: verificationCode })
      });

      if (response.ok) {
        toast.success('SMS verification enabled successfully!');
        setStep('initial');
        setPhoneNumber('');
        setVerificationCode('');
        setMaskedPhone('');
        onStatusChange();
      } else {
        const error = await response.json();
        toast.error(error.message || 'Invalid verification code');
      }
    } catch (error) {
      console.error('Error verifying SMS:', error);
      toast.error('Error verifying SMS code');
    } finally {
      setLoading(false);
    }
  };

  const resendCode = async () => {
    setLoading(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        toast.error('Please log in to resend code');
        return;
      }

      const response = await fetch('/api/sms/resend', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`
        }
      });

      if (response.ok) {
        toast.success('New verification code sent');
      } else {
        const error = await response.json();
        toast.error(error.message || 'Failed to resend code');
      }
    } catch (error) {
      console.error('Error resending code:', error);
      toast.error('Error resending verification code');
    } finally {
      setLoading(false);
    }
  };

  const disableSMS = async () => {
    if (!confirm('Are you sure you want to disable SMS verification? This will reduce your account security.')) {
      return;
    }

    setLoading(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        toast.error('Please log in to disable SMS verification');
        return;
      }

      const response = await fetch('/api/sms/disable', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`
        }
      });

      if (response.ok) {
        toast.success('SMS verification disabled');
        onStatusChange();
      } else {
        const error = await response.json();
        toast.error(error.message || 'Failed to disable SMS verification');
      }
    } catch (error) {
      console.error('Error disabling SMS:', error);
      toast.error('Error disabling SMS verification');
    } finally {
      setLoading(false);
    }
  };

  const handlePhoneChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const formatted = formatPhoneNumber(e.target.value);
    setPhoneNumber(formatted);
  };

  const handleCodeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.replace(/\D/g, '').slice(0, 6);
    setVerificationCode(value);
  };

  if (step === 'setup') {
    return (
      <div className="space-y-6">
        <div className="text-center">
          <Phone className="h-12 w-12 text-blue-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Set up SMS Verification</h3>
          <p className="text-gray-600">Enter your phone number to receive verification codes</p>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Phone Number
            </label>
            <input
              type="tel"
              value={phoneNumber}
              onChange={handlePhoneChange}
              placeholder="+1 (555) 123-4567"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <p className="text-xs text-gray-500 mt-1">US phone numbers only</p>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-start space-x-3">
              <AlertCircle className="h-5 w-5 text-blue-600 mt-0.5" />
              <div className="text-sm text-blue-800">
                <p className="font-medium mb-1">Important:</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>Standard SMS rates may apply</li>
                  <li>Keep your phone accessible during login</li>
                  <li>Codes expire after 10 minutes</li>
                </ul>
              </div>
            </div>
          </div>

          <div className="flex space-x-3">
            <button
              onClick={() => {
                setStep('initial');
                setPhoneNumber('');
              }}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={startSetup}
              disabled={loading || phoneNumber.replace(/\D/g, '').length !== 10}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? 'Sending...' : 'Send Code'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (step === 'verify') {
    return (
      <div className="space-y-6">
        <div className="text-center">
          <Smartphone className="h-12 w-12 text-blue-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Verify Your Phone</h3>
          <p className="text-gray-600">
            We sent a 6-digit code to {maskedPhone}
          </p>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Enter verification code:
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

          <div className="text-center">
            <button
              onClick={resendCode}
              disabled={loading}
              className="text-sm text-blue-600 hover:text-blue-800 disabled:opacity-50"
            >
              Didn't receive a code? Resend
            </button>
          </div>

          <div className="flex space-x-3">
            <button
              onClick={() => {
                setStep('initial');
                setPhoneNumber('');
                setVerificationCode('');
                setMaskedPhone('');
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
        <Smartphone className="h-12 w-12 text-blue-600 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">SMS Verification</h3>
        <p className="text-gray-600">
          Receive verification codes via text message
        </p>
      </div>

      {enabled ? (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-center space-x-3">
            <Check className="h-5 w-5 text-green-600" />
            <div>
              <h4 className="text-sm font-medium text-green-800">SMS Verification Enabled</h4>
              <p className="text-sm text-green-700">You'll receive codes on your registered phone</p>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-center space-x-3">
            <AlertCircle className="h-5 w-5 text-yellow-600" />
            <div>
              <h4 className="text-sm font-medium text-yellow-800">SMS Verification Disabled</h4>
              <p className="text-sm text-yellow-700">Add your phone number for SMS-based authentication</p>
            </div>
          </div>
        </div>
      )}

      <div className="space-y-4">
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="font-medium text-gray-900 mb-2">How SMS verification works:</h4>
          <ul className="text-sm text-gray-600 space-y-1">
            <li>• Enter your phone number once during setup</li>
            <li>• Receive 6-digit codes via text message</li>
            <li>• Enter the code when logging in</li>
            <li>• Works on any phone that can receive SMS</li>
          </ul>
        </div>

        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
          <div className="flex items-start space-x-3">
            <AlertCircle className="h-5 w-5 text-amber-600 mt-0.5" />
            <div className="text-sm text-amber-800">
              <p className="font-medium mb-1">Security Note:</p>
              <p>SMS is less secure than authenticator apps or hardware keys. Consider using those methods for better protection.</p>
            </div>
          </div>
        </div>

        <div className="flex space-x-3">
          {enabled ? (
            <button
              onClick={disableSMS}
              disabled={loading}
              className="flex-1 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? 'Disabling...' : 'Disable SMS'}
            </button>
          ) : (
            <button
              onClick={() => setStep('setup')}
              disabled={loading}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Set up SMS Verification
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default SMSSetup;