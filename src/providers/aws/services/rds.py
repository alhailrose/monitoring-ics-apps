"""RDS service wrapper."""

from src.providers.aws.clients import get_client


def client(profile_name=None, region_name=None):
    return get_client("rds", profile_name=profile_name, region_name=region_name)
