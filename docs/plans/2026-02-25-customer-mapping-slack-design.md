# Customer Mapping & Slack Integration Design

Date: 2026-02-25

## Overview

Pemetaan semua AWS profiles ke customer configs, redesign TUI menu, dan integrasi Slack prompt per customer.

## Customer Mapping (14 customers)

### SSO Multi-Account
| Customer | SSO Session | Profiles | Region |
|---|---|---|---|
| Aryanoble | aryanoble-sso | 17 akun | ap-southeast-3 |
| Nabati | Nabati | 17 akun | ap-southeast-3 |
| Fresnel | sadewa-sso | 4 akun (fresnel-ykai, fresnel-pialang, fresnel-phoenix, fresnel-master*) | ap-southeast-3 |

*fresnel-master = non-SSO tapi milik customer Fresnel

### SSO Single-Account (via sadewa-sso)
| Customer | Profile | Account ID | Region |
|---|---|---|---|
| Diamond | Diamond | 464587839665 | ap-southeast-3 |
| Techmeister | Techmeister | 763944546283 | ap-southeast-3 |
| KKI | KKI | 471112835466 | ap-southeast-3 |
| BBI | bbi | 940404076348 | ap-southeast-1 |
| Edot | edot | 261622543538 | ap-southeast-1 |

### SSO Single-Account
| Customer | Profile | Account ID | Region |
|---|---|---|---|
| HungryHub | prod-hungryhub | 202255947274 | ap-southeast-1 |

### Non-SSO Single-Account
| Customer | Profile | Region |
|---|---|---|
| NIKP | nikp | ap-southeast-1 |
| Sandbox | sandbox | us-east-1 |
| RumahMedia | rumahmedia | ap-southeast-2 |
| ASG | asg | ap-southeast-3 |
| Arista Web | arista-web | ap-southeast-1 |

## TUI Menu Redesign

### Before
```
Main Menu:
  > Single Check     (1 check, 1 profile)
  > All Checks       (all checks, multi-profile)
  > Arbel Check      (Aryanoble-specific: RDS/Alarm/Budget/Backup)
  > Cost Report
  > Settings
```

### After
```
Main Menu:
  > Quick Check        (default All Checks, pilih profile(s) + checks)
  > Customer Report    (pilih customer → checks dari YAML → Slack prompt)
  > Cost Report        (tetap)
  > Settings           (tetap)
```

### Quick Check Flow
1. Pilih check(s) — default semua tercentang
2. Pilih profile(s) — bisa 1 atau banyak
3. Run parallel → report

### Customer Report Flow
1. Pilih customer dari list (auto-scan configs/customers/*.yaml)
2. **Aryanoble** → sub-menu: RDS Monitoring / Alarm Verification / Budget / Backup / All
3. **Customer lain** → jalankan checks dari YAML, pilih akun (default semua)
4. Tampilkan report
5. Prompt: "Kirim ke Slack [customer]? [y/n]"

## Customer YAML Schema

```yaml
customer_id: <id>              # unique, matches filename
display_name: <name>           # for reports/TUI
sso_session: <session|null>    # null for non-SSO

slack:
  webhook_url: ""
  channel: ""
  enabled: false

checks:                        # checks to run in Customer Report mode
  -- cost
  - guardduty

accounts:
  - profile: <aws-profile>
    account_id: "<id>"
    display_name: "<name>"
    region: <region>           # optional override
```

## Slack Flow

- Customer YAML has `slack.webhook_url`, `slack.channel`, `slack.enabled`
- After Customer Report completes, if `slack.enabled` and `webhook_url` set:
  - Prompt operator: "Kirim ke Slack [customer] ([channel])? [y/n]"
  - If yes → send aggregated report via `send_to_webhook()`
- CLI `--customer <id>` has same behavior

## Files to Create/Modify

### New files
- `configs/customers/*.yaml` — 13 new customer configs
- `src/app/tui/flows/customer.py` — Customer Report TUI flow

### Modified files
- `configs/customers/aryanoble.yaml` — add missing profiles from SSO
- `src/app/tui/interactive.py` — redesign main menu
- `src/configs/loader.py` — add `find_customer_by_profile()` utility
- `src/core/runtime/customer_runner.py` — ensure TUI compatibility

## Guide: Adding New Customer

1. Create `configs/customers/<customer_id>.yaml`
2. Fill in: customer_id, display_name, sso_session, accounts
3. Add checks list (available: health, cost, guardduty, cloudwatch, notifications, backup, daily-arbel, daily-budget, ec2list)
4. Configure Slack: set webhook_url, channel, enabled: true
5. Validate: `monitoring-hub customer validate <customer_id>`
