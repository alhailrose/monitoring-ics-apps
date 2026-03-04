"""Config schema validation helpers."""


def validate_customer_config(raw):
    if not isinstance(raw, dict):
        raise ValueError("customer config must be an object")

    if not raw.get("customer_id"):
        raise ValueError("customer_id is required")

    accounts = raw.get("accounts")
    if not isinstance(accounts, list) or not accounts:
        raise ValueError("accounts must be a non-empty list")

    for account in accounts:
        if not isinstance(account, dict):
            raise ValueError("account entry must be an object")
        if not account.get("profile") and not account.get("account_id"):
            raise ValueError("profile or account_id is required in account entry")

    return raw
