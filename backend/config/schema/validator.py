"""Config schema validation helpers."""


def validate_customer_config(raw):
    if not isinstance(raw, dict):
        raise ValueError("customer config must be an object")

    if not raw.get("customer_id"):
        raise ValueError("customer_id is required")

    accounts = raw.get("accounts")
    if not isinstance(accounts, list) or not accounts:
        raise ValueError("accounts must be a non-empty list")

    for idx, account in enumerate(accounts):
        if not isinstance(account, dict):
            raise ValueError("account entry must be an object")

        profile = account.get("profile")

        # Only require profile - account_id is optional (can be filled manually or left empty)
        if not profile:
            raise ValueError(f"account[{idx}] missing profile")

    return raw
