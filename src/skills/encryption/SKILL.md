---
name: encryption
description: "Core skill for encrypting and decrypting data at rest using Fernet or XOR fallback."
entry_point: crypto.py
---

# Encryption Skill

Provides secure storage and data protection by encrypting strings, JSON objects, and files. It uses Fernet encryption when the `cryptography` library is available, falling back to XOR obfuscation otherwise.

### 🔧 Tools / Functions
- `encrypt(data)`: Encrypts a string and returns base64-encoded ciphertext.
- `decrypt(ciphertext)`: Decrypts a base64-encoded ciphertext string.
- `encrypt_file(filepath)`: Encrypts a file in-place, renaming it with a `.enc` extension.
- `decrypt_file(filepath)`: Decrypts a `.enc` file in-place.
- `encrypt_json(data)`: Serializes a dictionary to JSON and encrypts it.
- `decrypt_json(ciphertext)`: Decrypts a ciphertext string and deserializes it back to a dictionary.

### 📝 Examples
- "Encrypt the message 'secret'" -> Returns an encrypted string.
- "Decrypt this file" -> Restores the original file from its `.enc` version.

### 🛠️ Requirements
- `cryptography` (optional, for Fernet encryption)
- Encryption key stored at `config.ENCRYPTION_KEY_PATH`
