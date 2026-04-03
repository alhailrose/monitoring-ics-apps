"""AWS client factory helpers."""

from pathlib import Path

import boto3
import botocore.session


def user_aws_config_path(username: str) -> str:
    return str(Path.home() / ".aws" / "users" / username / "config")


def _build_botocore_session(
    aws_config_file: str | None = None,
) -> botocore.session.Session:
    session = botocore.session.Session()
    if not aws_config_file:
        return session

    session.set_config_variable("config_file", aws_config_file)
    user_credentials_file = Path(aws_config_file).with_name("credentials")
    if user_credentials_file.exists():
        session.set_config_variable("credentials_file", str(user_credentials_file))
    return session


def get_session(
    profile_name=None,
    region_name=None,
    aws_access_key_id=None,
    aws_secret_access_key=None,
    aws_session_token=None,
    aws_config_file: str | None = None,
):
    kwargs = {
        "profile_name": profile_name,
        "region_name": region_name,
        "aws_access_key_id": aws_access_key_id,
        "aws_secret_access_key": aws_secret_access_key,
        "aws_session_token": aws_session_token,
    }
    if aws_config_file:
        kwargs["botocore_session"] = _build_botocore_session(aws_config_file)
    return boto3.Session(**kwargs)


def get_client(
    service_name,
    profile_name=None,
    region_name=None,
    aws_config_file: str | None = None,
):
    session = get_session(
        profile_name=profile_name,
        region_name=region_name,
        aws_config_file=aws_config_file,
    )
    return session.client(service_name, region_name=region_name)
