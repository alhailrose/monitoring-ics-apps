#!/usr/bin/env bash
# setup-aws-profiles.sh
# Setup AWS CLI profiles untuk monitoring-hub
# Jalankan: bash setup-aws-profiles.sh

set -euo pipefail

AWS_CONFIG="$HOME/.aws/config"
AWS_DIR="$HOME/.aws"

# ─── Warna ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${CYAN}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC}   $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERR]${NC}  $*"; }
header()  { echo -e "\n${BOLD}$*${NC}"; }

# ─── Cek prerequisite ─────────────────────────────────────────────────────────
check_prerequisites() {
    header "Cek prerequisites..."

    if ! command -v aws &>/dev/null; then
        error "AWS CLI tidak ditemukan. Install dulu: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
        exit 1
    fi
    success "AWS CLI: $(aws --version 2>&1 | head -1)"

    mkdir -p "$AWS_DIR"
    touch "$AWS_CONFIG"
    chmod 600 "$AWS_CONFIG"
}

# ─── Helper: cek apakah profile sudah ada ─────────────────────────────────────
profile_exists() {
    local profile="$1"
    grep -q "^\[profile ${profile}\]" "$AWS_CONFIG" 2>/dev/null
}

sso_session_exists() {
    local session="$1"
    grep -q "^\[sso-session ${session}\]" "$AWS_CONFIG" 2>/dev/null
}

# ─── Helper: tambah SSO session ───────────────────────────────────────────────
add_sso_session() {
    local name="$1"
    local start_url="$2"
    local sso_region="${3:-ap-southeast-1}"

    if sso_session_exists "$name"; then
        info "SSO session '${name}' sudah ada, skip."
        return
    fi

    cat >> "$AWS_CONFIG" <<EOF

[sso-session ${name}]
sso_start_url = ${start_url}
sso_region = ${sso_region}
sso_registration_scopes = sso:account:access
EOF
    success "Ditambahkan: sso-session ${name}"
}

# ─── Helper: tambah SSO profile ───────────────────────────────────────────────
add_sso_profile() {
    local profile="$1"
    local session="$2"
    local account_id="$3"
    local role_name="$4"
    local region="${5:-ap-southeast-3}"

    if profile_exists "$profile"; then
        info "Profile '${profile}' sudah ada, skip."
        return
    fi

    cat >> "$AWS_CONFIG" <<EOF

[profile ${profile}]
sso_session = ${session}
sso_account_id = ${account_id}
sso_role_name = ${role_name}
region = ${region}
EOF
    success "Ditambahkan: profile ${profile}"
}

# ─── Helper: tambah profile assumed role (login_session) ──────────────────────
add_assumed_role_profile() {
    local profile="$1"
    local region="$2"
    local description="$3"

    if profile_exists "$profile"; then
        info "Profile '${profile}' sudah ada, skip."
        return
    fi

    echo
    warn "Profile '${profile}' (${description}) menggunakan assumed role / IAM credentials."
    echo "  Masukkan ARN assumed role atau IAM user untuk profile ini."
    echo "  Contoh assumed role : arn:aws:sts::123456789012:assumed-role/role-name/session"
    echo "  Contoh IAM user     : arn:aws:iam::123456789012:user/username"
    echo "  Kosongkan dan tekan Enter untuk SKIP profile ini."
    echo -n "  ARN untuk '${profile}': "
    read -r user_arn

    if [[ -z "$user_arn" ]]; then
        warn "Skip profile '${profile}'."
        return
    fi

    cat >> "$AWS_CONFIG" <<EOF

[profile ${profile}]
login_session = ${user_arn}
region = ${region}
EOF
    success "Ditambahkan: profile ${profile} (login_session)"
    warn "  CATATAN: login_session tidak di-refresh otomatis oleh AWS CLI."
    warn "  Credentials ini perlu diupdate manual jika expired."
}

# ─── Helper: tambah IAM user profile ──────────────────────────────────────────
add_iam_user_profile() {
    local profile="$1"
    local region="$2"
    local description="$3"

    if profile_exists "$profile"; then
        info "Profile '${profile}' sudah ada, skip."
        return
    fi

    echo
    warn "Profile '${profile}' (${description}) menggunakan IAM user credentials."
    echo "  Masukkan Access Key ID dan Secret Access Key."
    echo "  Kosongkan Access Key dan tekan Enter untuk SKIP."
    echo -n "  AWS Access Key ID untuk '${profile}': "
    read -r access_key

    if [[ -z "$access_key" ]]; then
        warn "Skip profile '${profile}'."
        return
    fi

    echo -n "  AWS Secret Access Key: "
    read -rs secret_key
    echo

    aws configure set aws_access_key_id "$access_key" --profile "$profile"
    aws configure set aws_secret_access_key "$secret_key" --profile "$profile"
    aws configure set region "$region" --profile "$profile"
    success "Ditambahkan: profile ${profile} (IAM user)"
}

