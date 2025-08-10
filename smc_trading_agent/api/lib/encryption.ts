import CryptoJS from 'crypto-js';

const ENCRYPTION_KEY = process.env.ENCRYPTION_KEY || 'smc-trading-agent-default-key-2024';

export class EncryptionService {
  private static key = ENCRYPTION_KEY;

  /**
   * Encrypt sensitive data like API keys
   */
  static encrypt(text: string): string {
    try {
      const encrypted = CryptoJS.AES.encrypt(text, this.key).toString();
      return encrypted;
    } catch (error) {
      console.error('Encryption error:', error);
      throw new Error('Failed to encrypt data');
    }
  }

  /**
   * Decrypt sensitive data like API keys
   */
  static decrypt(encryptedText: string): string {
    try {
      const bytes = CryptoJS.AES.decrypt(encryptedText, this.key);
      const decrypted = bytes.toString(CryptoJS.enc.Utf8);
      
      if (!decrypted) {
        throw new Error('Failed to decrypt - invalid key or corrupted data');
      }
      
      return decrypted;
    } catch (error) {
      console.error('Decryption error:', error);
      throw new Error('Failed to decrypt data');
    }
  }

  /**
   * Generate a secure random key for encryption
   */
  static generateKey(): string {
    return CryptoJS.lib.WordArray.random(256/8).toString();
  }

  /**
   * Hash password for storage
   */
  static hashPassword(password: string): string {
    const salt = CryptoJS.lib.WordArray.random(128/8);
    const hash = CryptoJS.PBKDF2(password, salt, {
      keySize: 256/32,
      iterations: 10000
    });
    return salt.toString() + ':' + hash.toString();
  }

  /**
   * Verify password against hash
   */
  static verifyPassword(password: string, hash: string): boolean {
    try {
      const [saltStr, hashStr] = hash.split(':');
      const salt = CryptoJS.enc.Hex.parse(saltStr);
      const computedHash = CryptoJS.PBKDF2(password, salt, {
        keySize: 256/32,
        iterations: 10000
      });
      return computedHash.toString() === hashStr;
    } catch (error) {
      console.error('Password verification error:', error);
      return false;
    }
  }
}

export default EncryptionService;