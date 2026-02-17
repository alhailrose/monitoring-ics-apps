"""AWS Backup status checker (jobs + vault activity + optional RDS snapshots)."""
import boto3
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from src.checks.common.base import BaseChecker


# Jakarta timezone for display
JAKARTA_TZ = timezone(timedelta(hours=7))


# Profiles that still rely on native RDS snapshots (outside AWS Backup)
RDS_ACCOUNTS: List[str] = ["iris-prod"]

# Vaults to monitor per profile (subset from standalone script)
VAULT_CONFIGS: List[Dict[str, str]] = [
    {"profile": "centralized-s3", "vault_name": "central-vault"},
    {"profile": "backup-hris", "vault_name": "central-aws-backup-restricted-account-Feedoctor"},
    {"profile": "backup-hris", "vault_name": "central-aws-backup-restricted-account-IRIS"},
    {"profile": "backup-hris", "vault_name": "central-aws-backup-restricted-account-SFA"},
]


class BackupStatusChecker(BaseChecker):
    """Summarize AWS Backup health for a profile within the last 24h."""

    def __init__(self, region: str = "ap-southeast-3"):
        super().__init__(region)

    def _list_backup_jobs(self, session, since_utc: datetime) -> List[dict]:
        client = session.client("backup", region_name=self.region)
        jobs: List[dict] = []
        token: Optional[str] = None
        while True:
            resp = client.list_backup_jobs(ByCreatedAfter=since_utc, NextToken=token) if token else client.list_backup_jobs(ByCreatedAfter=since_utc)
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
        except Exception:
            pass
        return names

    def _resource_label(self, arn: str) -> str:
        if not arn:
            return "N/A"
        if "/" in arn:
            return arn.split("/")[-1]
        if ":" in arn:
            return arn.split(":")[-1]
        return arn

    def _vault_activity(self, session, profile: str) -> List[dict]:
        """Check configured vaults for recovery point activity in last 24h."""
        vaults = [v for v in VAULT_CONFIGS if v["profile"] == profile]
        results: List[dict] = []
        if not vaults:
            return results

        client = session.client("backup", region_name=self.region)
        since_utc = datetime.now(timezone.utc) - timedelta(hours=24)

        for v in vaults:
            name = v["vault_name"]
            try:
                meta = client.describe_backup_vault(BackupVaultName=name)
                total_points = meta.get("NumberOfRecoveryPoints", 0)
            except Exception as e:  # pragma: no cover - API failure path
                results.append({"vault_name": name, "error": str(e)})
                continue

            rp_24h = 0
            resources_24h: List[str] = []
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
                    resources_24h.extend([r.get("ResourceArn", "") for r in rps if r.get("ResourceArn")])
                    token = resp.get("NextToken")
                    if not token:
                        break
            except Exception as e:  # pragma: no cover
                results.append({"vault_name": name, "error": str(e), "total_recovery_points": total_points})
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
            resp = client.describe_db_snapshots(Marker=token) if token else client.describe_db_snapshots()
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
            session = boto3.Session(profile_name=profile, region_name=self.region)
            # Use full previous day window in WIB (00:00–23:59 yesterday) for daily run
            now_jkt = datetime.now(JAKARTA_TZ)
            start_jkt = (now_jkt - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            since_utc = start_jkt.astimezone(timezone.utc)
            now_utc = now_jkt.astimezone(timezone.utc)

            jobs = self._list_backup_jobs(session, since_utc)
            plans = self._list_backup_plans(session)
            failed = [j for j in jobs if j.get("State") == "FAILED"]
            expired = [j for j in jobs if j.get("State") == "EXPIRED"]
            completed = [j for j in jobs if j.get("State") == "COMPLETED"]

            vaults = self._vault_activity(session, profile)

            rds_24h = 0
            if profile in RDS_ACCOUNTS:
                rds_24h = self._rds_snapshots_24h(session)

            issues = []
            if failed:
                issues.append(f"{len(failed)} failed job(s)")
            if expired:
                issues.append(f"{len(expired)} expired job(s)")
            if vaults:
                no_activity = [v for v in vaults if v.get("recovery_points_24h", 0) == 0 and not v.get("error")]
                if no_activity:
                    issues.append(f"{len(no_activity)} vault(s) no recovery points in 24h")
                vault_errors = [v for v in vaults if v.get("error")]
                if vault_errors:
                    issues.append(f"{len(vault_errors)} vault error(s)")
            if profile in RDS_ACCOUNTS and rds_24h == 0:
                issues.append("No RDS snapshots in 24h")

            status = "ATTENTION REQUIRED" if issues else "OK"

            job_details = []
            for j in jobs[:50]:  # capture more for per-account table (will slice later)
                created = j.get("CreationDate")
                job_details.append(
                    {
                        "job_id": j.get("BackupJobId", ""),
                        "state": j.get("State", ""),
                        "resource": j.get("ResourceArn", ""),
                        "resource_label": self._resource_label(j.get("ResourceArn", "")),
                        "type": j.get("ResourceType", ""),
                        "reason": j.get("StatusMessage") or j.get("FailureMessage") or "",
                        "created": created,
                        "created_wib": created.astimezone(JAKARTA_TZ) if hasattr(created, "astimezone") else created,
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
                "issues": issues,
                "job_details": job_details,
                "backup_plans": plans,
            }

        except Exception as e:  # pragma: no cover
            return {
                "status": "error",
                "profile": profile,
                "account_id": account_id,
                "region": self.region,
                "error": str(e),
            }

    def format_report(self, results):
        if results.get("status") == "error":
            return f"ERROR: {results.get('error')}"

        lines = []
        lines.append("AWS BACKUP STATUS")
        lines.append(f"Region: {results.get('region')}")
        if results.get("checked_at_utc"):
            checked_wib = results['checked_at_utc'].astimezone(JAKARTA_TZ)
            window_wib = results['window_start_utc'].astimezone(JAKARTA_TZ)
            lines.append(
                f"Checked at: {checked_wib.strftime('%Y-%m-%d %H:%M WIB')}"
            )
            lines.append(
                f"Window: {window_wib.strftime('%Y-%m-%d %H:%M')} - {checked_wib.strftime('%Y-%m-%d %H:%M WIB')}"
            )
        lines.append(
            f"Jobs: total {results.get('total_jobs', 0)} | completed {results.get('completed_jobs', 0)} | failed {results.get('failed_jobs', 0)} | expired {results.get('expired_jobs', 0)}"
        )

        # Show failed/expired jobs first with details
        details = results.get("job_details", [])
        failed_jobs = [j for j in details if j.get('state') in ['FAILED', 'EXPIRED']]
        if failed_jobs:
            lines.append("")
            lines.append(f"⚠️ FAILED/EXPIRED JOBS ({len(failed_jobs)}):")
            for j in failed_jobs:
                ts_wib = j.get("created_wib")
                ts_str = ts_wib.strftime('%Y-%m-%d %H:%M WIB') if hasattr(ts_wib, 'strftime') else str(ts_wib)
                reason = j.get('reason', 'No reason provided')
                lines.append(f"- {j.get('state')}: {j.get('resource_label', 'N/A')}")
                lines.append(f"  Time: {ts_str}")
                lines.append(f"  Reason: {reason}")

        # List sample successful jobs (up to 3)
        if details:
            success_jobs = [j for j in details if j.get('state') == 'COMPLETED'][:3]
            if success_jobs:
                lines.append("")
                lines.append("Recent successful jobs (up to 3):")
                for j in success_jobs:
                    ts_wib = j.get("created_wib")
                    ts_str = ts_wib.strftime('%Y-%m-%d %H:%M WIB') if hasattr(ts_wib, 'strftime') else str(ts_wib)
                    lines.append(f"- {j.get('resource_label', 'N/A')} at {ts_str}")

        # Backup plans listing
        plans = results.get("backup_plans", [])
        if plans:
            lines.append("")
            lines.append("Backup plans:")
            for p in plans[:5]:
                lines.append(f"- {p}")

        vaults = results.get("vaults", [])
        if vaults:
            lines.append("")
            lines.append("Vault activity (24h):")
            for v in vaults:
                if v.get("error"):
                    lines.append(f"- {v['vault_name']}: ERROR {v['error']}")
                    continue
                lines.append(
                    f"- {v['vault_name']}: {v.get('recovery_points_24h', 0)} new recovery point(s); total {v.get('total_recovery_points', 0)}"
                )

        if results.get("profile") in RDS_ACCOUNTS:
            lines.append("")
            lines.append(f"RDS snapshots (24h): {results.get('rds_snapshots_24h', 0)}")

        if results.get("issues"):
            lines.append("")
            lines.append("Issues:")
            for i in results["issues"]:
                lines.append(f"- {i}")

        if not results.get("issues"):
            lines.append("")
            lines.append("Status: All backup activities healthy in last 24h")

        return "\n".join(lines)
