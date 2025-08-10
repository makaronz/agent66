import express from 'express';
import {
  generateRegistrationOptions,
  verifyRegistrationResponse,
  generateAuthenticationOptions,
  verifyAuthenticationResponse,
} from '@simplewebauthn/server';
import type {
  GenerateRegistrationOptionsOpts,
  GenerateAuthenticationOptionsOpts,
  VerifyRegistrationResponseOpts,
  VerifyAuthenticationResponseOpts,
} from '@simplewebauthn/server';
import supabase from '../lib/supabase.js';
import { authenticateToken } from '../middleware/auth.js';
import { logMFAAction } from '../services/mfaAuditService.js';

const router = express.Router();

// WebAuthn configuration
const rpName = 'SMC Trading Agent';
const rpID = process.env.WEBAUTHN_RP_ID || 'localhost';
const origin = process.env.WEBAUTHN_ORIGIN || 'http://localhost:5173';

// Generate registration options
router.post('/register/begin', authenticateToken, async (req, res) => {
  try {
    const userId = req.user?.id;
    const userEmail = req.user?.email;

    if (!userId || !userEmail) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    // Get existing authenticators for the user
    const { data: mfaData, error: fetchError } = await supabase
      .from('user_mfa_methods')
      .select('webauthn_credentials')
      .eq('user_id', userId)
      .single();

    if (fetchError && fetchError.code !== 'PGRST116') {
      console.error('Error fetching WebAuthn credentials:', fetchError);
      return res.status(500).json({ error: 'Failed to fetch user credentials' });
    }

    const existingCredentials = mfaData?.webauthn_credentials || [];

    const opts: GenerateRegistrationOptionsOpts = {
      rpName,
      rpID,
      userID: new TextEncoder().encode(userId),
      userName: userEmail,
      userDisplayName: userEmail,
      attestationType: 'none',
      excludeCredentials: existingCredentials.map((cred: any) => ({
        id: cred.credentialID,
        type: 'public-key',
        transports: cred.transports,
      })),
      authenticatorSelection: {
        residentKey: 'discouraged',
        userVerification: 'preferred',
      },
    };

    const options = await generateRegistrationOptions(opts);

    // Store the challenge temporarily (in a real app, use Redis or similar)
    // For now, we'll store it in the user's session or a temporary table
    const { error: challengeError } = await supabase
      .from('user_mfa_methods')
      .upsert({
        user_id: userId,
        webauthn_challenge: options.challenge
      });

    if (challengeError) {
      console.error('Error storing WebAuthn challenge:', challengeError);
      return res.status(500).json({ error: 'Failed to initiate registration' });
    }

    res.json(options);
  } catch (error) {
    console.error('WebAuthn registration begin error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Complete registration
router.post('/register/complete', authenticateToken, async (req, res) => {
  try {
    const { credential } = req.body;
    const userId = req.user?.id;

    if (!userId || !credential) {
      return res.status(400).json({ error: 'Missing required fields' });
    }

    // Get the stored challenge
    const { data: mfaData, error: fetchError } = await supabase
      .from('user_mfa_methods')
      .select('webauthn_challenge, webauthn_credentials')
      .eq('user_id', userId)
      .single();

    if (fetchError || !mfaData?.webauthn_challenge) {
      await logMFAAction(userId, 'setup', 'webauthn', false, req.ip, req.get('User-Agent'));
      return res.status(400).json({ error: 'No registration in progress' });
    }

    const opts: VerifyRegistrationResponseOpts = {
      response: credential,
      expectedChallenge: mfaData.webauthn_challenge,
      expectedOrigin: origin,
      expectedRPID: rpID,
    };

    const verification = await verifyRegistrationResponse(opts);

    if (!verification.verified || !verification.registrationInfo) {
      await logMFAAction(userId, 'setup', 'webauthn', false, req.ip, req.get('User-Agent'));
      return res.status(400).json({ error: 'Registration verification failed' });
    }

    const { credentialID, credentialPublicKey, counter } = verification.registrationInfo;

    // Store the new credential
    const existingCredentials = mfaData.webauthn_credentials || [];
    const newCredential = {
      credentialID: Buffer.from(credentialID).toString('base64'),
      credentialPublicKey: Buffer.from(credentialPublicKey).toString('base64'),
      counter,
      transports: credential.response.transports || [],
      createdAt: new Date().toISOString()
    };

    const updatedCredentials = [...existingCredentials, newCredential];

    const { error: updateError } = await supabase
      .from('user_mfa_methods')
      .update({
        webauthn_credentials: updatedCredentials,
        webauthn_enabled: true,
        webauthn_challenge: null // Clear the challenge
      })
      .eq('user_id', userId);

    if (updateError) {
      console.error('Error storing WebAuthn credential:', updateError);
      await logMFAAction(userId, 'setup', 'webauthn', false, req.ip, req.get('User-Agent'));
      return res.status(500).json({ error: 'Failed to store credential' });
    }

    await logMFAAction(userId, 'setup', 'webauthn', true, req.ip, req.get('User-Agent'));
    res.json({ verified: true, message: 'WebAuthn credential registered successfully' });
  } catch (error) {
    console.error('WebAuthn registration complete error:', error);
    await logMFAAction(req.user?.id, 'setup', 'webauthn', false, req.ip, req.get('User-Agent'));
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Generate authentication options
router.post('/authenticate/begin', authenticateToken, async (req, res) => {
  try {
    const userId = req.user?.id;

    if (!userId) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    // Get user's WebAuthn credentials
    const { data: mfaData, error: fetchError } = await supabase
      .from('user_mfa_methods')
      .select('webauthn_credentials')
      .eq('user_id', userId)
      .single();

    if (fetchError || !mfaData?.webauthn_credentials?.length) {
      return res.status(400).json({ error: 'No WebAuthn credentials found' });
    }

    const allowCredentials = mfaData.webauthn_credentials.map((cred: any) => ({
      id: cred.credentialID,
      type: 'public-key' as const,
      transports: cred.transports,
    }));

    const opts: GenerateAuthenticationOptionsOpts = {
      rpID,
      allowCredentials,
      userVerification: 'preferred',
    };

    const options = await generateAuthenticationOptions(opts);

    // Store the challenge
    const { error: challengeError } = await supabase
      .from('user_mfa_methods')
      .update({ webauthn_challenge: options.challenge })
      .eq('user_id', userId);

    if (challengeError) {
      console.error('Error storing WebAuthn challenge:', challengeError);
      return res.status(500).json({ error: 'Failed to initiate authentication' });
    }

    res.json(options);
  } catch (error) {
    console.error('WebAuthn authentication begin error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Complete authentication
router.post('/authenticate/complete', authenticateToken, async (req, res) => {
  try {
    const { credential } = req.body;
    const userId = req.user?.id;

    if (!userId || !credential) {
      return res.status(400).json({ error: 'Missing required fields' });
    }

    // Get the stored challenge and credentials
    const { data: mfaData, error: fetchError } = await supabase
      .from('user_mfa_methods')
      .select('webauthn_challenge, webauthn_credentials')
      .eq('user_id', userId)
      .single();

    if (fetchError || !mfaData?.webauthn_challenge || !mfaData?.webauthn_credentials) {
      await logMFAAction(userId, 'verify', 'webauthn', false, req.ip, req.get('User-Agent'));
      return res.status(400).json({ error: 'No authentication in progress' });
    }

    // Find the credential being used
    const credentialID = credential.id;
    const dbCredential = mfaData.webauthn_credentials.find(
      (cred: any) => cred.credentialID === credentialID
    );

    if (!dbCredential) {
      await logMFAAction(userId, 'verify', 'webauthn', false, req.ip, req.get('User-Agent'));
      return res.status(400).json({ error: 'Credential not found' });
    }

    const opts: VerifyAuthenticationResponseOpts = {
      response: credential,
      expectedChallenge: mfaData.webauthn_challenge,
      expectedOrigin: origin,
      expectedRPID: rpID,
      authenticator: {
        credentialID: dbCredential.credentialID,
        credentialPublicKey: Buffer.from(dbCredential.credentialPublicKey, 'base64'),
        counter: dbCredential.counter,
      },
    };

    const verification = await verifyAuthenticationResponse(opts);

    if (!verification.verified) {
      await logMFAAction(userId, 'verify', 'webauthn', false, req.ip, req.get('User-Agent'));
      return res.status(400).json({ error: 'Authentication verification failed' });
    }

    // Update the counter
    const updatedCredentials = mfaData.webauthn_credentials.map((cred: any) => {
      if (cred.credentialID === credentialID) {
        return { ...cred, counter: verification.authenticationInfo.newCounter };
      }
      return cred;
    });

    const { error: updateError } = await supabase
      .from('user_mfa_methods')
      .update({
        webauthn_credentials: updatedCredentials,
        webauthn_challenge: null // Clear the challenge
      })
      .eq('user_id', userId);

    if (updateError) {
      console.error('Error updating WebAuthn credential counter:', updateError);
    }

    await logMFAAction(userId, 'verify', 'webauthn', true, req.ip, req.get('User-Agent'));
    res.json({ verified: true, message: 'WebAuthn authentication successful' });
  } catch (error) {
    console.error('WebAuthn authentication complete error:', error);
    await logMFAAction(req.user?.id, 'verify', 'webauthn', false, req.ip, req.get('User-Agent'));
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Remove WebAuthn credential
router.delete('/credential/:credentialId', authenticateToken, async (req, res) => {
  try {
    const { credentialId } = req.params;
    const userId = req.user?.id;

    if (!userId || !credentialId) {
      return res.status(400).json({ error: 'Missing required fields' });
    }

    // Get current credentials
    const { data: mfaData, error: fetchError } = await supabase
      .from('user_mfa_methods')
      .select('webauthn_credentials')
      .eq('user_id', userId)
      .single();

    if (fetchError || !mfaData?.webauthn_credentials) {
      return res.status(400).json({ error: 'No WebAuthn credentials found' });
    }

    // Remove the specified credential
    const updatedCredentials = mfaData.webauthn_credentials.filter(
      (cred: any) => cred.credentialID !== credentialId
    );

    const webauthnEnabled = updatedCredentials.length > 0;

    const { error: updateError } = await supabase
      .from('user_mfa_methods')
      .update({
        webauthn_credentials: updatedCredentials,
        webauthn_enabled: webauthnEnabled
      })
      .eq('user_id', userId);

    if (updateError) {
      console.error('Error removing WebAuthn credential:', updateError);
      return res.status(500).json({ error: 'Failed to remove credential' });
    }

    await logMFAAction(userId, 'disable', 'webauthn', true, req.ip, req.get('User-Agent'));
    res.json({ success: true, message: 'WebAuthn credential removed successfully' });
  } catch (error) {
    console.error('WebAuthn credential removal error:', error);
    await logMFAAction(req.user?.id, 'disable', 'webauthn', false, req.ip, req.get('User-Agent'));
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;