# ─── Setup: SSO Sessions ──────────────────────────────────────────────────────
setup_sso_sessions() {
    header "Setup SSO Sessions..."

    # sadewa-sso (internal ICS)
    add_sso_session "sadewa-sso" \
        "https://d-96670a95bf.awsapps.com/start/#/" \
        "ap-southeast-1"

    # aryanoble-sso
    add_sso_session "aryanoble-sso" \
        "https://aryanoble-sso.awsapps.com/start/#" \
        "ap-southeast-3"

    # Nabati
    add_sso_session "Nabati" \
        "https://ksni.awsapps.com/start/" \
        "ap-southeast-3"

    # HungryHub
    add_sso_session "HungryHub" \
        "https://d-9667bb79ef.awsapps.com/start/#" \
        "ap-southeast-1"
}

# ─── Setup: sadewa-sso profiles ───────────────────────────────────────────────
setup_sadewa_profiles() {
    header "Setup profiles sadewa-sso..."

    # Diamond
    add_sso_profile "Diamond"    "sadewa-sso" "464587839665" "aws_ms"  "ap-southeast-3"
    # Techmeister
    add_sso_profile "Techmeister" "sadewa-sso" "763944546283" "aws_ms" "ap-southeast-3"
    # Fresnel
    add_sso_profile "fresnel-ykai"    "sadewa-sso" "339712722804" "aws_ms"  "ap-southeast-3"
    add_sso_profile "fresnel-pialang" "sadewa-sso" "510940807875" "aws_ms"  "ap-southeast-3"
    add_sso_profile "fresnel-phoenix" "sadewa-sso" "197353582440" "aws_ms"  "ap-southeast-3"
    # KKI
    add_sso_profile "KKI"        "sadewa-sso" "471112835466" "aws_ms"  "ap-southeast-3"
    # BBI
    add_sso_profile "bbi"        "sadewa-sso" "940404076348" "aws_ctc" "ap-southeast-1"
    # eDot
    add_sso_profile "edot"       "sadewa-sso" "261622543538" "aws_ctc" "ap-southeast-1"
    # uCoal
    add_sso_profile "ucoal-appfuel"  "sadewa-sso" "593793048887" "aws_ctc" "ap-southeast-3"
    add_sso_profile "ucoal-legal"    "sadewa-sso" "622022425112" "aws_ctc" "ap-southeast-3"
    add_sso_profile "ucoal-minescape" "sadewa-sso" "595985021323" "aws_ctc" "ap-southeast-3"
    add_sso_profile "ucoal-prod"     "sadewa-sso" "637423564327" "aws_ctc" "ap-southeast-3"
    # Programa
    add_sso_profile "programa"   "sadewa-sso" "779060063462" "aws_ctc" "ap-southeast-3"
}

# ─── Setup: aryanoble-sso profiles ────────────────────────────────────────────
setup_aryanoble_profiles() {
    header "Setup profiles aryanoble-sso..."

    add_sso_profile "HRIS"             "aryanoble-sso" "493314732063" "ics-ms-rw"        "ap-southeast-3"
    add_sso_profile "fee-doctor"       "aryanoble-sso" "084828597777" "ics-ms-rw"        "ap-southeast-3"
    add_sso_profile "iris-dev"         "aryanoble-sso" "522814711071" "ics-ms-rw"        "ap-southeast-3"
    add_sso_profile "backup-hris"      "aryanoble-sso" "390403877301" "ics-ms-rw"        "ap-southeast-3"
    add_sso_profile "cis-erha"         "aryanoble-sso" "451916275465" "AWSReadOnlyAccess" "ap-southeast-3"
    add_sso_profile "connect-prod"     "aryanoble-sso" "620463044477" "AWSReadOnlyAccess" "ap-southeast-3"
    add_sso_profile "public-web"       "aryanoble-sso" "211125667194" "AWSReadOnlyAccess" "ap-southeast-3"
    add_sso_profile "dermies-max"      "aryanoble-sso" "637423567244" "AWSReadOnlyAccess" "ap-southeast-3"
    add_sso_profile "tgw"              "aryanoble-sso" "654654394944" "AWSReadOnlyAccess" "ap-southeast-3"
    add_sso_profile "iris-prod"        "aryanoble-sso" "522814722913" "AWSReadOnlyAccess" "ap-southeast-3"
    add_sso_profile "sfa"              "aryanoble-sso" "546158667544" "AWSReadOnlyAccess" "ap-southeast-3"
    add_sso_profile "erha-buddy"       "aryanoble-sso" "486250145105" "AWSReadOnlyAccess" "ap-southeast-3"
    add_sso_profile "centralized-s3"   "aryanoble-sso" "533267291161" "AWSReadOnlyAccess" "ap-southeast-3"
    add_sso_profile "dwh"              "aryanoble-sso" "084056488725" "AWSReadOnlyAccess" "ap-southeast-3"
    add_sso_profile "genero-empower"   "aryanoble-sso" "941377160792" "AWSReadOnlyAccess" "ap-southeast-3"
    add_sso_profile "genero-manufacture" "aryanoble-sso" "798344624633" "AWSReadOnlyAccess" "ap-southeast-3"
    add_sso_profile "arbel-master"     "aryanoble-sso" "477153214925" "AWSReadOnlyAccess" "ap-southeast-3"
}

