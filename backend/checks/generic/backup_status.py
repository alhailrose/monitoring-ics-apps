"""AWS Backup status checker (jobs + vault activity + optional RDS snapshots)."""

import logging
import boto3
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from backend.checks.common.base import BaseChecker
from backend.checks.common.aws_errors import is_credential_error

logger = logging.getLogger(__name__)


# Jakarta timezone for display
JAKARTA_TZ = timezone(timedelta(hours=7))


# Profiles that still rely on native RDS snapshots (outside AWS Backup)
RDS_ACCOUNTS: List[str] = ["iris-prod"]

# Vaults to monitor per profile (subset from standalone script)
VAULT_CONFIGS: List[Dict[str, str]] = [
    {"profile": "centralized-s3", "vault_name": "central-vault"},
    {
        "profile": "backup-hris",
        "vault_name": "central-aws-backup-restricted-account-Feedoctor",
    },
    {
        "profile": "backup-hris",
        "vault_name": "central-aws-backup-restricted-account-IRIS",
    },
    {
        "profile": "backup-hris",
        "vault_name": "central-aws-backup-restricted-account-SFA",
    },
]


class BackupStatusChecker(BaseChecker):
    """Summarize AWS Backup health for a profile within the last 24h."""

    report_section_title = "BACKUP STATUS"
    issue_label = "backup issues"
    recommendation_text = "BACKUP REVIEW: Investigate failed backup jobs"

    def __init__(
        self,
        region: str = "ap-southeast-3",
        vault_names=None,
        monitor_rds_snapshots: bool | None = None,
        max_job_details: int = 50,
        **kwargs,
    ):
        super().__init__(region=region, **kwargs)
        if isinstance(vault_names, str):
            parsed = [x.strip() for x in vault_names.split(",")]
            self.vault_names = [x for x in parsed if x]
        elif isinstance(vault_names, list):
            self.vault_names = [str(x).strip() for x in vault_names if str(x).strip()]
        else:
            self.vault_names = []
        self.monitor_rds_snapshots = monitor_rds_snapshots
        self.max_job_details = max(1, int(max_job_details))

    def _list_backup_jobs(self, session, since_utc: datetime) -> List[dict]:
        client = session.client("backup", region_name=self.region)
        jobs: List[dict] = []
        token: Optional[str] = None
        while True:
            resp = (
                client.list_backup_jobs(ByCreatedAfter=since_utc, NextToken=token)
                if token
                else client.list_backup_jobs(ByCreatedAfter=since_utc)
            )
            jobs.extend(resp.get("BackupJobs", []))
            token = resp.get("NextToken")
            if not token:
                break
        return jobs

    def _list_backup_plans(self, session) -> List[str]:
        client = session.client("backup", region_name=self.region)
        names: List[str] = []
        try:
            paginator = client.get_paginator("list_backup_plans")
            for page in paginator.paginate():
                for item in page.get("BackupPlansList", []):
                    if item.get("BackupPlanName"):
                        names.append(item["BackupPlanName"])
        except Exception as e:
            logger.warning("Failed to list backup plans: %s", e)
        return names

    def _resource_label(self, arn: str) -> str:
        if not arn:
            return "N/A"
        if "/" in arn:
            return arn.split("/")[-1]
        if ":" in arn:
            return arn.split(":")[-1]
        return arn

    def _resolve_resource_name(self, session, arn: str, resource_type: str) -> str:
        """Resolve a friendly name from an ARN. Falls back to the ARN label."""
        label = self._resource_label(arn)
        try:
            if resource_type == "EC2":
                ec2 = session.client("ec2", region_name=self.region)
                resp = ec2.describe_instances(InstanceIds=[label])
                reservations = resp.get("Reservations", [])
                if reservations:
                    instance = reservations[0].get("Instances", [{}])[0]
                    for tag in instance.get("Tags", []):
                        if tag.get("Key") == "Name" and tag.get("Value"):
                            return tag["Value"]
            elif resource_type == "EFS":
                efs = session.client("efs", region_name=self.region)
                # ARN: arn:aws:elasticfilesystem:region:account:file-system/fs-xxxx
                fs_id = label
                resp = efs.describe_file_systems(FileSystemId=fs_id)
                fss = resp.get("FileSystems", [])
                if fss:
                    for tag in fss[0].get("Tags", []):
                        if tag.get("Key") == "Name" and tag.get("Value"):
                            return tag["Value"]
        except Exception:
            pass
        # For RDS the ARN label already IS the db identifier (human-readable name)
        return label

    def _vault_activity(self, session, profile: str, since_utc: datetime) -> List[dict]:
        """Check configured vaults for recovery point activity since since_utc."""
        if self.vault_names:
            vaults = [
                {"profile": profile, "vault_name": name} for name in self.vault_names
            ]
        else:
            vaults = [v for v in VAULT_CONFIGS if v["profile"] == profile]
        results: List[dict] = []
        if not vaults:
            return results

        client = session.client("backup", region_name=self.region)

        for v in vaults:
            name = v["vault_name"]
            try:
                meta = client.describe_backup_vault(BackupVaultName=name)
                total_points = meta.get("NumberOfRecoveryPoints", 0)
            except Exception as e:  # pragma: no cover - API failure path
                results.append({"vault_name": name, "error": str(e)})
                continue

            rp_24h = 0
            resources_24h: List[dict] = []
            token: Optional[str] = None
            try:
                while True:
                    kwargs = {
                        "BackupVaultName": name,
                        "ByCreatedAfter": since_utc,
                    }
                    if token:
                        kwargs["NextToken"] = token
                    resp = client.list_recovery_points_by_backup_vault(**kwargs)
                    rps = resp.get("RecoveryPoints", [])
                    rp_24h += len(rps)
                    for r in rps:
                        arn = r.get("ResourceArn", "")
                        if not arn:
                            continue
                        res_type = r.get("ResourceType", "")
                        friendly_name = self._resolve_resource_name(session, arn, res_type)
                        resources_24h.append({
                            "arn": arn,
                            "name": friendly_name,
                            "type": res_type,
                        })
                    token = resp.get("NextToken")
                    if not token:
                        break
            except Exception as e:  # pragma: no cover
                results.append(
                    {
                        "vault_name": name,
                        "error": str(e),
                        "total_recovery_points": total_points,
                    }
                )
                continue

            results.append(
                {
                    "vault_name": name,
                    "total_recovery_points": total_points,
                    "recovery_points_24h": rp_24h,
                    "resources_24h": resources_24h,
                }
            )

        return results

    def _rds_snapshots_24h(self, session) -> int:
        """Count RDS snapshots created in last 24h (automated + manual)."""
        client = session.client("rds", region_name=self.region)
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        count = 0
        token: Optional[str] = None
        while True:
            resp = (
                client.describe_db_snapshots(Marker=token)
                if token
                else client.describe_db_snapshots()
            )
            snaps = resp.get("DBSnapshots", [])
            for s in snaps:
                ts = s.get("SnapshotCreateTime")
                if ts and ts >= since:
                    count += 1
            token = resp.get("Marker")
            if not token:
                break
        return count

    def check(self, profile, account_id):
        try:
            session = self._get_session(profile)
            # Use full previous day window in WIB (00:00–23:59 yesterday) for daily run
            now_jkt = datetime.now(JAKARTA_TZ)
            start_jkt = (now_jkt - timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            since_utc = start_jkt.astimezone(timezone.utc)
            now_utc = now_jkt.astimezone(timezone.utc)

            jobs = self._list_backup_jobs(session, since_utc)
            plans = self._list_backup_plans(session)
            failed = [j for j in jobs if j.get("State") == "FAILED"]
            expired = [j for j in jobs if j.get("State") == "EXPIRED"]
            completed = [j for j in jobs if j.get("State") == "COMPLETED"]

            vaults = self._vault_activity(session, profile, since_utc)

            rds_24h = 0
            should_monitor_rds = (
                self.monitor_rds_snapshots
                if self.monitor_rds_snapshots is not None
                else profile in RDS_ACCOUNTS
            )
            if should_monitor_rds:
                rds_24h = self._rds_snapshots_24h(session)

            issues = []
            if failed:
                issues.append(f"{len(failed)} failed job(s)")
            if expired:
                issues.append(f"{len(expired)} expired job(s)")
            if vaults:
                no_activity = [
                    v
                    for v in vaults
                    if v.get("recovery_points_24h", 0) == 0 and not v.get("error")
                ]
                if no_activity:
                    issues.append(
                        f"{len(no_activity)} vault(s) no recovery points in 24h"
                    )
                vault_errors = [v for v in vaults if v.get("error")]
                if vault_errors:
                    issues.append(f"{len(vault_errors)} vault error(s)")
            if should_monitor_rds and rds_24h == 0:
                issues.append("No RDS snapshots in 24h")

            status = "ATTENTION REQUIRED" if issues else "OK"

            job_details = []
            for j in jobs[: self.max_job_details]:
                created = j.get("CreationDate")
                created_wib = created
                if isinstance(created, datetime):
                    created_wib = created.astimezone(JAKARTA_TZ)
                job_details.append(
                    {
                        "job_id": j.get("BackupJobId", ""),
                        "state": j.get("State", ""),
                        "resource": j.get("ResourceArn", ""),
                        "resource_label": self._resource_label(
                            j.get("ResourceArn", "")
                        ),
                        "type": j.get("ResourceType", ""),
                        "reason": j.get("StatusMessage")
                        or j.get("FailureMessage")
                        or "",
                        "created": created,
                        "created_wib": created_wib,
                    }
                )

            return {
                "status": status,
                "profile": profile,
                "account_id": account_id,
                "region": self.region,
                "checked_at_utc": now_utc,
                "window_start_utc": since_utc,
                "total_jobs": len(jobs),
                "completed_jobs": len(completed),
                "failed_jobs": len(failed),
                "expired_jobs": len(expired),
                "vaults": vaults,
                "rds_snapshots_24h": rds_24h,
                "monitor_rds_snapshots": should_monitor_rds,
                "issues": issues,
                "job_details": job_details,
                "backup_plans": plans,
            }

        except Exception as e:  # pragma: no cover
            if is_credential_error(e):
                return self._error_result(e, profile, account_id)
            return {
                "status": "error",
                "profile": profile,
                "account_id": account_id,
                "region": self.region,
                "error": str(e),
            }

    def format_report(self, results):
        """Format backup status — full detail for specific/single check mode."""
        if results.get("status") == "error":
            return f"ERROR: {results.get('error')}"

        profile = results.get("profile", "")
        account_id = results.get("account_id", "Unknown")
        now_wib_str = datetime.now(JAKARTA_TZ).strftime("%d %b %Y %H:%M WIB")
        total = results.get("total_jobs", 0)
        completed = results.get("completed_jobs", 0)
        failed = results.get("failed_jobs", 0)
        expired = results.get("expired_jobs", 0)
        issues = results.get("issues", [])

        lines = []
        lines.append("┌─ BACKUP STATUS CHECK")
        lines.append(f"│  Profil     : {profile} ({account_id})")
        lines.append(f"│  Region     : {results.get('region', '-')}")
        lines.append(f"│  Diperiksa  : {now_wib_str}")
        lines.append(
            f"│  Total Jobs : {total} "
            f"(selesai: {completed}, gagal: {failed}, expired: {expired})"
        )

        if not issues:
            lines.append("└─ Status: ✓ Semua backup jobs berhasil")
        else:
            lines.append(f"└─ Status: ⚠ {len(issues)} masalah ditemukan")

        # Backup plans
        plans = results.get("backup_plans", [])
        if plans:
            lines.append("")
            lines.append(f"  Backup Plans ({len(plans)}):")
            for p in plans:
                lines.append(f"    • {p}")

        # Failed/expired job details
        details = results.get("job_details", [])
        failed_jobs = [j for j in details if j.get("state") in ["FAILED", "EXPIRED"]]
        if failed_jobs:
            lines.append("")
            lines.append(f"  Job Bermasalah ({len(failed_jobs)}):")
            for j in failed_jobs:
                ts_wib = j.get("created_wib")
                ts_str = (
                    ts_wib.strftime("%d %b %Y %H:%M WIB")
                    if hasattr(ts_wib, "strftime")
                    else str(ts_wib)
                )
                reason = j.get("reason") or "-"
                lines.append(
                    f"    [{j.get('state')}] {j.get('resource_label', 'N/A')} ({j.get('type', '-')})"
                )
                lines.append(f"      Waktu  : {ts_str}")
                if reason and reason != "-":
                    lines.append(f"      Alasan : {reason}")
                lines.append("")

        # Vault activity
        vaults = results.get("vaults", [])
        if vaults:
            lines.append("  Vault Activity (24 jam):")
            for v in vaults:
                if v.get("error"):
                    lines.append(f"    ⚠ {v['vault_name']}: ERROR — {v['error']}")
                else:
                    rp_24h = v.get("recovery_points_24h", 0)
                    total_rp = v.get("total_recovery_points", 0)
                    icon = "✓" if rp_24h > 0 else "⚠"
                    lines.append(
                        f"    {icon} {v['vault_name']}: {rp_24h} baru / {total_rp} total"
                    )
                    resources = v.get("resources_24h", [])
                    for r in resources[:5]:
                        lines.append(f"      - {r.get('name', 'N/A')} ({r.get('type', '-')})")
                    if len(resources) > 5:
                        lines.append(f"      ... dan {len(resources) - 5} resource lain")

        if results.get("monitor_rds_snapshots"):
            rds = results.get("rds_snapshots_24h", 0)
            icon = "✓" if rds > 0 else "⚠"
            lines.append("")
            lines.append(f"  {icon} RDS Snapshots (24 jam): {rds}")

        return "\n".join(lines).rstrip()

    def count_issues(self, result: dict) -> int:
        if result.get("status") == "error":
            return 0
        return int(result.get("failed_jobs", 0) or 0)

    def render_section(self, all_results: dict, errors: list) -> list[str]:
        """Render BACKUP STATUS section for consolidated report."""
        lines = []
        lines.append("")
        lines.append("BACKUP STATUS")

        if errors:
            lines.append("Status: ERROR - Backup check failed")
            for prof, err in errors[:5]:
                lines.append(f"  * {prof}: {err}")
            return lines

        backup_issues = []
        for profile, result in all_results.items():
            if result.get("failed_jobs", 0) > 0 or result.get("issues"):
                backup_issues.append(profile)

        if not backup_issues:
            lines.append("Status: All backup jobs completed successfully")
        else:
            lines.append(f"Status: {len(backup_issues)} accounts with backup issues")
            for profile in backup_issues:
                result = all_results.get(profile, {})
                account_id = result.get("account_id", "Unknown")
                failed = result.get("failed_jobs", 0)
                total = result.get("total_jobs", 0)
                lines.append(
                    f"  * {profile} ({account_id}): {failed} failed / {total} total jobs"
                )

        return lines
