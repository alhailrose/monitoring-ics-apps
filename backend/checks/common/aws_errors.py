"""AWS credential and token error detection utilities.

Provides helpers to identify expired tokens, missing credentials, and other
auth-related failures so checks can surface clear, actionable messages instead
of raw stack traces.
"""

from __future__ import annotations

import logging

from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    NoCredentialsError,
    ProfileNotFound,
)

logger = logging.getLogger(__name__)

# Error codes returned by AWS STS / SSO / IAM when credentials are bad.
_CREDENTIAL_ERROR_CODES = frozenset(
    {
        "ExpiredTokenException",
        "ExpiredToken",
        "InvalidIdentityToken",
        "UnrecognizedClientException",
        "InvalidClientTokenId",
        "SignatureDoesNotMatch",
        "AuthFailure",
        "AccessDenied",
        "AccessDeniedException",
        "UnauthorizedAccess",
    }
)

# Substrings that appear in botocore/SSO error messages for token issues.
_TOKEN_EXPIRED_HINTS = (
    "expired",
    "token",
    "sso",
    "refresh",
    "The SSO session",
    "Unable to load SSO Token",
    "Error when retrieving token",
)


def is_credential_error(exc: BaseException) -> bool:
    """Return True if *exc* is an AWS credential / token related error."""
    if isinstance(exc, (NoCredentialsError, ProfileNotFound)):
        return True

    if isinstance(exc, ClientError):
        code = exc.response.get("Error", {}).get("Code", "")
        if code in _CREDENTIAL_ERROR_CODES:
            return True

    # Catch botocore SSO token errors that surface as generic exceptions.
    msg = str(exc).lower()
    return any(hint.lower() in msg for hint in _TOKEN_EXPIRED_HINTS)


def _login_command_for_profile(profile: str) -> str:
    """Return the correct login command based on the profile's auth type in ~/.aws/config."""
    from configparser import ConfigParser
    from pathlib import Path

    config_path = Path.home() / ".aws" / "config"
    if profile and config_path.exists():
        parser = ConfigParser()
        parser.read(str(config_path))
        # Check both "profile <name>" and bare "<name>" sections
        for section in (f"profile {profile}", profile):
            if parser.has_section(section) and parser.has_option(section, "login_session"):
                return f"aws login --remote --profile {profile}"
    return f"aws sso login --profile {profile}"


def friendly_credential_message(exc: BaseException, profile: str = "") -> str:
    """Return a user-friendly message for credential/token errors."""
    login_cmd = _login_command_for_profile(profile)

    if isinstance(exc, NoCredentialsError):
        return (
            f"AWS credentials not found for profile '{profile}'. "
            f"Run: {login_cmd}"
        )

    if isinstance(exc, ProfileNotFound):
        return f"AWS profile '{profile}' not found in ~/.aws/config or ~/.aws/credentials."

    if isinstance(exc, ClientError):
        code = exc.response.get("Error", {}).get("Code", "")
        if code in ("ExpiredTokenException", "ExpiredToken"):
            return (
                f"AWS session token expired for profile '{profile}'. "
                f"Run: {login_cmd}"
            )
        if code == "InvalidClientTokenId":
            return (
                f"Invalid AWS access key for profile '{profile}'. "
                "Check your credentials configuration."
            )
        if code == "SignatureDoesNotMatch":
            return (
                f"AWS secret key mismatch for profile '{profile}'. "
                "Verify your credentials are correct."
            )
        if code in ("AccessDenied", "AccessDeniedException"):
            return (
                f"Access denied for profile '{profile}'. "
                "Check IAM permissions for this operation."
            )

    msg = str(exc)
    msg_lower = msg.lower()
    if "token" in msg_lower or "expired" in msg_lower or "sso" in msg_lower:
        return (
            f"AWS session expired or invalid for profile '{profile}'. "
            f"Run: {login_cmd}"
        )

    return (
        f"AWS authentication failed for profile '{profile}': {msg}. "
        f"Try: {login_cmd}"
    )


def classify_aws_error(exc: BaseException, profile: str = "") -> dict:
    """Classify an exception and return a structured error dict.

    Returns a dict with keys:
        error_type: 'credential' | 'aws_api' | 'unexpected'
        error: human-readable message
        is_credential_error: bool
    """
    if is_credential_error(exc):
        return {
            "error_type": "credential",
            "error": friendly_credential_message(exc, profile),
            "is_credential_error": True,
        }

    if isinstance(exc, (BotoCoreError, ClientError)):
        return {
            "error_type": "aws_api",
            "error": str(exc),
            "is_credential_error": False,
        }

    return {
        "error_type": "unexpected",
        "error": str(exc),
        "is_credential_error": False,
    }