# ─── Setup: Nabati profiles ───────────────────────────────────────────────────
setup_nabati_profiles() {
    header "Setup profiles Nabati (KSNI)..."

    add_sso_profile "ksni-master"       "Nabati" "317949653982" "ReadOnlyAccess" "ap-southeast-3"
    add_sso_profile "core-network-ksni" "Nabati" "207567759835" "ReadOnlyAccess" "ap-southeast-3"
    add_sso_profile "data-ksni"         "Nabati" "563983755611" "ReadOnlyAccess" "ap-southeast-3"
    add_sso_profile "dc-trans-ksni"     "Nabati" "982538789545" "ReadOnlyAccess" "ap-southeast-3"
    add_sso_profile "edin-ksni"         "Nabati" "288232812256" "ReadOnlyAccess" "ap-southeast-3"
    add_sso_profile "eds-ksni"          "Nabati" "701824263187" "ReadOnlyAccess" "ap-southeast-3"
    add_sso_profile "epc-ksni"          "Nabati" "783764594649" "ReadOnlyAccess" "ap-southeast-3"
    add_sso_profile "erp-ksni"          "Nabati" "992382445286" "ReadOnlyAccess" "ap-southeast-3"
    add_sso_profile "etl-ksni"          "Nabati" "654654389300" "ReadOnlyAccess" "ap-southeast-3"
    add_sso_profile "hc-assessment-ksni" "Nabati" "909927813600" "ReadOnlyAccess" "ap-southeast-3"
    add_sso_profile "hc-portal-ksni"    "Nabati" "954030863852" "ReadOnlyAccess" "ap-southeast-3"
    add_sso_profile "ngs-ksni"          "Nabati" "296062577084" "ReadOnlyAccess" "ap-southeast-3"
    add_sso_profile "outdig-ksni"       "Nabati" "465455994566" "ReadOnlyAccess" "ap-southeast-3"
    add_sso_profile "outlet-ksni"       "Nabati" "112555930839" "ReadOnlyAccess" "ap-southeast-3"
    add_sso_profile "q-devpro"          "Nabati" "528160043048" "ReadOnlyAccess" "ap-southeast-3"
    add_sso_profile "sales-support-pma" "Nabati" "734881641265" "ReadOnlyAccess" "ap-southeast-3"
    add_sso_profile "website-ksni"      "Nabati" "637423330091" "ReadOnlyAccess" "ap-southeast-3"
}

# ─── Setup: HungryHub profiles ────────────────────────────────────────────────
setup_hungryhub_profiles() {
    header "Setup profiles HungryHub..."

    add_sso_profile "prod-hungryhub" "HungryHub" "202255947274" "AWSReadOnlyAccess"  "ap-southeast-1"
    add_sso_profile "prod-audit"     "HungryHub" "454538763126" "AWSReadOnlyAccess"  "ap-southeast-1"
    add_sso_profile "prod-log"       "HungryHub" "993490993790" "AWSReadOnlyAccess"  "ap-southeast-1"
    add_sso_profile "prod-security"  "HungryHub" "380983552701" "AWSReadOnlyAccess"  "ap-southeast-1"
    add_sso_profile "prod-root"      "HungryHub" "891572013503" "AWSPowerUserAccess" "ap-southeast-1"
    add_sso_profile "prod-sandbox"   "HungryHub" "079994049689" "AWSReadOnlyAccess"  "ap-southeast-1"
}

