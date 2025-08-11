import React, { useState, useEffect } from 'react';
import { Key, Shield, AlertCircle, Check, Trash2 } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { supabase } from '../../supabase';
import { startRegistration, startAuthentication } from '@simplewebauthn/browser';

interface WebAuthnSetupProps {
  enabled: boolean;
  onStatusChange: () => void;
}

interface WebAuthnCredential {
  id: string;
  name: string;
  created_at: string;
}

const WebAuthnSetup: React.FC<WebAuthnSetupProps> = ({ enabled, onStatusChange }) => {
  const [credentials, setCredentials] = useState<WebAuthnCredential[]>([]);
  const [loading, setLoading] = useState(false);
  const [credentialName, setCredentialName] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);

  useEffect(() => {
    if (enabled) {
      fetchCredentials();
    }
  }, [enabled]);

  const fetchCredentials = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;

      const response = await fetch('/api/webauthn/credentials', {
        headers: {
          'Authorization': `Bearer ${session.access_token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setCredentials(data.credentials || []);
      }
    } catch (error) {
      console.error('Error fetching credentials:', error);
    }
  };

  const startRegistrationProcess = async () => {
    if (!credentialName.trim()) {
      toast.error('Please enter a name for your security key');
      return;
    }

    setLoading(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        toast.error('Please log in to register a security key');
        return;
      }

      // Get registration options from server
      const optionsResponse = await fetch('/api/webauthn/register/begin', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ credentialName: credentialName.trim() })
      });

      if (!optionsResponse.ok) {
        const error = await optionsResponse.json();
        toast.error(error.message || 'Failed to start registration');
        return;
      }

      const options = await optionsResponse.json();

      // Start WebAuthn registration
      const attResp = await startRegistration(options);

      // Send response to server for verification
      const verificationResponse = await fetch('/api/webauthn/register/finish', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          credential: attResp,
          credentialName: credentialName.trim()
        })
      });

      if (verificationResponse.ok) {
        toast.success('Security key registered successfully!');
        setCredentialName('');
        setShowAddForm(false);
        onStatusChange();
        fetchCredentials();
      } else {
        const error = await verificationResponse.json();
        toast.error(error.message || 'Failed to register security key');
      }
    } catch (error: any) {
      console.error('WebAuthn registration error:', error);
      if (error.name === 'NotSupportedError') {
        toast.error('WebAuthn is not supported on this device or browser');
      } else if (error.name === 'SecurityError') {
        toast.error('Security error: Please ensure you\'re using HTTPS');
      } else if (error.name === 'NotAllowedError') {
        toast.error('Registration was cancelled or timed out');
      } else {
        toast.error('Failed to register security key');
      }
    } finally {
      setLoading(false);
    }
  };

  const removeCredential = async (credentialId: string) => {
    if (!confirm('Are you sure you want to remove this security key?')) {
      return;
    }

    setLoading(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        toast.error('Please log in to remove security key');
        return;
      }

      const response = await fetch(`/api/webauthn/credentials/${credentialId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${session.access_token}`
        }
      });

      if (response.ok) {
        toast.success('Security key removed successfully');
        fetchCredentials();
        onStatusChange();
      } else {
        const error = await response.json();
        toast.error(error.message || 'Failed to remove security key');
      }
    } catch (error) {
      console.error('Error removing credential:', error);
      toast.error('Error removing security key');
    } finally {
      setLoading(false);
    }
  };

  const testAuthentication = async () => {
    setLoading(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        toast.error('Please log in to test authentication');
        return;
      }

      // Get authentication options
      const optionsResponse = await fetch('/api/webauthn/authenticate/begin', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`
        }
      });

      if (!optionsResponse.ok) {
        const error = await optionsResponse.json();
        toast.error(error.message || 'Failed to start authentication test');
        return;
      }

      const options = await optionsResponse.json();

      // Start WebAuthn authentication
      const authResp = await startAuthentication(options);

      // Verify authentication
      const verificationResponse = await fetch('/api/webauthn/authenticate/finish', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ credential: authResp })
      });

      if (verificationResponse.ok) {
        toast.success('Security key authentication successful!');
      } else {
        const error = await verificationResponse.json();
        toast.error(error.message || 'Authentication failed');
      }
    } catch (error: any) {
      console.error('WebAuthn authentication error:', error);
      if (error.name === 'NotAllowedError') {
        toast.error('Authentication was cancelled or timed out');
      } else {
        toast.error('Authentication test failed');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="text-center">
        <Key className="h-12 w-12 text-blue-600 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">Hardware Security Keys</h3>
        <p className="text-gray-600">
          Use WebAuthn-compatible security keys for the strongest authentication
        </p>
      </div>

      {enabled ? (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-center space-x-3">
            <Check className="h-5 w-5 text-green-600" />
            <div>
              <h4 className="text-sm font-medium text-green-800">WebAuthn Enabled</h4>
              <p className="text-sm text-green-700">
                You have {credentials.length} security key{credentials.length !== 1 ? 's' : ''} registered
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-center space-x-3">
            <AlertCircle className="h-5 w-5 text-yellow-600" />
            <div>
              <h4 className="text-sm font-medium text-yellow-800">No Security Keys Registered</h4>
              <p className="text-sm text-yellow-700">Add a security key for the strongest protection</p>
            </div>
          </div>
        </div>
      )}

      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="font-medium text-gray-900 mb-2">What are security keys?</h4>
        <ul className="text-sm text-gray-600 space-y-1">
          <li>• Physical devices that provide the strongest authentication</li>
          <li>• Resistant to phishing and man-in-the-middle attacks</li>
          <li>• Works with USB, NFC, or Bluetooth</li>
          <li>• Supports FIDO2/WebAuthn standards</li>
        </ul>
      </div>

      {/* Registered Credentials */}
      {credentials.length > 0 && (
        <div className="space-y-4">
          <h4 className="font-medium text-gray-900">Registered Security Keys</h4>
          <div className="space-y-2">
            {credentials.map((credential) => (
              <div key={credential.id} className="flex items-center justify-between p-3 bg-white border border-gray-200 rounded-lg">
                <div className="flex items-center space-x-3">
                  <Shield className="h-5 w-5 text-green-600" />
                  <div>
                    <div className="font-medium text-gray-900">{credential.name}</div>
                    <div className="text-sm text-gray-500">
                      Added {new Date(credential.created_at).toLocaleDateString()}
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => removeCredential(credential.id)}
                  disabled={loading}
                  className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                  title="Remove security key"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>

          <button
            onClick={testAuthentication}
            disabled={loading}
            className="w-full px-4 py-2 border border-blue-600 text-blue-600 rounded-md hover:bg-blue-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Testing...' : 'Test Authentication'}
          </button>
        </div>
      )}

      {/* Add New Credential */}
      <div className="space-y-4">
        {showAddForm ? (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Security Key Name
              </label>
              <input
                type="text"
                value={credentialName}
                onChange={(e) => setCredentialName(e.target.value)}
                placeholder="e.g., YubiKey 5, Work Laptop Key"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                maxLength={50}
              />
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-start space-x-3">
                <AlertCircle className="h-5 w-5 text-blue-600 mt-0.5" />
                <div className="text-sm text-blue-800">
                  <p className="font-medium mb-1">Ready to register your security key?</p>
                  <p>Make sure your security key is connected and ready. You'll be prompted to touch or activate it.</p>
                </div>
              </div>
            </div>

            <div className="flex space-x-3">
              <button
                onClick={() => {
                  setShowAddForm(false);
                  setCredentialName('');
                }}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={startRegistrationProcess}
                disabled={loading || !credentialName.trim()}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? 'Registering...' : 'Register Key'}
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setShowAddForm(true)}
            disabled={loading}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Add Security Key
          </button>
        )}
      </div>
    </div>
  );
};

export default WebAuthnSetup;