import base64
import hashlib

from cryptography.fernet import Fernet

from config.settings import get_settings


def _derive_key(seed: str) -> bytes:
    raw = hashlib.sha256(seed.encode()).digest()
    return base64.urlsafe_b64encode(raw)


def get_fernet() -> Fernet:
    settings = get_settings()
    key = _derive_key(settings.bot_token)
    return Fernet(key)


def encrypt(data: str) -> str:
    fernet = get_fernet()
    return fernet.encrypt(data.encode()).decode()


def decrypt(data: str) -> str:
    fernet = get_fernet()
    return fernet.decrypt(data.encode()).decode()
