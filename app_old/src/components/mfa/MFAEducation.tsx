import React from 'react';
import { Shield, Lock, Smartphone, Key, AlertTriangle, CheckCircle, Users, TrendingUp } from 'lucide-react';

const MFAEducation: React.FC = () => {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="text-center">
        <Shield className="h-16 w-16 text-blue-600 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Why Multi-Factor Authentication Matters</h2>
        <p className="text-lg text-gray-600">
          Protect your trading account with multiple layers of security
        </p>
      </div>

      {/* Security Statistics */}
      <div className="bg-gradient-to-r from-red-50 to-orange-50 border border-red-200 rounded-lg p-6">
        <div className="flex items-start space-x-4">
          <AlertTriangle className="h-8 w-8 text-red-600 mt-1" />
          <div>
            <h3 className="text-lg font-semibold text-red-900 mb-3">The Reality of Cyber Threats</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div className="bg-white rounded-lg p-4 border border-red-200">
                <div className="text-2xl font-bold text-red-600 mb-1">99.9%</div>
                <div className="text-red-800">of compromised accounts lack MFA protection</div>
              </div>
              <div className="bg-white rounded-lg p-4 border border-red-200">
                <div className="text-2xl font-bold text-red-600 mb-1">$4.45M</div>
                <div className="text-red-800">average cost of a data breach in 2023</div>
              </div>
              <div className="bg-white rounded-lg p-4 border border-red-200">
                <div className="text-2xl font-bold text-red-600 mb-1">300%</div>
                <div className="text-red-800">increase in financial fraud since 2020</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* How MFA Works */}
      <div className="bg-blue-50 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-blue-900 mb-4 flex items-center">
          <Lock className="h-5 w-5 mr-2" />
          How Multi-Factor Authentication Works
        </h3>
        <div className="space-y-4">
          <p className="text-blue-800">
            MFA requires multiple forms of verification before granting access to your account:
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white rounded-lg p-4 border border-blue-200">
              <div className="text-center">
                <div className="bg-blue-100 rounded-full w-12 h-12 flex items-center justify-center mx-auto mb-3">
                  <span className="text-blue-600 font-bold">1</span>
                </div>
                <h4 className="font-medium text-blue-900 mb-2">Something You Know</h4>
                <p className="text-sm text-blue-700">Your password or PIN</p>
              </div>
            </div>
            <div className="bg-white rounded-lg p-4 border border-blue-200">
              <div className="text-center">
                <div className="bg-blue-100 rounded-full w-12 h-12 flex items-center justify-center mx-auto mb-3">
                  <span className="text-blue-600 font-bold">2</span>
                </div>
                <h4 className="font-medium text-blue-900 mb-2">Something You Have</h4>
                <p className="text-sm text-blue-700">Your phone or security key</p>
              </div>
            </div>
            <div className="bg-white rounded-lg p-4 border border-blue-200">
              <div className="text-center">
                <div className="bg-blue-100 rounded-full w-12 h-12 flex items-center justify-center mx-auto mb-3">
                  <span className="text-blue-600 font-bold">3</span>
                </div>
                <h4 className="font-medium text-blue-900 mb-2">Something You Are</h4>
                <p className="text-sm text-blue-700">Biometrics (future feature)</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* MFA Methods Comparison */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-900">Choose the Right MFA Method for You</h3>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Authenticator Apps */}
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <div className="flex items-center space-x-3 mb-4">
              <Smartphone className="h-6 w-6 text-green-600" />
              <h4 className="font-semibold text-gray-900">Authenticator Apps (TOTP)</h4>
              <span className="bg-green-100 text-green-800 text-xs px-2 py-1 rounded-full">Recommended</span>
            </div>
            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <CheckCircle className="h-4 w-4 text-green-600" />
                <span className="text-sm text-gray-700">Works offline</span>
              </div>
              <div className="flex items-center space-x-2">
                <CheckCircle className="h-4 w-4 text-green-600" />
                <span className="text-sm text-gray-700">Very secure</span>
              </div>
              <div className="flex items-center space-x-2">
                <CheckCircle className="h-4 w-4 text-green-600" />
                <span className="text-sm text-gray-700">Free to use</span>
              </div>
              <div className="flex items-center space-x-2">
                <CheckCircle className="h-4 w-4 text-green-600" />
                <span className="text-sm text-gray-700">Phishing resistant</span>
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-3">
              Popular apps: Google Authenticator, Authy, Microsoft Authenticator
            </p>
          </div>

          {/* Hardware Keys */}
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <div className="flex items-center space-x-3 mb-4">
              <Key className="h-6 w-6 text-blue-600" />
              <h4 className="font-semibold text-gray-900">Hardware Security Keys</h4>
              <span className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full">Most Secure</span>
            </div>
            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <CheckCircle className="h-4 w-4 text-green-600" />
                <span className="text-sm text-gray-700">Highest security</span>
              </div>
              <div className="flex items-center space-x-2">
                <CheckCircle className="h-4 w-4 text-green-600" />
                <span className="text-sm text-gray-700">Phishing proof</span>
              </div>
              <div className="flex items-center space-x-2">
                <CheckCircle className="h-4 w-4 text-green-600" />
                <span className="text-sm text-gray-700">No battery needed</span>
              </div>
              <div className="flex items-center space-x-2">
                <AlertTriangle className="h-4 w-4 text-yellow-600" />
                <span className="text-sm text-gray-700">Requires purchase (~$25-50)</span>
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-3">
              Popular brands: YubiKey, Google Titan, SoloKeys
            </p>
          </div>

          {/* SMS */}
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <div className="flex items-center space-x-3 mb-4">
              <Smartphone className="h-6 w-6 text-yellow-600" />
              <h4 className="font-semibold text-gray-900">SMS Verification</h4>
              <span className="bg-yellow-100 text-yellow-800 text-xs px-2 py-1 rounded-full">Convenient</span>
            </div>
            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <CheckCircle className="h-4 w-4 text-green-600" />
                <span className="text-sm text-gray-700">Easy to set up</span>
              </div>
              <div className="flex items-center space-x-2">
                <CheckCircle className="h-4 w-4 text-green-600" />
                <span className="text-sm text-gray-700">Works on any phone</span>
              </div>
              <div className="flex items-center space-x-2">
                <AlertTriangle className="h-4 w-4 text-yellow-600" />
                <span className="text-sm text-gray-700">Vulnerable to SIM swapping</span>
              </div>
              <div className="flex items-center space-x-2">
                <AlertTriangle className="h-4 w-4 text-yellow-600" />
                <span className="text-sm text-gray-700">Requires cell service</span>
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-3">
              Best used as a backup method alongside stronger options
            </p>
          </div>

          {/* Backup Codes */}
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <div className="flex items-center space-x-3 mb-4">
              <Lock className="h-6 w-6 text-purple-600" />
              <h4 className="font-semibold text-gray-900">Backup Recovery Codes</h4>
              <span className="bg-purple-100 text-purple-800 text-xs px-2 py-1 rounded-full">Essential</span>
            </div>
            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <CheckCircle className="h-4 w-4 text-green-600" />
                <span className="text-sm text-gray-700">Emergency access</span>
              </div>
              <div className="flex items-center space-x-2">
                <CheckCircle className="h-4 w-4 text-green-600" />
                <span className="text-sm text-gray-700">Works offline</span>
              </div>
              <div className="flex items-center space-x-2">
                <AlertTriangle className="h-4 w-4 text-yellow-600" />
                <span className="text-sm text-gray-700">One-time use only</span>
              </div>
              <div className="flex items-center space-x-2">
                <AlertTriangle className="h-4 w-4 text-yellow-600" />
                <span className="text-sm text-gray-700">Must be stored securely</span>
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-3">
              Critical for account recovery when other methods fail
            </p>
          </div>
        </div>
      </div>

      {/* Trading-Specific Security */}
      <div className="bg-gradient-to-r from-green-50 to-blue-50 border border-green-200 rounded-lg p-6">
        <div className="flex items-start space-x-4">
          <TrendingUp className="h-8 w-8 text-green-600 mt-1" />
          <div>
            <h3 className="text-lg font-semibold text-green-900 mb-3">Why MFA is Critical for Trading</h3>
            <div className="space-y-3 text-sm text-green-800">
              <div className="flex items-start space-x-2">
                <CheckCircle className="h-4 w-4 text-green-600 mt-0.5" />
                <span>Protect your trading capital from unauthorized access</span>
              </div>
              <div className="flex items-start space-x-2">
                <CheckCircle className="h-4 w-4 text-green-600 mt-0.5" />
                <span>Prevent malicious trades that could wipe out your account</span>
              </div>
              <div className="flex items-start space-x-2">
                <CheckCircle className="h-4 w-4 text-green-600 mt-0.5" />
                <span>Secure your API keys and trading strategies</span>
              </div>
              <div className="flex items-start space-x-2">
                <CheckCircle className="h-4 w-4 text-green-600 mt-0.5" />
                <span>Comply with financial security regulations</span>
              </div>
              <div className="flex items-start space-x-2">
                <CheckCircle className="h-4 w-4 text-green-600 mt-0.5" />
                <span>Maintain audit trails for tax and compliance purposes</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Best Practices */}
      <div className="bg-gray-50 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
          <Users className="h-5 w-5 mr-2" />
          MFA Best Practices
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h4 className="font-medium text-gray-900 mb-2">✅ Do:</h4>
            <ul className="text-sm text-gray-700 space-y-1">
              <li>• Enable multiple MFA methods</li>
              <li>• Use authenticator apps over SMS when possible</li>
              <li>• Keep backup codes in a secure location</li>
              <li>• Test your MFA methods regularly</li>
              <li>• Update your methods if devices are lost/stolen</li>
              <li>• Use hardware keys for high-value accounts</li>
            </ul>
          </div>
          <div>
            <h4 className="font-medium text-gray-900 mb-2">❌ Don't:</h4>
            <ul className="text-sm text-gray-700 space-y-1">
              <li>• Rely on SMS as your only MFA method</li>
              <li>• Share your MFA codes with anyone</li>
              <li>• Store backup codes on the same device</li>
              <li>• Ignore MFA prompts you didn't initiate</li>
              <li>• Use the same device for all MFA methods</li>
              <li>• Disable MFA for convenience</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Call to Action */}
      <div className="bg-blue-600 text-white rounded-lg p-6 text-center">
        <Shield className="h-12 w-12 mx-auto mb-4" />
        <h3 className="text-xl font-semibold mb-2">Secure Your Trading Account Today</h3>
        <p className="mb-4">
          Don't wait until it's too late. Enable MFA now to protect your investments and trading strategies.
        </p>
        <p className="text-sm opacity-90">
          Start with an authenticator app, add backup codes, and consider a hardware key for maximum security.
        </p>
      </div>
    </div>
  );
};

export default MFAEducation;