"""Simple symmetric encryption for storing secrets at rest."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet


def _derive_key(secret: str) -> bytes:
    """Derive a valid Fernet key from an arbitrary secret string via SHA-256."""
    digest = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_secret(plaintext: str, secret: str) -> str:
    """Encrypt plaintext using the app secret. Returns a URL-safe base64 token."""
    f = Fernet(_derive_key(secret))
    return f.encrypt(plaintext.encode()).decode()


def decrypt_secret(token: str, secret: str) -> str:
    """Decrypt a token produced by encrypt_secret. Raises InvalidToken if tampered."""
    f = Fernet(_derive_key(secret))
    return f.decrypt(token.encode()).decode()
