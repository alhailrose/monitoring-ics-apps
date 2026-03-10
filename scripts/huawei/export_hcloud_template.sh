#!/usr/bin/env bash
set -euo pipefail

CONFIG_PATH="${HCLOUD_CONFIG_PATH:-$HOME/.hcloud/config.json}"
OUTPUT_PATH="./hcloud-config-template.json"

usage() {
  cat <<'EOF'
Usage:
  export_hcloud_template.sh [--config <path>] [--output <path>]

Description:
  Export a sanitized Huawei hcloud config template by removing active
  SSO token and client secret fields from all SSO profiles.

Options:
  --config <path>   Input config path (default: ~/.hcloud/config.json)
  --output <path>   Output template file (default: ./hcloud-config-template.json)
  -h, --help        Show this help.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config)
      CONFIG_PATH="${2:-}"
      shift 2
      ;;
    --output)
      OUTPUT_PATH="${2:-}"
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

if [[ ! -f "$CONFIG_PATH" ]]; then
  echo "Error: config file not found: $CONFIG_PATH" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT_PATH")"
tmp_file="$(mktemp)"
trap 'rm -f "$tmp_file"' EXIT

jq '
  .profiles |= map(
    if .mode=="SSO" then
      .ssoAuth = (.ssoAuth // {})
      | .ssoAuth.accessTokenResult = null
      | .ssoAuth.clientIdAndSecret = null
    else . end
  )
' "$CONFIG_PATH" > "$tmp_file"

mv "$tmp_file" "$OUTPUT_PATH"
chmod 600 "$OUTPUT_PATH" 2>/dev/null || true

echo "Template exported to: $OUTPUT_PATH"
echo "Sensitive SSO token fields were removed."
