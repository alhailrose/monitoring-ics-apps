"""Budgets service wrapper."""

from src.providers.aws.clients import get_client


def client(profile_name=None, region_name="us-east-1"):
    return get_client("budgets", profile_name=profile_name, region_name=region_name)
