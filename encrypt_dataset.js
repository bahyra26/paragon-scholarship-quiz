/**
 * Dataset Encryptor (AES-GCM-256 with PBKDF2)
 * Encrypts quiz_data.json into quiz_data.enc using AES-256-GCM.
 */
const fs = require('fs');
const path = require('path');
const { subtle, randomBytes } = require('crypto');

const PASSWORD = process.env.QUIZ_PASSWORD || 'persebayaselamanya';

async function encryptData() {
  const srcPath = path.join(__dirname, 'public', 'data', 'quiz_data.json');
  if (!fs.existsSync(srcPath)) {
    console.error('File not found:', srcPath);
    process.exit(1);
  }

  const rawJson = fs.readFileSync(srcPath, 'utf8');
  const enc = new TextEncoder();

  // 16-byte cryptographic salt, 12-byte IV for AES-GCM
  const salt = randomBytes(16);
  const iv = randomBytes(12);

  // Derive 256-bit AES-GCM key using PBKDF2 with 100,000 iterations of SHA-256
  const keyMaterial = await subtle.importKey(
    'raw',
    enc.encode(PASSWORD),
    { name: 'PBKDF2' },
    false,
    ['deriveKey']
  );

  const aesKey = await subtle.deriveKey(
    {
      name: 'PBKDF2',
      salt: salt,
      iterations: 100000,
      hash: 'SHA-256'
    },
    keyMaterial,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt']
  );

  // Encrypt JSON
  const ciphertextBuffer = await subtle.encrypt(
    { name: 'AES-GCM', iv: iv },
    aesKey,
    enc.encode(rawJson)
  );

  const payload = {
    algorithm: 'AES-256-GCM',
    kdf: 'PBKDF2-SHA256-100K',
    salt: Buffer.from(salt).toString('base64'),
    iv: Buffer.from(iv).toString('base64'),
    data: Buffer.from(ciphertextBuffer).toString('base64')
  };

  const payloadString = JSON.stringify(payload);

  // Save to public/data/quiz_data.enc and data/quiz_data.enc
  fs.mkdirSync(path.join(__dirname, 'public', 'data'), { recursive: true });
  fs.mkdirSync(path.join(__dirname, 'data'), { recursive: true });

  fs.writeFileSync(path.join(__dirname, 'public', 'data', 'quiz_data.enc'), payloadString, 'utf8');
  fs.writeFileSync(path.join(__dirname, 'data', 'quiz_data.enc'), payloadString, 'utf8');

  console.log('✅ Successfully encrypted quiz dataset into quiz_data.enc');
  console.log(`Original size: ${rawJson.length} bytes | Encrypted payload: ${payloadString.length} bytes`);
}

encryptData().catch(err => {
  console.error('Encryption error:', err);
  process.exit(1);
});
