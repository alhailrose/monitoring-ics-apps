#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_PATH=""
TARGET_HOME="${HOME}"
OWNER=""

usage() {
  cat <<'EOF'
Usage:
  bootstrap_hcloud_user.sh --template <path> [--target-home <path>] [--owner <user:group>]

Description:
  Install an hcloud config template into target user's ~/.hcloud/config.json
  with safe file permissions.

Options:
  --template <path>     Sanitized template file (required).
  --target-home <path>  Target user home directory (default: current $HOME).
  --owner <user:group>  Optional chown target (useful when run with sudo).
  -h, --help            Show this help.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --template)
      TEMPLATE_PATH="${2:-}"
      shift 2
      ;;
    --target-home)
      TARGET_HOME="${2:-}"
      shift 2
      ;;
    --owner)
      OWNER="${2:-}"
      shift 2
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

if [[ -z "$TEMPLATE_PATH" ]]; then
  echo "Error: --template is required." >&2
  usage
  exit 1
fi

if [[ ! -f "$TEMPLATE_PATH" ]]; then
  echo "Error: template not found: $TEMPLATE_PATH" >&2
  exit 1
fi

target_dir="${TARGET_HOME}/.hcloud"
target_file="${target_dir}/config.json"

mkdir -p "$target_dir"
cp "$TEMPLATE_PATH" "$target_file"
chmod 700 "$target_dir"
chmod 600 "$target_file"

if [[ -n "$OWNER" ]]; then
  chown -R "$OWNER" "$target_dir"
fi

echo "Installed template to: $target_file"
echo
echo "Next steps on target user:"
echo "  1) hcloud configure sso --cli-profile=<source-profile>"
echo "  2) ${SCRIPT_DIR}/sync_sso_token.sh --source <source-profile>"