# ─── Setup: profiles dengan login_session / IAM (perlu input manual) ──────────
setup_manual_profiles() {
    header "Setup profiles dengan credentials manual..."
    echo "  Profile berikut tidak menggunakan SSO — perlu input ARN atau credentials."

    # fresnel-master (assumed role)
    add_assumed_role_profile "fresnel-master" "ap-southeast-3" "Fresnel Master"

    # nikp (assumed role)
    add_assumed_role_profile "nikp" "ap-southeast-1" "NIKP"

    # sandbox (assumed role)
    add_assumed_role_profile "sandbox" "us-east-1" "Sandbox ICS"

    # rumahmedia (assumed role)
    add_assumed_role_profile "rumahmedia" "ap-southeast-2" "Rumahmedia"

    # asg (IAM user)
    add_iam_user_profile "asg" "ap-southeast-3" "Agung Sedayu Group"

    # arista-web (IAM user)
    add_iam_user_profile "arista-web" "ap-southeast-1" "Arista Web"
}

# ─── Set default region ───────────────────────────────────────────────────────
setup_default() {
    header "Setup default region..."

    if grep -q "^\[default\]" "$AWS_CONFIG" 2>/dev/null; then
        info "Blok [default] sudah ada, skip."
    else
        cat >> "$AWS_CONFIG" <<'EOF'

[default]
region = ap-southeast-3
output = json
cli_pager =
cli_binary_format = raw-in-base64-out
EOF
        success "Ditambahkan: [default] region ap-southeast-3"
    fi
}

# ─── Login SSO ────────────────────────────────────────────────────────────────
prompt_sso_login() {
    header "Login SSO..."
    echo
    echo "  Setelah setup selesai, kamu perlu login ke setiap SSO session."
    echo "  Jalankan perintah berikut satu per satu:"
    echo
    echo -e "  ${CYAN}aws sso login --sso-session sadewa-sso${NC}"
    echo -e "  ${CYAN}aws sso login --sso-session aryanoble-sso${NC}"
    echo -e "  ${CYAN}aws sso login --sso-session Nabati${NC}"
    echo -e "  ${CYAN}aws sso login --sso-session HungryHub${NC}"
    echo
    echo "  Browser akan terbuka untuk autentikasi. Setelah login, token berlaku ±8 jam."
    echo
    echo -n "  Mau login SSO sekarang? [sadewa-sso] (y/N): "
    read -r do_login
    if [[ "$do_login" =~ ^[Yy]$ ]]; then
        info "Login sadewa-sso..."
        aws sso login --sso-session sadewa-sso || warn "Login sadewa-sso gagal, coba manual."
    fi
}

# ─── Verifikasi ───────────────────────────────────────────────────────────────
verify_setup() {
    header "Verifikasi..."

    local total
    total=$(grep -c "^\[profile " "$AWS_CONFIG" 2>/dev/null || echo 0)
    success "Total profiles terkonfigurasi: ${total}"

    echo
    info "Cek profile SSO (contoh: connect-prod)..."
    if aws sts get-caller-identity --profile connect-prod &>/dev/null; then
        success "Profile connect-prod OK"
    else
        warn "Profile connect-prod tidak bisa diakses. Mungkin perlu login SSO dulu."
        echo "  Jalankan: aws sso login --sso-session aryanoble-sso"
    fi
}

# ─── Main ─────────────────────────────────────────────────────────────────────
main() {
    echo -e "${BOLD}"
    echo "╔═══════════════════════════════════════════╗"
    echo "║   AWS Profiles Setup - monitoring-hub     ║"
    echo "╚═══════════════════════════════════════════╝"
    echo -e "${NC}"

    echo "  Script ini akan menambahkan AWS CLI profiles ke: ${AWS_CONFIG}"
    echo "  Profile yang sudah ada tidak akan ditimpa."
    echo
    echo -n "  Lanjutkan? (y/N): "
    read -r confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo "  Dibatalkan."
        exit 0
    fi

    check_prerequisites
    setup_default
    setup_sso_sessions
    setup_sadewa_profiles
    setup_aryanoble_profiles
    setup_nabati_profiles
    setup_hungryhub_profiles
    setup_manual_profiles
    prompt_sso_login
    verify_setup

    echo
    echo -e "${GREEN}${BOLD}Setup selesai!${NC}"
    echo
    echo "  Langkah selanjutnya:"
    echo "  1. Login ke SSO sessions yang dibutuhkan:"
    echo -e "     ${CYAN}aws sso login --sso-session sadewa-sso${NC}"
    echo -e "     ${CYAN}aws sso login --sso-session aryanoble-sso${NC}"
    echo -e "     ${CYAN}aws sso login --sso-session Nabati${NC}"
    echo -e "     ${CYAN}aws sso login --sso-session HungryHub${NC}"
    echo "  2. Jalankan monitoring-hub:"
    echo -e "     ${CYAN}monitoring-hub${NC}"
    echo
}

main "$@"
