"""AWS auth helper placeholders for AssumeRole workflow."""


def resolve_execution_identity(profile_name=None, role_arn=None):
    execution_mode = "assume-role" if role_arn else "profile"
    return {
        "execution_mode": execution_mode,
        "profile_name": profile_name,
        "role_arn": role_arn,
    }
