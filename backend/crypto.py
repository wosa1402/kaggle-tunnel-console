"""Field-level encryption for secrets stored in the DB.

Uses Fernet (AES-128-CBC + HMAC-SHA256). The master key lives in the
ENCRYPTION_KEY env var. If missing, the app refuses to start rather than
silently generating a key (which would become unrecoverable on restart
and corrupt existing encrypted data).
"""
from __future__ import annotations

import sys
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import String, TypeDecorator

from .config import ENCRYPTION_KEY


def _load_fernet() -> Fernet:
    if not ENCRYPTION_KEY:
        sys.stderr.write(
            "\nFATAL: ENCRYPTION_KEY not set.\n"
            "Generate one and put it in .env:\n\n"
            "  python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\"\n\n"
            "WARNING: once set, do NOT change or lose this key — it's required\n"
            "to decrypt existing account secrets in the database.\n"
        )
        raise SystemExit(1)
    try:
        return Fernet(ENCRYPTION_KEY.encode())
    except (ValueError, TypeError) as e:
        sys.stderr.write(
            f"\nFATAL: ENCRYPTION_KEY is not a valid Fernet key ({e}).\n"
            "It must be a 32-byte url-safe base64-encoded string.\n"
        )
        raise SystemExit(1)


_fernet = _load_fernet()


def encrypt(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return _fernet.encrypt(value.encode("utf-8")).decode("ascii")


def decrypt(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    try:
        return _fernet.decrypt(value.encode("ascii")).decode("utf-8")
    except InvalidToken:
        raise ValueError(
            "Failed to decrypt a field. ENCRYPTION_KEY may have changed "
            "since this row was written."
        )


class EncryptedString(TypeDecorator):
    """SQLAlchemy column type that encrypts on write, decrypts on read."""
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return encrypt(value)

    def process_result_value(self, value, dialect):
        return decrypt(value)
