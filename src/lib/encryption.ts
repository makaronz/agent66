import crypto from 'crypto';

const ALGORITHM = 'aes-256-gcm';
const KEY_LENGTH = 32;
const IV_LENGTH = 16;
const TAG_LENGTH = 16;

// Generate a random encryption key
export const generateKey = (): string => {
  return crypto.randomBytes(KEY_LENGTH).toString('hex');
};

// Encrypt data using AES-256-GCM
export const encrypt = (text: string, key: string): string => {
  try {
    const keyBuffer = Buffer.from(key, 'hex');
    const iv = crypto.randomBytes(IV_LENGTH);
    const cipher = crypto.createCipheriv(ALGORITHM, keyBuffer, iv);
    cipher.setAAD(Buffer.from('additional-data'));
    
    let encrypted = cipher.update(text, 'utf8', 'hex');
    encrypted += cipher.final('hex');
    
    const tag = cipher.getAuthTag();
    
    // Combine iv, tag, and encrypted data
    return iv.toString('hex') + ':' + tag.toString('hex') + ':' + encrypted;
  } catch (error) {
    console.error('Encryption error:', error);
    throw new Error('Failed to encrypt data');
  }
};

// Decrypt data using AES-256-GCM
export const decrypt = (encryptedData: string, key: string): string => {
  try {
    const keyBuffer = Buffer.from(key, 'hex');
    const parts = encryptedData.split(':');
    
    if (parts.length !== 3) {
      throw new Error('Invalid encrypted data format');
    }
    
    const iv = Buffer.from(parts[0], 'hex');
    const tag = Buffer.from(parts[1], 'hex');
    const encrypted = parts[2];
    
    const decipher = crypto.createDecipheriv(ALGORITHM, keyBuffer, iv);
    decipher.setAAD(Buffer.from('additional-data'));
    decipher.setAuthTag(tag);
    
    let decrypted = decipher.update(encrypted, 'hex', 'utf8');
    decrypted += decipher.final('utf8');
    
    return decrypted;
  } catch (error) {
    console.error('Decryption error:', error);
    throw new Error('Failed to decrypt data');
  }
};

// Hash data using SHA-256
export const hash = (data: string): string => {
  return crypto.createHash('sha256').update(data).digest('hex');
};

// Generate a secure random string
export const generateSecureRandom = (length: number = 32): string => {
  return crypto.randomBytes(length).toString('hex');
};

// Verify hash
export const verifyHash = (data: string, hashedData: string): boolean => {
  return hash(data) === hashedData;
};

// Generate TOTP secret
export const generateTOTPSecret = (): string => {
  return crypto.randomBytes(20).toString('hex');
};

export default {
  generateKey,
  encrypt,
  decrypt,
  hash,
  generateSecureRandom,
  verifyHash,
  generateTOTPSecret
};