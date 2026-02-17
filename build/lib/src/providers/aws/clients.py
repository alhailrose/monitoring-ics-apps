"""AWS client factory helpers."""

import boto3


def get_session(profile_name=None, region_name=None):
    if profile_name:
        return boto3.Session(profile_name=profile_name, region_name=region_name)
    return boto3.Session(region_name=region_name)


def get_client(service_name, profile_name=None, region_name=None):
    session = get_session(profile_name=profile_name, region_name=region_name)
    return session.client(service_name, region_name=region_name)
