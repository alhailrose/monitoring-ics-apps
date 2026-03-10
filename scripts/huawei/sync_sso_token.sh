#!/usr/bin/env bash
set -euo pipefail

CONFIG_PATH="${HCLOUD_CONFIG_PATH:-$HOME/.hcloud/config.json}"
SOURCE_PROFILE=""
VERIFY_PROFILES=""
FALLBACK_REGION="ap-southeast-4"

usage() {
  cat <<'EOF'
Usage:
  sync_sso_token.sh [--source <profile>] [--verify <p1,p2,...>] [--config <path>]

Description:
  Copy active SSO token data (access token + client id/secret) from one profile
  to all SSO profiles in ~/.hcloud/config.json so you do not need browser confirm
  one-by-one.

Options:
  --source <profile>     Source profile with active SSO token.
                         Default: current profile in config.json.
  --verify <p1,p2,...>   Optional quick verification using ECS ListServersDetails.
  --config <path>        Optional custom config path.
  -h, --help             Show this help.
EOF
}

epoch_to_human() {
  local val="$1"
  if [[ "$val" =~ ^[0-9]+$ ]]; then
    date -d "@$val" '+%Y-%m-%d %H:%M:%S %Z'
  else
    printf '%s\n' "$val"
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source)
      SOURCE_PROFILE="${2:-}"
      shift 2
      ;;
    --verify)
      VERIFY_PROFILES="${2:-}"
      shift 2
      ;;
    --config)
      CONFIG_PATH="${2:-}"
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

if ! command -v jq >/dev/null 2>&1; then
  echo "Error: jq is required." >&2
  exit 1
fi

if ! command -v hcloud >/dev/null 2>&1; then
  echo "Error: hcloud is required." >&2
  exit 1
fi

if [[ ! -f "$CONFIG_PATH" ]]; then
  echo "Error: config file not found: $CONFIG_PATH" >&2
  exit 1
fi

if [[ -z "$SOURCE_PROFILE" ]]; then
  SOURCE_PROFILE="$(jq -r '.current // empty' "$CONFIG_PATH")"
fi

if [[ -z "$SOURCE_PROFILE" ]]; then
  echo "Error: cannot resolve source profile. Use --source <profile>." >&2
  exit 1
fi

src_exists="$(jq -r --arg p "$SOURCE_PROFILE" '.profiles[] | select(.name==$p) | .name' "$CONFIG_PATH")"
if [[ -z "$src_exists" ]]; then
  echo "Error: source profile not found: $SOURCE_PROFILE" >&2
  exit 1
fi

src_mode="$(jq -r --arg p "$SOURCE_PROFILE" '.profiles[] | select(.name==$p) | .mode // ""' "$CONFIG_PATH")"
if [[ "$src_mode" != "SSO" ]]; then
  echo "Error: source profile is not SSO mode: $SOURCE_PROFILE ($src_mode)" >&2
  exit 1
fi

src_expiry="$(jq -r --arg p "$SOURCE_PROFILE" '.profiles[] | select(.name==$p) | .ssoAuth.accessTokenResult.expiresAt // ""' "$CONFIG_PATH")"
if [[ -z "$src_expiry" || "$src_expiry" == "null" ]]; then
  echo "Error: source profile has no access token expiry. Login first." >&2
  exit 1
fi

now_epoch="$(date +%s)"
if [[ "$src_expiry" =~ ^[0-9]+$ ]] && (( src_expiry <= now_epoch )); then
  echo "Error: source token already expired ($(epoch_to_human "$src_expiry")). Login first." >&2
  exit 1
fi

backup="${CONFIG_PATH}.bak-sync-$(date +%Y%m%d-%H%M%S)"
cp "$CONFIG_PATH" "$backup"

tmp_file="$(mktemp)"
trap 'rm -f "$tmp_file"' EXIT

jq --arg src "$SOURCE_PROFILE" '
  (.profiles[] | select(.name==$src) | .ssoAuth.accessTokenResult) as $tok
  | (.profiles[] | select(.name==$src) | .ssoAuth.clientIdAndSecret) as $client
  | .profiles |= map(
      if .mode=="SSO" then
        .ssoAuth.accessTokenResult = $tok
        | .ssoAuth.clientIdAndSecret = $client
      else . end
    )
' "$CONFIG_PATH" > "$tmp_file"
mv "$tmp_file" "$CONFIG_PATH"
chmod 600 "$CONFIG_PATH" 2>/dev/null || true

echo "Synced SSO token from: $SOURCE_PROFILE"
echo "Backup created: $backup"
echo
echo "Profile token expiry:"
jq -r '.profiles[] | select(.mode=="SSO") | [.name, (.ssoAuth.accessTokenResult.expiresAt // "-")] | @tsv' "$CONFIG_PATH" \
  | while IFS=$'\t' read -r name exp; do
      printf '  %-20s %s\n' "$name" "$(epoch_to_human "$exp")"
    done

if [[ -n "$VERIFY_PROFILES" ]]; then
  echo
  echo "Verification (ECS ListServersDetails --limit=1):"
  IFS=',' read -r -a profiles <<< "$VERIFY_PROFILES"
  for p in "${profiles[@]}"; do
    p="${p// /}"
    [[ -z "$p" ]] && continue
    region="$(jq -r --arg p "$p" '.profiles[] | select(.name==$p) | .region // ""' "$CONFIG_PATH")"
    if [[ -z "$region" || "$region" == "null" ]]; then
      region="$FALLBACK_REGION"
    fi
    out="$(hcloud ECS ListServersDetails --cli-profile="$p" --cli-region="$region" --limit=1 --cli-output=json 2>&1 || true)"
    cleaned="$(printf '%s\n' "$out" | sed -n '/^{/,$p')"
    if [[ -n "$cleaned" ]] && printf '%s\n' "$cleaned" | jq -e '.servers' >/dev/null 2>&1; then
      cnt="$(printf '%s\n' "$cleaned" | jq -r '.servers | length')"
      echo "  [OK]   $p (region=$region, servers_returned=$cnt)"
    else
      last_line="$(printf '%s\n' "$out" | tail -n 1)"
      echo "  [FAIL] $p (region=$region) -> $last_line"
    fi
  done
fi

echo
echo "Done."
