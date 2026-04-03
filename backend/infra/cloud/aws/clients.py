"""AWS client factory helpers."""

import json
import logging
import os
from configparser import ConfigParser
from pathlib import Path

import boto3
import botocore.session

logger = logging.getLogger(__name__)


def user_aws_config_path(username: str) -> str:
    return str(Path.home() / ".aws" / "users" / username / "config")


def user_sso_cache_path(username: str) -> str:
    return str(Path.home() / ".aws" / "users" / username / "sso" / "cache")


def _build_botocore_session(
    aws_config_file: str | None = None,
    sso_cache_dir: str | None = None,
) -> botocore.session.Session:
    session = botocore.session.Session()
    if not aws_config_file:
        return session

    session.set_config_variable("config_file", aws_config_file)
    user_credentials_file = Path(aws_config_file).with_name("credentials")
    if user_credentials_file.exists():
        session.set_config_variable("credentials_file", str(user_credentials_file))
    if sso_cache_dir:
        session.set_config_variable("sso_cache_dir", sso_cache_dir)
    return session


def get_session(
    profile_name=None,
    region_name=None,
    aws_access_key_id=None,
    aws_secret_access_key=None,
    aws_session_token=None,
    aws_config_file: str | None = None,
    sso_cache_dir: str | None = None,
):
    kwargs = {
        "profile_name": profile_name,
        "region_name": region_name,
        "aws_access_key_id": aws_access_key_id,
        "aws_secret_access_key": aws_secret_access_key,
        "aws_session_token": aws_session_token,
    }
    if aws_config_file or sso_cache_dir:
        kwargs["botocore_session"] = _build_botocore_session(aws_config_file, sso_cache_dir)
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


def sync_sso_profiles(
    aws_config_file: str,
    sso_cache_dir: str,
) -> int:
    """Read SSO cache tokens and auto-generate profile entries for all accessible accounts/roles.

    For each valid (non-expired) SSO token found in *sso_cache_dir*, calls the AWS SSO API
    to list all accounts and permission sets the token holder can access, then writes matching
    profile entries to *aws_config_file*.

    Returns the number of profiles written (0 if no valid tokens found or on error).
    """
    from datetime import datetime, timezone

    cache_dir = Path(sso_cache_dir)
    config_path = Path(aws_config_file)

    if not cache_dir.exists():
        return 0

    token_files = list(cache_dir.glob("*.json"))
    if not token_files:
        return 0

    # Load existing config (preserve all current sections)
    parser = ConfigParser()
    if config_path.exists():
        parser.read(str(config_path))

    profiles_written = 0

    for token_file in token_files:
        try:
            token_data = json.loads(token_file.read_text())
        except Exception:
            continue

        # Skip expired tokens
        expires_at = token_data.get("expiresAt", "")
        try:
            exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if exp_dt <= datetime.now(timezone.utc):
                continue
        except Exception:
            continue

        access_token = token_data.get("accessToken")
        sso_region = token_data.get("region") or token_data.get("ssoRegion")
        sso_start_url = token_data.get("startUrl") or token_data.get("ssoStartUrl", "")
        session_name = token_data.get("clientId", "")

        if not access_token or not sso_region:
            continue

        # Derive sso-session name: prefer the key "startUrl" hostname, or file stem
        # Use the file stem (SHA1) as fallback, but try to read from config first
        sso_session_name = None
        for section in parser.sections():
            if section.startswith("sso-session "):
                if parser.get(section, "sso_start_url", fallback="") == sso_start_url:
                    sso_session_name = section[len("sso-session "):]
                    break

        try:
            sso_client = boto3.client("sso", region_name=sso_region)

            # List all accounts accessible with this token
            accounts: list[dict] = []
            paginator = sso_client.get_paginator("list_accounts")
            for page in paginator.paginate(accessToken=access_token):
                accounts.extend(page.get("accountList", []))

            for account in accounts:
                account_id = account.get("accountId", "")
                account_name = account.get("accountName", account_id)

                # List roles (permission sets) for this account
                roles: list[str] = []
                try:
                    role_paginator = sso_client.get_paginator("list_account_roles")
                    for page in role_paginator.paginate(
                        accessToken=access_token, accountId=account_id
                    ):
                        for role in page.get("roleList", []):
                            roles.append(role.get("roleName", ""))
                except Exception:
                    continue

                for role_name in roles:
                    if not role_name:
                        continue
                    # Build a profile name: "<account_name>-<role_name>" (sanitized)
                    profile_name = f"{account_name}-{role_name}".replace(" ", "_").replace("/", "-")
                    section = f"profile {profile_name}"

                    parser[section] = {
                        "sso_account_id": account_id,
                        "sso_role_name": role_name,
                        "region": "ap-southeast-3",
                        "output": "json",
                    }
                    if sso_session_name:
                        parser[section]["sso_session"] = sso_session_name
                    else:
                        parser[section]["sso_start_url"] = sso_start_url
                        parser[section]["sso_region"] = sso_region

                    profiles_written += 1

        except Exception as exc:
            logger.warning("sync_sso_profiles: error reading SSO accounts: %s", exc)
            continue

    if profiles_written > 0:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(str(config_path), "w") as fh:
            parser.write(fh)
        logger.info("sync_sso_profiles: wrote %d profiles to %s", profiles_written, aws_config_file)

    return profiles_written
