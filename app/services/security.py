from cryptography.fernet import Fernet, InvalidToken

from app.config import SETTINGS_ENCRYPTION_KEY


class SettingsEncryptionError(RuntimeError):
    pass


def _fernet() -> Fernet:
    if not SETTINGS_ENCRYPTION_KEY:
        raise SettingsEncryptionError(
            "Set SETTINGS_ENCRYPTION_KEY in the backend .env before saving provider settings."
        )
    try:
        return Fernet(SETTINGS_ENCRYPTION_KEY.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise SettingsEncryptionError("SETTINGS_ENCRYPTION_KEY is not a valid Fernet key.") from exc


def encrypt_api_key(api_key: str) -> str:
    return _fernet().encrypt(api_key.encode("utf-8")).decode("ascii")


def decrypt_api_key(encrypted_api_key: str) -> str:
    try:
        return _fernet().decrypt(encrypted_api_key.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeEncodeError) as exc:
        raise SettingsEncryptionError(
            "Could not decrypt the saved provider key. Check SETTINGS_ENCRYPTION_KEY."
        ) from exc
