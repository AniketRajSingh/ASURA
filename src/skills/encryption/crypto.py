# ============================================================
# skills/encryption/crypto.py — Encrypted Memory at Rest
# ============================================================

import os
import json
import base64
from skills.logger import log_audit, log_app
from settings import settings as config


def _get_key() -> bytes:
    """Get or generate the encryption key."""
    if os.path.isfile(config.ENCRYPTION_KEY_PATH):
        with open(config.ENCRYPTION_KEY_PATH, "rb") as f:
            return f.read()

    # Generate new key
    try:
        from cryptography.fernet import Fernet
        key = Fernet.generate_key()
    except ImportError:
        # Fallback: generate a simple key
        import secrets
        key = base64.urlsafe_b64encode(secrets.token_bytes(32))

    with open(config.ENCRYPTION_KEY_PATH, "wb") as f:
        f.write(key)
    os.chmod(config.ENCRYPTION_KEY_PATH, 0o600)
    log_audit("CRYPTO", "New encryption key generated")
    return key


def encrypt(data: str) -> str:
    """Encrypt a string. Returns base64-encoded ciphertext."""
    if not data:
        raise ValueError("Cannot encrypt empty data.")
    if not isinstance(data, str):
        raise TypeError(f"Data to encrypt must be a string, got {type(data).__name__}.")
    try:
        from cryptography.fernet import Fernet
        key = _get_key()
        f = Fernet(key)
        return f.encrypt(data.encode()).decode()
    except ImportError:
        # Simple XOR fallback (NOT production-safe, just obfuscation)
        return _xor_encode(data)


def decrypt(ciphertext: str) -> str:
    """Decrypt a base64-encoded ciphertext string."""
    if not ciphertext:
        raise ValueError("Cannot decrypt empty ciphertext.")
    if not isinstance(ciphertext, str):
        raise TypeError(f"Ciphertext must be a string, got {type(ciphertext).__name__}.")
    try:
        from cryptography.fernet import Fernet
        key = _get_key()
        f = Fernet(key)
        return f.decrypt(ciphertext.encode()).decode()
    except ImportError:
        return _xor_decode(ciphertext)


def encrypt_file(filepath: str) -> bool:
    """Encrypt a file in-place."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = f.read()
        encrypted = encrypt(data)
        with open(filepath + ".enc", "w") as f:
            f.write(encrypted)
        os.remove(filepath)
        log_audit("CRYPTO", f"Encrypted: {filepath}")
        return True
    except Exception as e:
        log_audit("CRYPTO_ERROR", f"Encryption failed: {filepath}: {e}")
        return False


def decrypt_file(filepath: str) -> bool:
    """Decrypt a .enc file in-place."""
    enc_path = filepath if filepath.endswith(".enc") else filepath + ".enc"
    out_path = enc_path.replace(".enc", "")

    try:
        with open(enc_path, "r") as f:
            ciphertext = f.read()
        decrypted = decrypt(ciphertext)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(decrypted)
        os.remove(enc_path)
        log_audit("CRYPTO", f"Decrypted: {out_path}")
        return True
    except Exception as e:
        log_audit("CRYPTO_ERROR", f"Decryption failed: {enc_path}: {e}")
        return False


def encrypt_json(data: dict) -> str:
    """Encrypt a dict as JSON string."""
    return encrypt(json.dumps(data, ensure_ascii=False))


def decrypt_json(ciphertext: str) -> dict:
    """Decrypt a JSON string back to dict."""
    return json.loads(decrypt(ciphertext))


# ─── XOR fallback (when cryptography not installed) ──────────
def _xor_encode(data: str) -> str:
    key = _get_key()
    encoded = bytes(d ^ key[i % len(key)] for i, d in enumerate(data.encode()))
    return base64.urlsafe_b64encode(encoded).decode()


def _xor_decode(encoded: str) -> str:
    key = _get_key()
    decoded = base64.urlsafe_b64decode(encoded)
    return bytes(d ^ key[i % len(key)] for i, d in enumerate(decoded)).decode()
