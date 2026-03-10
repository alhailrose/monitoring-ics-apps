#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROFILE_MAP_FILE="${SCRIPT_DIR}/hcloud-profile-map.json"
SYNC_SCRIPT="${SCRIPT_DIR}/sync_sso_token.sh"
TARGET_CONFIG_DIR="${HCLOUD_CONFIG_DIR:-$HOME/.hcloud}"
TARGET_CONFIG_FILE="${TARGET_CONFIG_DIR}/config.json"
SOURCE_PROFILE="${1:-dh_prod_erp-ro}"

usage() {
  cat <<'EOF'
Usage:
  setup_hcloud_profiles.sh [source_profile]

Description:
  Install predefined Huawei SSO profile mapping, then run one SSO login and
  sync token to all SSO profiles automatically.

Examples:
  ./scripts/huawei/setup_hcloud_profiles.sh
  ./scripts/huawei/setup_hcloud_profiles.sh dh_prod_erp-ro
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "Error: jq is required." >&2
  exit 1
fi

if ! command -v hcloud >/dev/null 2>&1; then
  echo "Error: hcloud is required." >&2
  exit 1
fi

if [[ ! -f "$PROFILE_MAP_FILE" ]]; then
  echo "Error: profile map not found: $PROFILE_MAP_FILE" >&2
  exit 1
fi

if [[ ! -x "$SYNC_SCRIPT" ]]; then
  echo "Error: sync script not executable: $SYNC_SCRIPT" >&2
  exit 1
fi

if ! jq -e --arg p "$SOURCE_PROFILE" '.profiles[] | select(.name==$p)' "$PROFILE_MAP_FILE" >/dev/null; then
  echo "Error: source profile '$SOURCE_PROFILE' not found in $PROFILE_MAP_FILE" >&2
  exit 1
fi

mkdir -p "$TARGET_CONFIG_DIR"

tmp_file="$(mktemp)"
cleanup() {
  rm -f "$tmp_file"
}
trap cleanup EXIT

if [[ -f "$TARGET_CONFIG_FILE" ]]; then
  backup="${TARGET_CONFIG_FILE}.bak-$(date +%Y%m%d-%H%M%S)"
  cp "$TARGET_CONFIG_FILE" "$backup"
  echo "Existing config backed up to: $backup"
fi

jq --arg src "$SOURCE_PROFILE" '
  (if type=="array" then . else (.profiles // []) end) as $profiles
  | {
      current: $src,
      profiles: (
        $profiles
        | map(
            .accessKeyId = ""
            | .secretAccessKey = ""
            | .securityToken = ""
            | .ssoAuth = ((.ssoAuth // {})
                | .accessTokenResult = null
                | .clientIdAndSecret = null
                | .stsToken = null)
          )
      )
    }
' "$PROFILE_MAP_FILE" > "$tmp_file"

mv "$tmp_file" "$TARGET_CONFIG_FILE"
chmod 700 "$TARGET_CONFIG_DIR"
chmod 600 "$TARGET_CONFIG_FILE"

if ! hcloud configure show --cli-profile="$SOURCE_PROFILE" --cli-output=json >/dev/null 2>&1; then
  if [[ -n "${backup:-}" && -f "$backup" ]]; then
    cp "$backup" "$TARGET_CONFIG_FILE"
  fi
  echo "Error: generated $TARGET_CONFIG_FILE cannot be parsed by hcloud." >&2
  echo "Please check hcloud version and profile map format." >&2
  exit 1
fi

echo "Installed Huawei profile mapping to: $TARGET_CONFIG_FILE"
echo
echo "Step 1/2: Login SSO (single profile)"
hcloud configure sso --cli-profile="$SOURCE_PROFILE"

echo
echo "Step 2/2: Sync token to all SSO profiles"
"$SYNC_SCRIPT" --source "$SOURCE_PROFILE"

echo
echo "Done. You can run:"
echo "  monitoring-hub --check huawei-ecs-util --profile $SOURCE_PROFILE --region ap-southeast-4"
