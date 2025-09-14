import React, { useState } from 'react';
import { Download, RefreshCw, AlertTriangle, Check, Copy, Eye, EyeOff } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { supabase } from '../../supabase';

interface BackupCodesProps {
  enabled: boolean;
  remainingCodes: number;
  onStatusChange: () => void;
}

const BackupCodes: React.FC<BackupCodesProps> = ({ enabled, remainingCodes, onStatusChange }) => {
  const [backupCodes, setBackupCodes] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [showCodes, setShowCodes] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const generateBackupCodes = async () => {
    if (enabled && !confirm('Generating new backup codes will invalidate your existing codes. Continue?')) {
      return;
    }

    setLoading(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        toast.error('Please log in to generate backup codes');
        return;
      }

      const response = await fetch('/api/mfa/backup-codes/generate', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setBackupCodes(data.codes);
        setShowCodes(true);
        toast.success('Backup codes generated successfully!');
        onStatusChange();
      } else {
        const error = await response.json();
        toast.error(error.message || 'Failed to generate backup codes');
      }
    } catch (error) {
      console.error('Error generating backup codes:', error);
      toast.error('Error generating backup codes');
    } finally {
      setLoading(false);
    }
  };

  const copyCode = async (code: string, index: number) => {
    await navigator.clipboard.writeText(code);
    setCopiedIndex(index);
    toast.success('Code copied to clipboard');
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const copyAllCodes = async () => {
    const codesText = backupCodes.join('\n');
    await navigator.clipboard.writeText(codesText);
    toast.success('All codes copied to clipboard');
  };

  const downloadCodes = () => {
    const codesText = [
      'SMC Trading Agent - Backup Recovery Codes',
      '==========================================',
      '',
      'IMPORTANT: Store these codes in a safe place!',
      'Each code can only be used once.',
      '',
      'Generated on: ' + new Date().toLocaleString(),
      '',
      ...backupCodes.map((code, index) => `${index + 1}. ${code}`),
      '',
      'Keep these codes secure and accessible.',
      'You will need them if you lose access to your other MFA methods.'
    ].join('\n');

    const blob = new Blob([codesText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `smc-backup-codes-${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success('Backup codes downloaded');
  };

  const acknowledgeAndClose = () => {
    setShowCodes(false);
    setBackupCodes([]);
  };

  if (showCodes && backupCodes.length > 0) {
    return (
      <div className="space-y-6">
        <div className="text-center">
          <Check className="h-12 w-12 text-green-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Your Backup Codes</h3>
          <p className="text-gray-600">
            Save these codes in a secure location. Each can only be used once.
          </p>
        </div>

        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-start space-x-3">
            <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5" />
            <div className="text-sm text-red-800">
              <p className="font-medium mb-1">Critical Security Information:</p>
              <ul className="list-disc list-inside space-y-1">
                <li>These codes will only be shown once</li>
                <li>Store them in a password manager or secure location</li>
                <li>Each code can only be used once</li>
                <li>Don't share these codes with anyone</li>
              </ul>
            </div>
          </div>
        </div>

        <div className="bg-gray-50 rounded-lg p-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {backupCodes.map((code, index) => (
              <div key={index} className="flex items-center justify-between bg-white p-3 rounded border">
                <span className="font-mono text-sm">{code}</span>
                <button
                  onClick={() => copyCode(code, index)}
                  className="ml-2 p-1 text-gray-500 hover:text-gray-700 transition-colors"
                  title="Copy code"
                >
                  {copiedIndex === index ? (
                    <Check className="h-4 w-4 text-green-600" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </button>
              </div>
            ))}
          </div>
        </div>

        <div className="flex space-x-3">
          <button
            onClick={copyAllCodes}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 transition-colors flex items-center justify-center space-x-2"
          >
            <Copy className="h-4 w-4" />
            <span>Copy All</span>
          </button>
          <button
            onClick={downloadCodes}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 transition-colors flex items-center justify-center space-x-2"
          >
            <Download className="h-4 w-4" />
            <span>Download</span>
          </button>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="text-sm text-blue-800">
            <p className="font-medium mb-2">How to use backup codes:</p>
            <ol className="list-decimal list-inside space-y-1">
              <li>When prompted for MFA during login, select "Use backup code"</li>
              <li>Enter one of these codes exactly as shown</li>
              <li>The code will be consumed and cannot be used again</li>
              <li>Generate new codes when you're running low</li>
            </ol>
          </div>
        </div>

        <button
          onClick={acknowledgeAndClose}
          className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
        >
          I've Saved These Codes Securely
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <RefreshCw className="h-12 w-12 text-blue-600 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">Backup Recovery Codes</h3>
        <p className="text-gray-600">
          One-time use codes for account recovery when other MFA methods aren't available
        </p>
      </div>

      {enabled ? (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-center space-x-3">
            <Check className="h-5 w-5 text-green-600" />
            <div>
              <h4 className="text-sm font-medium text-green-800">Backup Codes Generated</h4>
              <p className="text-sm text-green-700">
                You have {remainingCodes} unused backup code{remainingCodes !== 1 ? 's' : ''} remaining
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-center space-x-3">
            <AlertTriangle className="h-5 w-5 text-yellow-600" />
            <div>
              <h4 className="text-sm font-medium text-yellow-800">No Backup Codes Generated</h4>
              <p className="text-sm text-yellow-700">Generate backup codes for account recovery</p>
            </div>
          </div>
        </div>
      )}

      {remainingCodes <= 2 && remainingCodes > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
          <div className="flex items-start space-x-3">
            <AlertTriangle className="h-5 w-5 text-amber-600 mt-0.5" />
            <div className="text-sm text-amber-800">
              <p className="font-medium mb-1">Running Low on Backup Codes</p>
              <p>You only have {remainingCodes} backup code{remainingCodes !== 1 ? 's' : ''} remaining. Consider generating new ones.</p>
            </div>
          </div>
        </div>
      )}

      <div className="space-y-4">
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="font-medium text-gray-900 mb-2">What are backup codes?</h4>
          <ul className="text-sm text-gray-600 space-y-1">
            <li>• One-time use codes for emergency access</li>
            <li>• Use when you can't access your phone or security key</li>
            <li>• Each code works only once</li>
            <li>• Store them securely offline</li>
          </ul>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start space-x-3">
            <AlertTriangle className="h-5 w-5 text-blue-600 mt-0.5" />
            <div className="text-sm text-blue-800">
              <p className="font-medium mb-1">Security Best Practices:</p>
              <ul className="list-disc list-inside space-y-1">
                <li>Store codes in a password manager</li>
                <li>Keep a printed copy in a secure location</li>
                <li>Don't store codes on the same device you use for login</li>
                <li>Generate new codes if you suspect they're compromised</li>
              </ul>
            </div>
          </div>
        </div>

        <button
          onClick={generateBackupCodes}
          disabled={loading}
          className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center space-x-2"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          <span>
            {loading ? 'Generating...' : enabled ? 'Generate New Codes' : 'Generate Backup Codes'}
          </span>
        </button>
      </div>
    </div>
  );
};

export default BackupCodes;