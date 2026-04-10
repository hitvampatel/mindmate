"""
utils/validators.py — Input Validation Helpers

Centralised validation functions for API inputs.
Returns a list of error strings (empty list = valid).
"""

import re


def validate_signup(data: dict) -> list:
    """Validate signup payload. Returns list of error messages."""
    errors = []

    if not data:
        return ["Request body is required."]

    username = data.get("username", "").strip()
    email    = data.get("email", "").strip()
    password = data.get("password", "")

    # Username
    if not username:
        errors.append("Username is required.")
    elif len(username) < 3:
        errors.append("Username must be at least 3 characters.")
    elif len(username) > 30:
        errors.append("Username must be 30 characters or fewer.")
    elif not re.match(r"^[a-zA-Z0-9_.-]+$", username):
        errors.append("Username can only contain letters, numbers, underscores, dots, and hyphens.")

    # Email
    if not email:
        errors.append("Email is required.")
    elif not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        errors.append("Please provide a valid email address.")

    # Password
    if not password:
        errors.append("Password is required.")
    elif len(password) < 8:
        errors.append("Password must be at least 8 characters.")
    elif len(password) > 128:
        errors.append("Password is too long (max 128 characters).")

    return errors


def validate_login(data: dict) -> list:
    """Validate login payload."""
    errors = []

    if not data:
        return ["Request body is required."]

    has_email    = bool(data.get("email", "").strip())
    has_username = bool(data.get("username", "").strip())
    has_password = bool(data.get("password", ""))

    if not has_email and not has_username:
        errors.append("Email or username is required.")

    if not has_password:
        errors.append("Password is required.")

    return errors
