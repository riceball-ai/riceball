"""
Django Password Hash Adapter

Supports verifying Django pbkdf2_sha256 format passwords, and automatically upgrading to bcrypt upon successful verification
"""
import hashlib
import base64
from typing import Optional


def verify_django_password(password: str, hashed: str) -> bool:
    """
    Verify Django pbkdf2_sha256 format password
    
    Django password format: pbkdf2_sha256$iterations$salt$hash
    Example: pbkdf2_sha256$600000$2RTwD8t0sBkSAb6uz55cS5$OhTo3WDBeFdR+9gZE8332AInVUngsJ7pWLHzn1RE/o8=
    
    Args:
        password: Plain text password
        hashed: Django hashed password
        
    Returns:
        bool: Whether password matches
    """
    if not hashed.startswith('pbkdf2_sha256$'):
        return False
    
    try:
        # Parse Django password format
        algorithm, iterations, salt, hash_value = hashed.split('$')
        iterations = int(iterations)
        
        # Calculate hash using same parameters
        new_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            iterations,
            dklen=None  # Use default length
        )
        
        # Base64 encode
        new_hash_b64 = base64.b64encode(new_hash).decode('ascii')
        
        # Compare hash values
        return new_hash_b64 == hash_value
        
    except (ValueError, IndexError):
        return False


def is_django_password(hashed: str) -> bool:
    """
    Check if password is in Django format
    
    Args:
        hashed: Password hash
        
    Returns:
        bool: Whether it is Django format
    """
    return hashed.startswith('pbkdf2_sha256$')


def is_unusable_password(hashed: str) -> bool:
    """
    Check if password is Django's unusable password
    
    Passwords starting with '!' in Django indicate that the account cannot be logged in with a password,
    usually used for OAuth login or disabled accounts.
    
    Args:
        hashed: Password hash
        
    Returns:
        bool: Whether it is unusable password
    """
    return hashed.startswith('!')


# Test function
if __name__ == "__main__":
    # Test Django password verification
    django_hash = "pbkdf2_sha256$600000$2RTwD8t0sBkSAb6uz55cS5$OhTo3WDBeFdR+9gZE8332AInVUngsJ7pWLHzn1RE/o8="
    
    # Need actual password to test here
    # test_password = "your_actual_password"
    # result = verify_django_password(test_password, django_hash)
    # print(f"Password verification: {result}")
    
    print(f"Is Django password: {is_django_password(django_hash)}")
    print(f"Is Django password (bcrypt): {is_django_password('$2b$12$...')}")
