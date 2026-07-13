from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken
from loguru import logger


class FieldEncryptor:
    """Encrypt/decrypt sensitive DB fields. Supports legacy plaintext reads."""

    def __init__(self, key: str | None, *, warn_if_missing: bool = True) -> None:
        self._fernet: Fernet | None = None
        if key:
            self._fernet = Fernet(key.encode() if isinstance(key, str) else key)
        elif warn_if_missing:
            logger.warning(
                "DATA_ENCRYPTION_KEY is not set — session_token/document_ref "
                "will be stored in plaintext. Generate one with: "
                "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )

    @classmethod
    def noop(cls) -> FieldEncryptor:
        return cls(None, warn_if_missing=False)

    @property
    def enabled(self) -> bool:
        return self._fernet is not None

    def encrypt(self, value: str | None) -> str | None:
        if value is None or self._fernet is None:
            return value
        return self._fernet.encrypt(value.encode("utf-8")).decode("ascii")

    def decrypt(self, value: str | None) -> str | None:
        if value is None or self._fernet is None:
            return value
        try:
            return self._fernet.decrypt(value.encode("ascii")).decode("utf-8")
        except (InvalidToken, ValueError):
            if value.startswith("gAAAAA"):
                logger.error(
                    "decrypt() failed for Fernet-looking value — check DATA_ENCRYPTION_KEY"
                )
            return value

    @staticmethod
    def generate_key() -> str:
        return Fernet.generate_key().decode("ascii")
