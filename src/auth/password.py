"""
Password hashing utilities.
"""
import hashlib
import secrets


def hash_password(password: str) -> str:
    """
    Hash a password using PBKDF2 with SHA-256.
    Returns: salt$hash format
    """
    salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000  # iterations
    )
    return f"{salt}${pw_hash.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a password against its hash.
    """
    try:
        salt, stored_hash = hashed.split('$')
        pw_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        return secrets.compare_digest(pw_hash.hex(), stored_hash)
    except (ValueError, AttributeError):
        return False
