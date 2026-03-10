#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXPORT_SCRIPT="${SCRIPT_DIR}/export_hcloud_template.sh"
BOOTSTRAP_SCRIPT="${SCRIPT_DIR}/bootstrap_hcloud_user.sh"
SYNC_SCRIPT="${SCRIPT_DIR}/sync_sso_token.sh"

TARGET_USER=""
TARGET_HOME=""
SOURCE_PROFILE=""
TEMPLATE_OUT=""
OWNER=""
EXECUTE_LOGIN_SYNC="false"

usage() {
  cat <<'EOF'
Usage:
  onboard_hcloud_user.sh --target-user <username> --source-profile <profile>
                         [--target-home <path>] [--template-out <path>]
                         [--owner <user:group>] [--execute-login-sync]

Description:
  End-to-end helper to onboard Huawei hcloud profiles for another user.

  Steps performed:
    1) Export sanitized template from current user's ~/.hcloud/config.json
    2) Install template into target user's ~/.hcloud/config.json
    3) Print (or run) login + token sync commands for target user

Options:
  --target-user <username>       Target OS user (required)
  --source-profile <profile>     Source SSO profile to login/sync (required)
  --target-home <path>           Target home dir (default: from /etc/passwd)
  --template-out <path>          Output template path (default: /tmp/hcloud-config-template-<user>-<timestamp>.json)
  --owner <user:group>           Owner for target ~/.hcloud files (default: <target-user>:<target-user>)
  --execute-login-sync           Run login+sync commands automatically as target user
  -h, --help                     Show this help
EOF
}

resolve_home_from_passwd() {
  local user="$1"
  local home_dir
  home_dir="$(getent passwd "$user" | cut -d: -f6)"
  if [[ -n "$home_dir" ]]; then
    printf '%s\n' "$home_dir"
    return
  fi
  printf '/home/%s\n' "$user"
}

run_as_target() {
  local user="$1"
  shift

  if [[ "$(id -un)" == "$user" ]]; then
    "$@"
    return
  fi

  if [[ "${EUID}" -eq 0 ]]; then
    su - "$user" -c "$(printf '%q ' "$@")"
    return
  fi

  if command -v sudo >/dev/null 2>&1; then
    sudo -u "$user" -H "$@"
    return
  fi

  echo "Error: need sudo (or root) to run command as user '$user'." >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target-user)
      TARGET_USER="${2:-}"
      shift 2
      ;;
    --target-home)
      TARGET_HOME="${2:-}"
      shift 2
      ;;
    --source-profile)
      SOURCE_PROFILE="${2:-}"
      shift 2
      ;;
    --template-out)
      TEMPLATE_OUT="${2:-}"
      shift 2
      ;;
    --owner)
      OWNER="${2:-}"
      shift 2
      ;;
    --execute-login-sync)
      EXECUTE_LOGIN_SYNC="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$TARGET_USER" || -z "$SOURCE_PROFILE" ]]; then
  echo "Error: --target-user and --source-profile are required." >&2
  usage
  exit 1
fi

if [[ ! -x "$EXPORT_SCRIPT" || ! -x "$BOOTSTRAP_SCRIPT" || ! -x "$SYNC_SCRIPT" ]]; then
  echo "Error: required helper scripts are missing or not executable in scripts/huawei/." >&2
  exit 1
fi

if [[ -z "$TARGET_HOME" ]]; then
  TARGET_HOME="$(resolve_home_from_passwd "$TARGET_USER")"
fi

if [[ -z "$TEMPLATE_OUT" ]]; then
  TEMPLATE_OUT="/tmp/hcloud-config-template-${TARGET_USER}-$(date +%Y%m%d-%H%M%S).json"
fi

if [[ -z "$OWNER" ]]; then
  OWNER="${TARGET_USER}:${TARGET_USER}"
fi

echo "[1/3] Export sanitized template"
"$EXPORT_SCRIPT" --output "$TEMPLATE_OUT"

echo "[2/3] Install template to target user"
bootstrap_cmd=(
  "$BOOTSTRAP_SCRIPT"
  --template "$TEMPLATE_OUT"
  --target-home "$TARGET_HOME"
  --owner "$OWNER"
)

if [[ "$(id -un)" == "$TARGET_USER" || "${EUID}" -eq 0 ]]; then
  "${bootstrap_cmd[@]}"
elif command -v sudo >/dev/null 2>&1; then
  sudo "${bootstrap_cmd[@]}"
else
  echo "Error: need sudo (or root) to install config for '$TARGET_USER'." >&2
  exit 1
fi

echo "[3/3] Login + sync token"
login_cmd=(hcloud configure sso --cli-profile="$SOURCE_PROFILE")
sync_cmd=("$SYNC_SCRIPT" --source "$SOURCE_PROFILE")

if [[ "$EXECUTE_LOGIN_SYNC" == "true" ]]; then
  run_as_target "$TARGET_USER" "${login_cmd[@]}"
  run_as_target "$TARGET_USER" "${sync_cmd[@]}"
else
  echo
  echo "Run these commands as ${TARGET_USER}:"
  echo "  ${login_cmd[*]}"
  echo "  ${sync_cmd[*]}"
fi

echo
echo "Onboarding setup completed for user: ${TARGET_USER}"
