#!/usr/bin/env python3
"""
AWS Monitoring Hub
Centralized monitoring for AWS security and operations
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone
from time import monotonic
import boto3
from botocore.exceptions import BotoCoreError, ClientError
import questionary
from questionary import Style
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from checks.health_events import HealthChecker
from checks.cost_anomalies import CostAnomalyChecker
from checks.guardduty import GuardDutyChecker
from checks.cloudwatch_alarms import CloudWatchAlarmChecker
from checks.notifications import NotificationChecker
from checks.backup_status import BackupStatusChecker
from checks.rds_metrics import RDSMetricsChecker
from checks.ec2_list import EC2ListChecker

# Profile groups with account IDs
PROFILE_GROUPS = {
    'nabati': {
        'core-network-ksni': '207567759835',
        'data-ksni': '563983755611', 
        'dc-trans-ksni': '982538789545',
        'edin-ksni': '288232812256',
        'eds-ksni': '701824263187',
        'epc-ksni': '783764594649',
        'erp-ksni': '992382445286',
        'etl-ksni': '654654389300',
        'hc-assessment-ksni': '909927813600',
        'hc-portal-ksni': '954030863852',
        'ksni-master': '317949653982',
        'ngs-ksni': '296062577084',
        'outdig-ksni': '465455994566',
        'outlet-ksni': '112555930839',
        'q-devpro': '528160043048',
        'sales-support-pma': '734881641265',
        'website-ksni': '637423330091'
    },
    'sadewa': {
        'Diamond': '464587839665',
        'Techmeister': '763944546283',
        'KKI': '471112835466',
        'iris-dev': '522814711071',
        'bbi':'940404076348',
        'edot':'261622543538',
        'fresnel-phoenix':'197353582440',
        'fresnel-pialang':'510940807875',
        'fresnel-ykai':'339712722804'
    },
    'aryanoble-backup': {
        'HRIS': '493314732063',
        'fee-doctor': '084828597777',
        'cis-erha': '451916275465',
        'connect-prod': '620463044477',
        'public-web': '211125667194',
        'dermies-max': '637423567244',
        'tgw': '654654394944',
        'iris-prod': '522814722913',
        'sfa': '546158667544',
        'erha-buddy': '486250145105',
        'centralized-s3': '533267291161',
        'backup-hris': '390403877301'
    },
    'hungryhub': {
        'prod': '202255947274'
    },
     'master': {
        'arbel-master': '477153214925'
    },
    'ics': {
        'nikp': '038361715485',
        'sandbox': '339712808680',
        'rumahmedia': '975050309328',
        'asg': '264887202956',
        'fresnel-master':'466650104955'
        
    }
}

AVAILABLE_CHECKS = {
    'health': HealthChecker,
    'cost': CostAnomalyChecker,
    'guardduty': GuardDutyChecker,
    'cloudwatch': CloudWatchAlarmChecker,
    'notifications': NotificationChecker,
    'backup': BackupStatusChecker,
    'rds': RDSMetricsChecker,
    'ec2list': EC2ListChecker,
}

# Checks to run in --all mode (excludes health only)
ALL_MODE_CHECKS = {
    'cost': CostAnomalyChecker,
    'guardduty': GuardDutyChecker,
    'cloudwatch': CloudWatchAlarmChecker,
    'notifications': NotificationChecker,
    'backup': BackupStatusChecker,
    'rds': RDSMetricsChecker,
}

INTERRUPT_EXIT_WINDOW = 1.5
_last_interrupt_ts = 0.0

# Minimal ANSI helpers for a brighter CLI without extra deps
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"

console = Console()


def resolve_region(profile_list, override_region):
    """Resolve region using CLI override, then profile config, then fallback."""
    if override_region:
        return override_region
    for prof in profile_list:
        try:
            session = boto3.Session(profile_name=prof)
            if session.region_name:
                return session.region_name
        except Exception:
            continue
    return 'ap-southeast-3'

def get_account_id(profile):
    """Get account ID for a profile"""
    for group in PROFILE_GROUPS.values():
        if profile in group:
            return group[profile]
    return "Unknown"


def run_individual_check(check_name, profile, region):
    """Run individual check with detailed output"""
    if check_name not in AVAILABLE_CHECKS:
        console.print(f"[bold red]ERROR[/bold red]: Unknown check '{check_name}'")
        console.print(f"Available checks: {', '.join(AVAILABLE_CHECKS.keys())}")
        return

    account_id = get_account_id(profile)
    checker_class = AVAILABLE_CHECKS[check_name]
    checker = checker_class(region=region)

    header = Panel(
        f"[bold]{check_name.upper()}[/bold] untuk [cyan]{profile}[/cyan]\n"
        f"Account: [bold]{account_id}[/bold]\n"
        f"Region: [green]{region}[/green]",
        border_style="cyan",
        title="Single Check",
        padding=(1, 2),
    )
    console.print(header)

    try:
        results = checker.check(profile, account_id)
        report = checker.format_report(results)
        console.print(Rule(style="cyan"))
        console.print(report)
    except (BotoCoreError, ClientError) as exc:
        console.print(f"[bold red]ERROR[/bold red]: Failed to run {check_name} untuk {profile}: {exc}")
    except Exception as exc:
        console.print(f"[bold red]ERROR[/bold red]: Unexpected failure running {check_name} untuk {profile}: {exc}")


def run_group_specific(check_name, profiles, region, group_name=None):
    """Run a specific check across multiple profiles (for backup/rds WhatsApp)."""
    console.print(Panel(
        f"[bold]{check_name.upper()}[/bold] untuk {len(profiles)} profil\n"
        f"Group: [cyan]{group_name or '-'}[/cyan]\n"
        f"Region: [green]{region}[/green]",
        border_style="cyan",
        title="Multi-Account",
        padding=(1, 2),
    ))

    # Mirror check_backup header: 24h window and current time in WIB
    if check_name == 'backup':
        now_utc = datetime.now(timezone.utc)
        since_utc = now_utc - timedelta(hours=24)
        now_jkt = now_utc.astimezone(timezone(timedelta(hours=7)))
        since_jkt = since_utc.astimezone(timezone(timedelta(hours=7)))
        console.print(f"[bold]Periode[/bold] : 24 jam terakhir (sejak: {since_jkt:%Y-%m-%d %H:%M:%S %Z})")
        console.print(f"[bold]Time   [/bold] : {now_jkt:%Y-%m-%d %H:%M:%S %Z}\n")

    all_results = {}
    for profile in profiles:
        account_id = get_account_id(profile)
        console.print(f"[cyan]→[/cyan] Checking [bold]{profile}[/bold]...")
        checker_class = AVAILABLE_CHECKS[check_name]
        checker = checker_class(region=region)
        try:
            results = checker.check(profile, account_id)
        except (BotoCoreError, ClientError) as exc:
            results = {'status': 'error', 'error': str(exc)}
        except Exception as exc:
            results = {'status': 'error', 'error': str(exc)}
        all_results[profile] = {check_name: results}
        # For non-backup/rds checks, print each profile's report
        if check_name not in ['backup', 'rds']:
            report = checker.format_report(results)
            print(f"\n[{profile}]")
            print(report)
            print("")

    if check_name == 'backup':
        date_str = datetime.now(timezone(timedelta(hours=7))).strftime("%d-%m-%Y")
        whatsapp = build_whatsapp_backup(date_str, all_results)
        print("\nWHATSAPP MESSAGE (READY TO SEND)")
        print("--backup")
        print(whatsapp)

        # Detailed per-account view (structured tables) for Aryanoble group
        print("\n================ DETAIL PER ACCOUNT (BACKUP, 24H WINDOW) ================")
        for profile in profiles:
            res = all_results.get(profile, {}).get('backup')
            if not res:
                continue
            acct = res.get('account_id', get_account_id(profile))
            print(f"\n== {profile} | Account: {acct} | Region: {res.get('region', region)} ==")
            print(f"Checked at: {res.get('checked_at_utc')} | Window start: {res.get('window_start_utc')}")
            print(f"Jobs (24h): total {res.get('total_jobs',0)} | completed {res.get('completed_jobs',0)} | failed {res.get('failed_jobs',0)} | expired {res.get('expired_jobs',0)}")

            jobs = res.get('job_details', [])
            if jobs:
                print("AWS BACKUP JOBS (24h, max 20 baris):")
                header = f"{'JobID':36}  {'Status':10} {'Type':8} {'Created (WIB)':20} {'Resource':22} {'ResName':22} {'Reason':30}"
                print(header)
                print("-" * len(header))
                for j in jobs[:20]:
                    ts = j.get('created_wib') or j.get('created')
                    ts_str = ts.strftime('%Y-%m-%d %H:%M') if hasattr(ts, 'strftime') else str(ts)
                    job_id = (j.get('job_id','') or '')[:36]
                    status = (j.get('state','') or '')[:10]
                    rtype = (j.get('type','') or '')[:8]
                    res_label = (j.get('resource_label','') or '')[:22]
                    res_full = (j.get('resource','') or '')[:22]
                    reason = (j.get('reason','') or '')[:30]
                    print(f"{job_id:36}  {status:10} {rtype:8} {ts_str:20} {res_label:22} {res_full:22} {reason:30}")
            else:
                print("AWS BACKUP JOBS: (none)")

            plans = res.get('backup_plans', [])
            if plans:
                print("Backup plans (maks 10):")
                for p in plans[:10]:
                    print(f"  - {p}")
            vaults = res.get('vaults', [])
            if vaults:
                print("Vaults:")
                for v in vaults:
                    if v.get('error'):
                        print(f"  - {v['vault_name']}: ERROR {v['error']}")
                    else:
                        print(f"  - {v['vault_name']}: {v.get('recovery_points_24h',0)} RP 24h; total {v.get('total_recovery_points',0)}")
            print("")
    elif check_name == 'rds':
        whatsapp = build_whatsapp_rds(all_results)
        print("\nWHATSAPP MESSAGE (READY TO SEND)")
        print("--rds")
        print(whatsapp)


def summarize_health(results):
    total = results.get('total_events', 0)
    action_req = results.get('action_required', 0)
    status = 'ATTENTION REQUIRED' if action_req > 0 else 'OK'
    detail = f"{total} events; {action_req} need action"
    return status, detail


def summarize_cost(results):
    if results.get('status') == 'error':
        return 'ERROR', results.get('error', 'Unknown error')
    monitors = results.get('total_monitors', 0)
    anomalies = results.get('total_anomalies', 0)
    status = 'ANOMALIES DETECTED' if anomalies > 0 else 'OK'
    detail = f"{monitors} monitors; {anomalies} anomalies (30d)"
    return status, detail


def summarize_guardduty(results):
    if results.get('status') == 'error':
        return 'ERROR', results.get('error', 'Unknown error')
    if results['status'] == 'disabled':
        return 'DISABLED', 'GuardDuty not enabled'
    status = 'ATTENTION REQUIRED' if results.get('findings', 0) > 0 else 'OK'
    detail = f"{results.get('findings', 0)} findings today"
    return status, detail


def summarize_cloudwatch(results):
    if results.get('status') == 'error':
        return 'ERROR', results.get('error', 'Unknown error')
    status = 'ATTENTION REQUIRED' if results.get('count', 0) > 0 else 'OK'
    detail = f"{results.get('count', 0)} alarm(s) in ALARM"
    return status, detail


def summarize_notifications(results):
    if results.get('status') == 'error':
        return 'ERROR', results.get('error', 'Unknown error')
    status = 'OK' if results.get('today_count', 0) == 0 else 'NEW'
    detail = f"{results.get('today_count', 0)} new today; {results.get('total_managed', 0)} total managed"
    return status, detail


def summarize_backup(results):
    if results.get('status') == 'error':
        return 'ERROR', results.get('error', 'Unknown error')
    issues = results.get('issues', [])
    status = 'ATTENTION REQUIRED' if issues else 'OK'
    detail = f"Jobs:{results.get('total_jobs', 0)} completed:{results.get('completed_jobs', 0)} failed:{results.get('failed_jobs', 0)}"
    return status, detail


def summarize_rds(results):
    if results.get('status') in ['error', 'skipped']:
        return results.get('status').upper(), results.get('reason', results.get('error', ''))
    status = 'ATTENTION REQUIRED' if results.get('status') == 'ATTENTION REQUIRED' else 'OK'
    instances = results.get('instances', {})
    warn_count = 0
    for data in instances.values():
        for m in data.get('metrics', {}).values():
            if m.get('status') == 'warn':
                warn_count += 1
    detail = f"Instances:{len(instances)} warnings:{warn_count}"
    return status, detail


SUMMARY_MAP = {
    'health': summarize_health,
    'cost': summarize_cost,
    'guardduty': summarize_guardduty,
    'cloudwatch': summarize_cloudwatch,
    'notifications': summarize_notifications,
    'backup': summarize_backup,
    'rds': summarize_rds,
}


def build_whatsapp_backup(date_str, all_results):
    completed_lines = []
    failed_lines = []
    expired_lines = []
    vault_gap_lines = []
    nobackup_lines = []

    # Friendly display names aligned with original backup script
    display_name_map = {
        "backup-hris": "Backup HRIS",
        "HRIS": "HRIS",
        "cis-erha": "CIS Erha",
        "connect-prod": "Connect Prod",
        "tgw": "TGW",
        "centralized-s3": "Centralized S3",
        "erha-buddy": "ERHA BUDDY",
        "public-web": "Public Web App",
        "iris-prod": "PROD -  IRIS PROD",
        "iris-dev": "DEV - IRIS DEV",
        "sfa": "SFA",
        "dermies-max": "Dermies Max",
        "fee-doctor": "Fee Doctor",
    }

    for profile, checks in all_results.items():
        res = checks.get('backup')
        if not res or res.get('status') == 'error':
            continue

        display = display_name_map.get(profile, profile)
        acct = get_account_id(profile)
        has_activity = (res.get('total_jobs', 0) > 0 or
                        any(v.get('recovery_points_24h', 0) > 0 for v in res.get('vaults', [])) or
                        res.get('rds_snapshots_24h', 0) > 0)

        if not has_activity:
            nobackup_lines.append(f"- {display} - {acct} (tidak ada backup pada periode)")
            continue

        missing_vaults = [v for v in res.get('vaults', []) if v.get('recovery_points_24h', 0) == 0 and not v.get('error')]
        if missing_vaults:
            vault_gap_lines.append(f"- {display} - {acct} vault gap: {len(missing_vaults)} vault tanpa RP 24h")

        issues = res.get('issues', [])
        failed = res.get('failed_jobs', 0)
        expired = res.get('expired_jobs', 0)

        if not issues:
            parts = []
            if res.get('total_jobs', 0) > 0:
                parts.append(f"AWS Backup: {res.get('completed_jobs',0)}/{res.get('total_jobs',0)}")
            if res.get('vaults'):
                total_rp_24h = sum(v.get('recovery_points_24h', 0) for v in res.get('vaults', []))
                parts.append(f"Vault: {total_rp_24h} RP 24h")
            if res.get('rds_snapshots_24h', 0) > 0:
                parts.append(f"RDS: {res.get('rds_snapshots_24h')} snapshots")
            activity = " | ".join(parts) if parts else "aktivitas 24h"
            completed_lines.append(f"- {display} - {acct} ({activity})")
        else:
            if failed:
                failed_lines.append(f"- {display} - {acct} => {failed} failed job(s)")
            if expired:
                expired_lines.append(f"- {display} - {acct} => {expired} expired job(s)")
            for i in issues:
                if "failed" in i or "expired" in i:
                    continue
                failed_lines.append(f"- {display} - {acct} => {i}")

    completed_block = "\r\n".join(completed_lines) if completed_lines else "- (tidak ada akun dengan status OK)"
    failed_block = "\r\n".join(failed_lines) if failed_lines else "- (tidak ada)"
    expired_block = "\r\n".join(expired_lines) if expired_lines else "- (tidak ada)"
    vault_gap_block = "\r\n".join(vault_gap_lines) if vault_gap_lines else "- (tidak ada)"
    nobackup_block = "\r\n".join(nobackup_lines) if nobackup_lines else "- (tidak ada)"

    return (
        "Selamat Pagi Team,\r\n"
        "Berikut report untuk AryaNoble Backup pada hari ini\r\n"
        f"{date_str}\r\n\r\n"
        "Completed:\r\n"
        f"{completed_block}\r\n\r\n"
        "Failed:\r\n"
        f"{failed_block}\r\n\r\n"
        "Expired:\r\n"
        f"{expired_block}\r\n\r\n"
        "Vault Gaps (tidak ada RP 24h):\r\n"
        f"{vault_gap_block}\r\n\r\n"
        "No Backups:\r\n"
        f"{nobackup_block}\r\n"
    ).strip()


def build_whatsapp_rds(all_results):
    now_jkt = datetime.now(timezone(timedelta(hours=7)))
    greeting = "Selamat Pagi" if 5 <= now_jkt.hour <= 17 else "Selamat Malam"
    date_str = now_jkt.strftime("%d-%m-%Y")

    messages = []
    for profile, checks in all_results.items():
        res = checks.get('rds')
        if not res or res.get('status') in ['skipped', 'error']:
            continue
        acct_id = res.get('account_id', get_account_id(profile))
        acct_name = res.get('account_name', profile)

        lines = [
            f"{greeting} Team,",
            f"Berikut Daily report untuk akun id {acct_name} ({acct_id}) pada {'Pagi' if 5 <= now_jkt.hour <= 17 else 'Malam'} ini",
            f"{date_str}",
            "",
            "Summary:",
        ]

        instances = res.get('instances', {})
        for role, data in instances.items():
            lines.append("")
            lines.append(f"{role.capitalize()}:")
            metrics = data.get('metrics', {})
            for m in ['ACUUtilization', 'CPUUtilization', 'FreeableMemory', 'DatabaseConnections']:
                info = metrics.get(m, {})
                msg = info.get('message', f"{m}: Data tidak tersedia")
                lines.append(f"* {msg}")

        messages.append("\n".join(lines))

    if not messages:
        return "Tidak ada data RDS untuk profil Aryanoble yang terkonfigurasi."

    sep = "\n" + ("-" * 70) + "\n\n"
    return sep.join(messages)


def generate_whatsapp_message(all_results):
    """Generate a WhatsApp-ready text focusing on Backup and RDS for Aryanoble."""
    now_jkt = datetime.now(timezone(timedelta(hours=7)))
    lines = [
        "Selamat Pagi Team,",
        f"Laporan daily Aryanoble {now_jkt:%d-%m-%Y}",
        "",
    ]

    # Backup section
    backup_lines = []
    for profile, checks in all_results.items():
        backup = checks.get('backup')
        if not backup:
            continue
        if backup.get('status') == 'error':
            backup_lines.append(f"- {profile}: ERROR {backup.get('error', '')}")
            continue
        if backup.get('issues'):
            issues = "; ".join(backup.get('issues', []))
            backup_lines.append(f"- {profile}: Attention ({issues})")
        else:
            backup_lines.append(f"- {profile}: OK (jobs {backup.get('total_jobs',0)} / failed {backup.get('failed_jobs',0)})")

    if backup_lines:
        lines.append("Backup:")
        lines.extend(backup_lines)
        lines.append("")

    # RDS section
    rds_lines = []
    for profile, checks in all_results.items():
        rds = checks.get('rds')
        if not rds or rds.get('status') == 'skipped':
            continue
        if rds.get('status') == 'error':
            rds_lines.append(f"- {profile}: ERROR {rds.get('error','')}")
            continue
        warn = 0
        for data in rds.get('instances', {}).values():
            for m in data.get('metrics', {}).values():
                if m.get('status') == 'warn':
                    warn += 1
        if warn:
            rds_lines.append(f"- {profile}: Attention ({warn} metric warning)")
        else:
            rds_lines.append(f"- {profile}: OK (RDS metrics normal)")

    if rds_lines:
        lines.append("RDS:")
        lines.extend(rds_lines)
        lines.append("")

    if not backup_lines and not rds_lines:
        lines.append("Tidak ada data Backup/RDS yang relevan untuk Aryanoble.")

    lines.append("Terima kasih.")
    return "\n".join(lines)


def run_all_checks(profiles, region, group_name=None):
    """Run all checks and generate combined summary"""
    console.print(Panel(
        f"[bold]{len(profiles)}[/bold] profil • Region: [green]{region}[/green] • Group: [cyan]{group_name or '-'}[/cyan]",
        title="All Checks",
        border_style="cyan",
        padding=(1, 2),
    ))
    
    all_results = {}
    total_anomalies = 0
    total_findings = 0
    total_alarms = 0
    total_new_notifications = 0
    check_errors = []  # list of (profile, check_name, error)
    clean_accounts = []
    guardduty_disabled = []
    whatsapp_ready = None
    errors_by_check = {name: [] for name in ALL_MODE_CHECKS.keys()}
    
    for profile in profiles:
        account_id = get_account_id(profile)
        print(f"  Checking {profile}...")
        
        profile_results = {}
        has_issue = False
        
        for check_name, checker_class in ALL_MODE_CHECKS.items():
            checker = checker_class(region=region)
            try:
                results = checker.check(profile, account_id)
            except (BotoCoreError, ClientError) as exc:
                results = {'status': 'error', 'error': str(exc)}
            except Exception as exc:
                results = {'status': 'error', 'error': str(exc)}
            profile_results[check_name] = results
            
            # Track issues
            if results.get('status') == 'error':
                check_errors.append((profile, check_name, results.get('error', 'Unknown error')))
                errors_by_check[check_name].append((profile, results.get('error', 'Unknown error')))
                has_issue = True
            if check_name == 'cost' and results.get('total_anomalies', 0) > 0:
                total_anomalies += results.get('total_anomalies', 0)
                has_issue = True
            elif check_name == 'guardduty':
                if results.get('status') == 'disabled':
                    guardduty_disabled.append(profile)
                elif results.get('findings', 0) > 0:
                    total_findings += results.get('findings', 0)
                    has_issue = True
            elif check_name == 'cloudwatch' and results.get('count', 0) > 0:
                total_alarms += results.get('count', 0)
                has_issue = True
            elif check_name == 'notifications' and results.get('today_count', 0) > 0:
                total_new_notifications += results.get('today_count', 0)
                has_issue = True
        
        all_results[profile] = profile_results
        if not has_issue:
            clean_accounts.append(profile)

    # If the group is Aryanoble, prepare WhatsApp-ready messages for backup & rds
    if group_name == 'aryanoble':
        date_str = datetime.now(timezone(timedelta(hours=7))).strftime("%d-%m-%Y")
        whatsapp_ready = {
            'backup': build_whatsapp_backup(date_str, all_results),
            'rds': build_whatsapp_rds(all_results)
        }
    
    # Generate report
    now = datetime.now()
    date_str = now.strftime('%B %d, %Y')
    time_str = now.strftime('%H:%M WIB')
    
    lines = []
    if group_name:
        lines.append(f"DAILY MONITORING REPORT - {group_name.upper()} GROUP")
    else:
        lines.append("DAILY MONITORING REPORT")
    lines.append(f"Date: {date_str}")
    lines.append(f"Scope: {len(profiles)} AWS Accounts | Region: {region}")
    lines.append("")
    lines.append("EXECUTIVE SUMMARY")
    
    summary_text = f"Security assessment completed across {len(profiles)} AWS accounts."
    if check_errors:
        summary_text += f" {len(check_errors)} check error(s) encountered; see CHECK ERRORS section."
    if total_anomalies == 0 and total_findings == 0 and total_alarms == 0 and not check_errors:
        summary_text += " No new security incidents detected. All systems operating normally."
    else:
        issues = []
        if check_errors:
            issues.append(f"{len(check_errors)} check errors")
        if total_anomalies > 0:
            issues.append(f"{total_anomalies} cost anomalies")
        if total_findings > 0:
            issues.append(f"{total_findings} new security findings")
        if total_alarms > 0:
            issues.append(f"{total_alarms} infrastructure alerts")
        summary_text += f" {' and '.join(issues)} detected requiring attention."
    lines.append(summary_text)
    
    lines.append("")
    lines.append("ASSESSMENT RESULTS")
    
    # Cost Anomalies Section
    lines.append("")
    lines.append("COST ANOMALIES")
    if errors_by_check.get('cost'):
        lines.append("Status: ERROR - Cost Anomaly check failed")
        lines.append("Errors:")
        for prof, err in errors_by_check['cost'][:5]:
            lines.append(f"• {prof}: {err}")
        if len(errors_by_check['cost']) > 5:
            lines.append(f"... and {len(errors_by_check['cost'])-5} more")
    elif total_anomalies == 0:
        lines.append("Status: CLEAR - No cost anomalies detected")
    else:
        lines.append(f"Status: ATTENTION REQUIRED - {total_anomalies} anomalies detected")
        lines.append("")
        lines.append("Detected Anomalies:")
        for profile, results in all_results.items():
            cost_data = results.get('cost', {})
            if cost_data.get('total_anomalies', 0) > 0:
                account_id = get_account_id(profile)
                lines.append(f"• {profile} ({account_id}): {cost_data['total_anomalies']} anomalies")
                for anomaly in cost_data.get('anomalies', [])[:3]:
                    impact = anomaly.get('Impact', {}).get('TotalImpact', '0')
                    anomaly_start = anomaly.get('AnomalyStartDate', 'N/A')
                    anomaly_end = anomaly.get('AnomalyEndDate', 'N/A')
                    lines.append(f"  - Monitor: {anomaly.get('MonitorName', 'N/A')}")
                    lines.append(f"  - Impact: ${impact}")
                    lines.append(f"  - Date: {anomaly_start} to {anomaly_end}")
                    
                    # Show affected services
                    root_causes = anomaly.get('RootCauses', [])
                    if root_causes:
                        services = list(set([rc.get('Service', 'N/A') for rc in root_causes]))
                        lines.append(f"  - Affected Services: {', '.join(services[:3])}")
                        if len(services) > 3:
                            lines.append(f"    ... and {len(services) - 3} more services")
                        
                        # Show top root cause
                        top_cause = root_causes[0]
                        lines.append(f"  - Top Root Cause: {top_cause.get('Service', 'N/A')} - {top_cause.get('UsageType', 'N/A')}")
                        if top_cause.get('Region') and top_cause.get('Region') != 'N/A':
                            lines.append(f"    Region: {top_cause.get('Region')}")
    
    # GuardDuty Section
    lines.append("")
    lines.append("GUARDDUTY FINDINGS")
    if errors_by_check.get('guardduty'):
        lines.append("Status: ERROR - GuardDuty check failed")
        lines.append("Errors:")
        for prof, err in errors_by_check['guardduty'][:5]:
            lines.append(f"• {prof}: {err}")
        if len(errors_by_check['guardduty']) > 5:
            lines.append(f"... and {len(errors_by_check['guardduty'])-5} more")
    elif total_findings > 0 or guardduty_disabled:
        if total_findings > 0:
            lines.append(f"Status: ATTENTION REQUIRED - {total_findings} new findings detected")
            lines.append("")
            lines.append("Current Findings:")
            for profile, results in all_results.items():
                gd_data = results.get('guardduty', {})
                if gd_data.get('findings', 0) > 0:
                    account_id = get_account_id(profile)
                    lines.append(f"• {profile} ({account_id}): {gd_data['findings']} findings")
                    for detail in gd_data.get('details', [])[:3]:
                        lines.append(f"  - Type: {detail.get('type', 'N/A')}")
                        lines.append(f"  - Severity: {detail.get('severity', 'N/A')}")
                        lines.append(f"  - Date: {detail.get('updated', 'N/A')}")
        
        if guardduty_disabled:
            if total_findings > 0:
                lines.append("")
            lines.append("GuardDuty NOT ENABLED:")
            for profile in guardduty_disabled:
                account_id = get_account_id(profile)
                lines.append(f"• {profile} ({account_id})")
    else:
        lines.append("Status: CLEAR - No new security findings detected")
    
    # CloudWatch Section
    lines.append("")
    lines.append("CLOUDWATCH ALARMS")
    if errors_by_check.get('cloudwatch'):
        lines.append("Status: ERROR - CloudWatch check failed")
        lines.append("Errors:")
        for prof, err in errors_by_check['cloudwatch'][:5]:
            lines.append(f"• {prof}: {err}")
        if len(errors_by_check['cloudwatch']) > 5:
            lines.append(f"... and {len(errors_by_check['cloudwatch'])-5} more")
    elif total_alarms == 0:
        lines.append("Status: All monitoring systems normal")
    else:
        lines.append(f"Status: {total_alarms} alarms in ALARM state")
        lines.append("")
        lines.append("Active Alarms:")
        for profile, results in all_results.items():
            cw_data = results.get('cloudwatch', {})
            if cw_data.get('count', 0) > 0:
                account_id = get_account_id(profile)
                lines.append(f"• {profile} ({account_id}): {cw_data['count']} active alarms")
                for detail in cw_data.get('details', [])[:3]:
                    lines.append(f"  - Alarm: {detail.get('name', 'N/A')}")
                    lines.append(f"  - Reason: {detail.get('reason', 'N/A')}")
                    lines.append(f"  - Date: {detail.get('updated', 'N/A')}")
    
    # Notification Center Section
    notif_data = None
    for profile, results in all_results.items():
        if 'notifications' in results:
            notif_data = results['notifications']
            break
    
    lines.append("")
    lines.append("NOTIFICATION CENTER")
    if errors_by_check.get('notifications'):
        lines.append("Status: ERROR - Notification Center check failed")
        lines.append("Errors:")
        for prof, err in errors_by_check['notifications'][:5]:
            lines.append(f"• {prof}: {err}")
        if len(errors_by_check['notifications']) > 5:
            lines.append(f"... and {len(errors_by_check['notifications'])-5} more")
    elif notif_data:
        today_count = notif_data.get('today_count', 0)
        total_managed = notif_data.get('total_managed', 0)
        
        if today_count == 0:
            lines.append(f"Status: No new notifications today ({total_managed} existing available)")
        else:
            lines.append(f"Status: {today_count} new notifications detected today")
            lines.append("")
            lines.append("Today's Notifications:")
            for event in notif_data.get('today_events', [])[:3]:
                notif_event = event.get('notificationEvent', {})
                event_type = notif_event.get('sourceEventMetadata', {}).get('eventType', 'N/A')
                headline = notif_event.get('messageComponents', {}).get('headline', 'N/A')
                
                lines.append(f"• Event Type: {event_type}")
                lines.append(f"  Description: {headline}")
    else:
        lines.append("Status: No data")
    
    # Account Coverage
    lines.append("")
    lines.append("ACCOUNT COVERAGE")
    lines.append(f"Total Assessed: {len(profiles)} accounts")
    lines.append(f"Clean Accounts: {len(clean_accounts)}")
    lines.append(f"Accounts with Issues: {len(profiles) - len(clean_accounts)}")
    if check_errors:
        lines.append(f"Check Errors: {len(check_errors)} (see below)")
    
    if check_errors:
        lines.append("")
        lines.append("CHECK ERRORS")
        for profile, chk, err in check_errors:
            lines.append(f"- {profile} | {chk}: {err}")

    # Recommendations
    lines.append("")
    lines.append("RECOMMENDATIONS")
    rec_count = 1
    
    if check_errors:
        lines.append(f"{rec_count}. INVESTIGATE CHECK ERRORS: Resolve authentication/permission/session issues")
        lines.append("   Affected:")
        for profile, chk, err in check_errors[:5]:
            lines.append(f"   - {profile} ({chk}): {err}")
        if len(check_errors) > 5:
            lines.append(f"   ... and {len(check_errors)-5} more")
        rec_count += 1
    
    if total_anomalies > 0:
        lines.append(f"{rec_count}. COST REVIEW: Investigate cost anomalies")
        affected = [p for p, r in all_results.items() if r.get('cost', {}).get('total_anomalies', 0) > 0]
        lines.append(f"   Affected accounts: {', '.join(affected)}")
        rec_count += 1
    
    if total_findings > 0:
        lines.append(f"{rec_count}. IMMEDIATE ACTION REQUIRED: Investigate GuardDuty findings")
        affected = [p for p, r in all_results.items() if r.get('guardduty', {}).get('findings', 0) > 0]
        lines.append(f"   Affected accounts: {', '.join(affected)}")
        rec_count += 1
    
    if total_alarms > 0:
        lines.append(f"{rec_count}. INFRASTRUCTURE REVIEW: Address CloudWatch alarms")
        affected = [p for p, r in all_results.items() if r.get('cloudwatch', {}).get('count', 0) > 0]
        lines.append(f"   Affected accounts: {', '.join(affected)}")
        rec_count += 1

    # Append WhatsApp-ready section if available
    if whatsapp_ready:
        lines.append("")
        lines.append("WHATSAPP MESSAGE (READY TO SEND)")
        lines.append("--backup")
        lines.append(whatsapp_ready.get('backup', ''))
        lines.append("")
        lines.append("--rds")
        lines.append(whatsapp_ready.get('rds', ''))
    
    if rec_count == 1:
        lines.append("1. ROUTINE MONITORING: Continue assessment schedule")
    
    print("\n" + "\n".join(lines))


# ---------------------- Interactive helpers ---------------------- #

def list_local_profiles():
    """Return list of AWS CLI profiles available locally."""
    try:
        return boto3.Session().available_profiles
    except Exception:
        return []


# Custom style for cooler prompts
CUSTOM_STYLE = Style([
    ("qmark", "fg:#00b894 bold"),
    ("question", "bold"),
    ("answer", "fg:#00cec9 bold"),
    ("pointer", "fg:#00e0a3 bold"),
    ("highlighted", "fg:#00e0a3 bold"),
    ("selected", "fg:#0a0a0a bg:#00e0a3"),
    ("separator", "fg:#636e72"),
    ("instruction", "fg:#b2bec3"),
])

TIPS = [
    "Esc/Ctrl+C selalu membawa Anda ke menu utama.",
    "Gunakan Group (SSO) agar daftar akun otomatis terisi.",
    "Backup dan RDS mendukung multi akun untuk laporan WhatsApp.",
    "Single check cocok untuk verifikasi cepat per profil.",
    "Pilih region sesuai default profil untuk menghindari error.",
]


def _tip_of_the_day():
    if not TIPS:
        return ""
    idx = datetime.now().minute % len(TIPS)
    return TIPS[idx]


def _fmt(title, text):
    return f"{BOLD}{title}{RESET} {text}"


def _section(title, subtitle=None, tip=None):
    """Render a compact section header using rich."""
    header = Text(title, style="bold cyan")
    if subtitle:
        header.append(f" · {subtitle}", style="dim")
    console.print(Rule())
    console.print(header)
    if tip:
        console.print(Text(tip, style="italic magenta"))
    console.print(Rule())


def _handle_interrupt(context="Kembali ke menu utama", exit_direct=False):
    """Handle Ctrl+C/Esc; in menus we exit immediately for convenience."""
    global _last_interrupt_ts
    now = monotonic()
    if exit_direct:
        console.print(f"\n[bold green]Keluar dari AWS Monitoring Hub. Sampai jumpa![/bold green]\n")
        sys.exit(0)
    if now - _last_interrupt_ts <= INTERRUPT_EXIT_WINDOW:
        console.print(f"\n[bold green]Keluar dari AWS Monitoring Hub. Sampai jumpa![/bold green]\n")
        sys.exit(0)
    _last_interrupt_ts = now
    console.print(f"\n[bold yellow]{context}[/bold yellow]. Tekan Ctrl+C lagi dalam {INTERRUPT_EXIT_WINDOW:.1f}s untuk keluar.\n")


def _banner():
    tip = _tip_of_the_day()
    lines = [
        "[bold]AWS Monitoring Hub[/bold]",
        "[dim]Monitoring ringkas untuk keamanan & operasi AWS[/dim]",
        "",
        "[cyan]⌨︎[/cyan] Esc/Ctrl+C: kembali   •   Ctrl+C dua kali: keluar",
        "[cyan]✓[/cyan] Spasi: centang pilihan   •   Enter: konfirmasi",
        "[cyan]🌏[/cyan] Gunakan region sesuai default profil jika ragu",
    ]
    if tip:
        lines.append("")
        lines.append(f"[magenta]💡 Tip:[/magenta] {tip}")
    console.print(Panel("\n".join(lines), border_style="cyan", padding=(1, 2)))


def _select_prompt(prompt, choices, default=None):
    opts = choices
    try:
        ans = questionary.select(
            prompt + " (Esc untuk kembali)",
            choices=opts,
            default=default if default in opts else None,
            style=CUSTOM_STYLE,
        ).ask()
    except KeyboardInterrupt:
        _handle_interrupt(exit_direct=True)
        return None
    return ans or None


def _checkbox_prompt(prompt, choices):
    opts = choices
    try:
        ans = questionary.checkbox(
            prompt + " (Spasi pilih, Enter konfirm, Esc untuk kembali)",
            choices=opts,
            style=CUSTOM_STYLE,
        ).ask()
    except KeyboardInterrupt:
        _handle_interrupt(exit_direct=True)
        return None
    return ans or None


def _choose_region(selected_profiles):
    default_region = resolve_region(selected_profiles, None)
    region_choices = ["ap-southeast-3", "ap-southeast-1", "us-east-1", "us-west-2", "Other"]
    region = _select_prompt(
        "Pilih region",
        region_choices,
        default=default_region if default_region in region_choices else "ap-southeast-3",
    )
    if region is None:
        return None
    if region == "Other":
        try:
            region = questionary.text("Masukkan region (contoh ap-southeast-3) [Esc untuk kembali]:", style=CUSTOM_STYLE).ask()
        except KeyboardInterrupt:
            _handle_interrupt(exit_direct=True)
            return None
    return region


def _pick_profiles(allow_multiple=True):
    source = _select_prompt("Pilih sumber profil", ["Group (SSO)", "All Account"])
    if not source:
        return [], None, True

    profiles = []
    group_choice = None

    if source == "Group (SSO)":
        group_choice = _select_prompt("Pilih group", list(PROFILE_GROUPS.keys()))
        if not group_choice:
            return [], None, True
        choices = list(PROFILE_GROUPS[group_choice].keys())
        if allow_multiple:
            profiles = _checkbox_prompt("Pilih akun (bisa lebih dari satu)", choices)
        else:
            selected = _select_prompt("Pilih akun", choices)
            profiles = [selected] if selected else []
    else:
        local_profiles = list_local_profiles()
        if not local_profiles:
            console.print("[bold red]ERROR[/bold red]: Tidak menemukan profil AWS lokal. Silakan login/configure AWS CLI terlebih dulu.")
            return [], None, False
        if allow_multiple:
            profiles = _checkbox_prompt("Pilih profil (bisa lebih dari satu)", local_profiles)
        else:
            selected = _select_prompt("Pilih profil", local_profiles)
            profiles = [selected] if selected else []

    return profiles or [], group_choice, False


def _pause():
    try:
        questionary.text("Tekan Enter untuk kembali ke menu utama (Esc/Ctrl+C untuk kembali):", style=CUSTOM_STYLE, default="").ask()
    except KeyboardInterrupt:
        _handle_interrupt(exit_direct=True)
        return


def run_interactive():
    """Interactive menu loop; returns to main menu after each action."""
    quick_actions = [
        questionary.Choice(title="Single check · cek satu profil", value="single"),
        questionary.Choice(title="All checks · ringkas banyak profil", value="all"),
        questionary.Choice(title="Backup report · WhatsApp", value="backup"),
        questionary.Choice(title="RDS report · WhatsApp", value="rds"),
    ]

    while True:
        _banner()
        try:
            main_choice = _select_prompt("Pilih aksi", quick_actions)
        except KeyboardInterrupt:
            _handle_interrupt(exit_direct=True)
            break
        if not main_choice:
            break

        if main_choice == "single":
            try:
                check = questionary.select(
                    "Pilih check (Esc untuk kembali):",
                    choices=list(AVAILABLE_CHECKS.keys()),
                    style=CUSTOM_STYLE,
                ).ask()
            except KeyboardInterrupt:
                _handle_interrupt(exit_direct=True)
                continue
            if not check:
                continue
            allow_multi = check in ['backup', 'rds']
            profiles, group_choice, back = _pick_profiles(allow_multiple=allow_multi)
            if back:
                continue
            if not profiles:
                console.print("[bold red]ERROR[/bold red]: Tidak ada profil dipilih.")
                _pause()
                continue
            region = _choose_region(profiles)
            if region is None:
                continue
            if check in ['backup', 'rds'] and len(profiles) > 1:
                run_group_specific(check, profiles, region, group_name=group_choice)
            else:
                run_individual_check(check, profiles[0], region)
            _pause()
            continue

        if main_choice == "all":
            profiles, group_choice, back = _pick_profiles(allow_multiple=True)
            if back:
                continue
            if not profiles:
                console.print("[bold red]ERROR[/bold red]: Tidak ada profil dipilih.")
                _pause()
                continue
            region = _choose_region(profiles)
            if region is None:
                continue
            run_all_checks(profiles, region, group_name=group_choice)
            _pause()
            continue

        if main_choice == "backup":
            profiles, group_choice, back = _pick_profiles(allow_multiple=True)
            if back:
                continue
            if not profiles:
                console.print("[bold red]ERROR[/bold red]: Tidak ada profil dipilih.")
                _pause()
                continue
            region = _choose_region(profiles)
            if region is None:
                continue
            run_group_specific('backup', profiles, region, group_name=group_choice)
            _pause()
            continue

        if main_choice == "rds":
            profiles, group_choice, back = _pick_profiles(allow_multiple=True)
            if back:
                continue
            if not profiles:
                console.print("[bold red]ERROR[/bold red]: Tidak ada profil dipilih.")
                _pause()
                continue
            region = _choose_region(profiles)
            if region is None:
                continue
            run_group_specific('rds', profiles, region, group_name=group_choice)
            _pause()
            continue


def main():
    parser = argparse.ArgumentParser(
        description='AWS Monitoring Hub - Centralized AWS monitoring',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run individual check with details
  python monitoring_hub.py --check health --profile ksni-master
  python monitoring_hub.py --check cost --profile ksni-master
  python monitoring_hub.py --check backup --profile ksni-master
  python monitoring_hub.py --check rds --profile ksni-master
  
  # Run individual check with SSO profile
  python monitoring_hub.py --check guardduty --sso-profile ksni-master
  
  # Run all checks for single profile (summary)
  python monitoring_hub.py --all --profile ksni-master
  
  # Run all checks for SSO profile (summary)
  python monitoring_hub.py --all --sso-profile ksni-master
  
  # Run all checks for multiple profiles (summary)
  python monitoring_hub.py --all --profile ksni-master,data-ksni
  
  # Run all checks for entire group (summary)
  python monitoring_hub.py --all --sso nabati

Available checks: health, cost, guardduty, cloudwatch, notifications, backup, rds, ec2list
        """
    )
    
    parser.add_argument('--check', 
                       help='Run specific check (health, cost, guardduty, cloudwatch, notifications, backup, rds, ec2list)')
    parser.add_argument('--all', 
                       action='store_true',
                       help='Run all checks (summary mode)')
    parser.add_argument('--interactive',
                       action='store_true',
                       help='Jalankan mode menu interaktif (menu dropdown untuk profil/check)')
    parser.add_argument('--profile', 
                       help='AWS profile name(s) using regular aws login/credentials (comma-separated)')
    parser.add_argument('--aws-profile',
                       help='Alias for --profile (regular aws login/credentials)')
    parser.add_argument('--group',
                       choices=PROFILE_GROUPS.keys(),
                       help='Profile group via SSO (nabati, sadewa, aryanoble, hungryhub, ics)')
    parser.add_argument('--sso',
                       choices=PROFILE_GROUPS.keys(),
                       help='Alias for --group (SSO groups)')
    parser.add_argument('--sso-profile',
                       help='Specific SSO profile name(s), comma-separated')
    parser.add_argument('--region',
                       default=None,
                       help='AWS region override (defaults to profile config)')
    
    args = parser.parse_args()

    # Default ke mode interaktif jika tidak ada argumen --check/--all
    if args.interactive or (not args.check and not args.all):
        run_interactive()
        sys.exit(0)

    # Validate arguments
    if args.group and args.sso:
        print("ERROR: Use only one of --group or --sso")
        sys.exit(1)
    
    aws_profiles_raw = args.profile or args.aws_profile
    sso_profiles_raw = args.sso_profile

    if not any([aws_profiles_raw, sso_profiles_raw, args.group, args.sso]):
        print("ERROR: Must specify AWS login profiles (--profile/--aws-profile) or SSO (--group/--sso/--sso-profile)")
        sys.exit(1)
    
    # Get profiles to check
    profiles = []

    if aws_profiles_raw:
        profiles.extend([p.strip() for p in aws_profiles_raw.split(',') if p.strip()])

    if sso_profiles_raw:
        profiles.extend([p.strip() for p in sso_profiles_raw.split(',') if p.strip()])

    group_choice = args.group or args.sso
    if group_choice:
        profiles.extend(list(PROFILE_GROUPS[group_choice].keys()))

    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for p in profiles:
        if p not in seen:
            deduped.append(p)
            seen.add(p)
    profiles = deduped

    if not profiles:
        print("ERROR: No profiles resolved from provided arguments")
        sys.exit(1)

    resolved_region = resolve_region(profiles, args.region)

    # Run checks
    if args.check:
        # Special handling: allow backup/rds across group for WhatsApp-ready output
        if args.check in ['backup', 'rds'] and len(profiles) > 1:
            group_choice = args.group or args.sso
            run_group_specific(args.check, profiles, resolved_region, group_name=group_choice)
        else:
            if len(profiles) > 1:
                print("ERROR: Individual check mode only supports single profile")
                print("Use --all for multiple profiles or use backup/rds with --group")
                sys.exit(1)
            run_individual_check(args.check, profiles[0], resolved_region)
    else:
        # All checks mode - summary output
        group_choice = args.group or args.sso
        run_all_checks(profiles, resolved_region, group_name=group_choice)

if __name__ == '__main__':
    main()
