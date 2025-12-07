"""
Encryption and Input Sanitization Helpers

This module provides utilities for:
1. Data encryption/decryption using Fernet (symmetric encryption)
2. Input sanitization to prevent XSS and injection attacks
3. Authentication decorators for route protection

Requires:
- cryptography library for Fernet encryption (optional)
- bleach library for HTML sanitization
"""

# --- optional encryption helpers ---
from functools import wraps
import bleach
from flask import current_app, redirect, session, url_for

# ============================================================================
# ENCRYPTION UTILITIES
# ============================================================================

try:
    from cryptography.fernet import Fernet, InvalidToken
    _has_fernet = True
except Exception:
    _has_fernet = False


def get_fernet():
    """
    Initialize and return a Fernet cipher instance.

    Retrieves the encryption key from Flask application config (FERNET_KEY).
    Returns None if encryption is not enabled or key is not configured.

    Returns:
        Fernet: Cipher instance for encryption/decryption, or None if unavailable

    Note:
        - FERNET_KEY should be a valid Fernet key generated with Fernet.generate_key()
        - If key is missing or invalid, encryption operations are skipped

    Example:
        >>> f = get_fernet()
        >>> if f:
        ...     encrypted = f.encrypt(b"sensitive data")
    """
    key = current_app.config.get('FERNET_KEY')
    if not key or not _has_fernet:
        return None
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_value(value: str):
    """
    Encrypt a string value using Fernet symmetric encryption.

    Safely encrypts sensitive data (e.g., medical information, work types).
    Returns original value unchanged if encryption is not available.

    Args:
        value (str): Plain text string to encrypt

    Returns:
        str: Encrypted value as string, or original value if encryption unavailable

    Raises:
        None: Gracefully handles missing encryption setup

    Example:
        >>> encrypted = encrypt_value("Patient Name")
        >>> # Returns: 'gAAAAABlxxx...' (encrypted string)
    """
    f = get_fernet()
    if not f or value is None:
        return value
    return f.encrypt(value.encode()).decode()


def decrypt_value(value: str):
    """
    Decrypt a Fernet-encrypted string value.

    Safely decrypts previously encrypted data with error handling.
    Returns None if decryption fails (e.g., invalid token or corrupted data).

    Args:
        value (str): Encrypted string to decrypt

    Returns:
        str: Decrypted plain text, or None if decryption fails

    Raises:
        None: All exceptions caught and handled gracefully

    Example:
        >>> decrypted = decrypt_value('gAAAAABlxxx...')
        >>> # Returns: 'Patient Name'
    """
    f = get_fernet()
    if not f or value is None:
        return value
    try:
        return f.decrypt(value.encode()).decode()
    except InvalidToken:
        # Log error: Invalid or corrupted encrypted token
        return None


# ============================================================================
# INPUT SANITIZATION
# ============================================================================

def clean_text(s: str, maxlen: int = 256):
    """
    Sanitize and validate user input text.

    Performs multiple sanitization steps:
    1. Converts input to string and strips whitespace
    2. Removes HTML/script tags using bleach library (XSS prevention)
    3. Enforces maximum length limit to prevent overflow attacks

    Args:
        s (str): Input string to sanitize
        maxlen (int): Maximum allowed string length (default: 256)

    Returns:
        str: Sanitized string, or None if input is None

    Security Features:
        - Removes all HTML tags and attributes
        - Prevents XSS injection attacks
        - Enforces length limits to prevent buffer overflows
        - Strips leading/trailing whitespace

    Example:
        >>> clean_text("<script>alert('xss')</script>hello", maxlen=50)
        # Returns: "alert('xss')hello"

        >>> clean_text("    test   ", maxlen=256)
        # Returns: "test"

        >>> clean_text(None)
        # Returns: None
    """
    if s is None:
        return None

    # Convert to string and strip whitespace
    t = str(s).strip()

    # Remove HTML tags and script content
    # tags=[] means strip all HTML tags
    # strip=True means remove content of dangerous tags
    t = bleach.clean(t, tags=[], strip=True)

    # Enforce maximum length
    if maxlen:
        t = t[:maxlen]

    return t


# ============================================================================
# AUTHENTICATION DECORATORS
# ============================================================================

def login_required(view):
    """
    Decorator to protect routes requiring user authentication.

    Checks if user_id exists in session before allowing access.
    Redirects unauthenticated users to login page.

    Args:
        view (function): Flask view function to protect

    Returns:
        function: Wrapped view function with authentication check

    Usage:
        @app.route('/dashboard')
        @login_required
        def dashboard():
            return render_template('dashboard.html')

    Note:
        - Uses Flask session to check authentication status
        - Redirects to 'auth.login' route if not authenticated
        - Preserves function metadata with @wraps decorator
    """
    @wraps(view)
    def wrapped(*args, **kwargs):
        # Check if user_id exists in session
        if not session.get('user_id'):
            # Redirect to login page
            return redirect(url_for('auth.login'))
        # User is authenticated, proceed to view
        return view(*args, **kwargs)
    return wrapped