"""
Utility functions for AWS Monitoring Hub
"""

import boto3

from .config import PROFILE_GROUPS


def resolve_region(profile_list, override_region):
    """Resolve region using CLI override, then profile config, then fallback."""
    if override_region:
        return override_region
    for prof in profile_list:
        try:
            session = boto3.Session(profile_name=prof)
            if session.region_name:
                return session.region_name
        except Exception:
            continue
    return "ap-southeast-3"


def get_account_id(profile):
    """Get account ID for a profile"""
    for group in PROFILE_GROUPS.values():
        if profile in group:
            return group[profile]
    return "Unknown"


def list_local_profiles():
    """Return list of AWS CLI profiles available locally."""
    try:
        return boto3.Session().available_profiles
    except Exception:
        return []
