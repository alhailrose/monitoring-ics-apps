"""AWS utilization checker for CPU, memory, and disk free."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import boto3

from src.checks.common.aws_errors import is_credential_error
from src.checks.common.base import BaseChecker
from src.checks.generic.aws_utilization_status import (
    DEFAULT_THRESHOLDS,
    classify_instance_status,
)


class AWSUtilization3CoreChecker(BaseChecker):
    report_section_title = "AWS UTILIZATION (CPU / MEMORY / DISK)"
    issue_label = "utilization warning/critical instances"
    recommendation_text = (
        "CAPACITY REVIEW: Investigate warning/critical utilization instances"
    )

    def __init__(self, region: str = "ap-southeast-3", **kwargs):
        super().__init__(region=region, **kwargs)
        self.util_hours = int(kwargs.get("util_hours", 12))
        self.period_seconds = int(kwargs.get("period_seconds", 300))
        self.thresholds = dict(DEFAULT_THRESHOLDS)
        threshold_overrides = kwargs.get("thresholds")
        if isinstance(threshold_overrides, dict):
            for key, value in threshold_overrides.items():
                if key in self.thresholds and isinstance(value, (int, float)):
                    self.thresholds[key] = float(value)

        for key in self.thresholds:
            override = kwargs.get(key)
            if isinstance(override, (int, float)):
                self.thresholds[key] = float(override)

        self.profile_regions = dict(kwargs.get("profile_regions", {}) or {})

    @staticmethod
    def _instance_name(row: dict[str, Any]) -> str:
        for tag in row.get("Tags", []) or []:
            if tag.get("Key") == "Name":
                return str(tag.get("Value") or "-")
        return "-"

    @staticmethod
    def _instance_os_type(row: dict[str, Any]) -> str:
        platform = str(row.get("Platform") or "").lower()
        platform_details = str(row.get("PlatformDetails") or "").lower()
        if "windows" in platform or "windows" in platform_details:
            return "windows"
        return "linux"

    @staticmethod
    def _round2(value: float | None) -> float | None:
        if isinstance(value, (int, float)):
            return round(float(value), 2)
        return None

    def _create_session(self, profile: str):
        return boto3.Session(profile_name=profile)

    def _discover_regions(self, session, profile: str | None = None) -> list[str]:
        configured = []
        if profile and profile in self.profile_regions:
            configured = [
                str(region).strip()
                for region in (self.profile_regions.get(profile) or [])
                if str(region).strip()
            ]
        if configured:
            return configured

        try:
            ec2 = session.client("ec2", region_name=self.region)
            regions = [
                item.get("RegionName")
                for item in ec2.describe_regions(AllRegions=False).get("Regions", [])
                if item.get("RegionName")
            ]
            if regions:
                return regions
        except Exception:
            pass
        return [self.region]

    def _list_instances(self, session, regions: list[str]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()

        for region in regions:
            try:
                ec2 = session.client("ec2", region_name=region)
                paginator = ec2.get_paginator("describe_instances")
                for page in paginator.paginate():
                    for reservation in page.get("Reservations", []) or []:
                        for inst in reservation.get("Instances", []) or []:
                            instance_id = inst.get("InstanceId")
                            if not instance_id or instance_id in seen:
                                continue
                            state = str(
                                ((inst.get("State") or {}).get("Name")) or "unknown"
                            )
                            if state.lower() != "running":
                                continue
                            seen.add(instance_id)
                            rows.append(
                                {
                                    "instance_id": str(instance_id),
                                    "name": self._instance_name(inst),
                                    "state": state,
                                    "os_type": self._instance_os_type(inst),
                                    "instance_type": str(
                                        inst.get("InstanceType") or ""
                                    ),
                                    "region": region,
                                }
                            )
            except Exception:
                continue

        return rows

    @staticmethod
    def _stat_from_datapoints(
        datapoints: list[dict[str, Any]],
    ) -> tuple[float | None, float | None, datetime | None]:
        values: list[float] = []
        peak_value: float | None = None
        peak_time: datetime | None = None
        for point in datapoints or []:
            val = point.get("Average")
            if isinstance(val, (int, float)):
                numeric_val = float(val)
                values.append(numeric_val)
                if peak_value is None or numeric_val >= peak_value:
                    peak_value = numeric_val
                    timestamp = point.get("Timestamp")
                    if isinstance(timestamp, datetime):
                        peak_time = timestamp
        if not values:
            return None, None, None
        return (sum(values) / len(values), peak_value, peak_time)

    @staticmethod
    def _format_peak_time(value: datetime | None) -> str | None:
        if not isinstance(value, datetime):
            return None
        return value.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")

    def _get_metric_summary(
        self,
        cloudwatch,
        namespace: str,
        metric_name: str,
        dimensions: list[dict[str, str]],
        start_time: datetime,
        end_time: datetime,
    ) -> tuple[float | None, float | None, datetime | None]:
        out = cloudwatch.get_metric_statistics(
            Namespace=namespace,
            MetricName=metric_name,
            Dimensions=dimensions,
            StartTime=start_time,
            EndTime=end_time,
            Period=self.period_seconds,
            Statistics=["Average"],
        )
        return self._stat_from_datapoints(out.get("Datapoints", []) or [])

    def _get_cpu_usage(
        self,
        cloudwatch,
        instance_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> tuple[float | None, float | None, datetime | None]:
        return self._get_metric_summary(
            cloudwatch,
            namespace="AWS/EC2",
            metric_name="CPUUtilization",
            dimensions=[{"Name": "InstanceId", "Value": instance_id}],
            start_time=start_time,
            end_time=end_time,
        )

    def _get_instance_total_memory_bytes(
        self, session, region: str, instance_type: str
    ) -> float | None:
        """Return total physical RAM in bytes for an instance type via EC2."""
        if not instance_type:
            return None
        try:
            ec2 = session.client("ec2", region_name=region)
            resp = ec2.describe_instance_types(InstanceTypes=[instance_type])
            size_mib = (
                (resp.get("InstanceTypes") or [{}])[0]
                .get("MemoryInfo", {})
                .get("SizeInMiB")
            )
            if isinstance(size_mib, (int, float)):
                return float(size_mib) * 1024 * 1024
        except Exception:
            pass
        return None

    def _get_memory_from_available_bytes(
        self,
        cloudwatch,
        instance_id: str,
        start_time: datetime,
        end_time: datetime,
        total_memory_bytes: float | None = None,
    ) -> tuple[float | None, float | None, str | None, datetime | None]:
        """Compute memory used% from Memory Available Bytes.

        Total physical RAM must be supplied via total_memory_bytes (from EC2
        describe_instance_types), since CloudWatch Agent does not emit a
        Memory Total Bytes metric for Windows.

        Returns (avg_used_pct, peak_used_pct, metric_name, peak_at) or
        (None, None, None, None) if the metric is not available.
        """
        if not isinstance(total_memory_bytes, (int, float)) or total_memory_bytes <= 0:
            return None, None, None, None

        try:
            listed = cloudwatch.list_metrics(
                Namespace="CWAgent",
                MetricName="Memory Available Bytes",
                Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
            )
        except Exception:
            return None, None, None, None

        for metric_def in listed.get("Metrics", []) or []:
            dims = metric_def.get("Dimensions", []) or []
            try:
                avail_out = cloudwatch.get_metric_statistics(
                    Namespace="CWAgent",
                    MetricName="Memory Available Bytes",
                    Dimensions=dims,
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=self.period_seconds,
                    Statistics=["Average"],
                )
            except Exception:
                continue

            datapoints = avail_out.get("Datapoints") or []
            used_pct_values: list[float] = []
            peak_used_pct: float | None = None
            peak_at: datetime | None = None

            for point in datapoints:
                avg_avail = point.get("Average")
                if not isinstance(avg_avail, (int, float)):
                    continue
                used_pct = (1.0 - float(avg_avail) / total_memory_bytes) * 100.0
                used_pct_values.append(used_pct)
                if peak_used_pct is None or used_pct >= peak_used_pct:
                    peak_used_pct = used_pct
                    ts = point.get("Timestamp")
                    if isinstance(ts, datetime):
                        peak_at = ts

            if not used_pct_values:
                continue

            avg_used_pct = sum(used_pct_values) / len(used_pct_values)
            return avg_used_pct, peak_used_pct, "Memory Available Bytes", peak_at

        return None, None, None, None

    def _get_memory_usage(
        self,
        cloudwatch,
        instance_id: str,
        os_type: str,
        start_time: datetime,
        end_time: datetime,
        total_memory_bytes: float | None = None,
    ) -> tuple[float | None, float | None, str | None, datetime | None]:
        if os_type == "windows":
            result = self._get_memory_from_available_bytes(
                cloudwatch, instance_id, start_time, end_time,
                total_memory_bytes=total_memory_bytes,
            )
            if result[0] is not None:
                return result

        metric_names = ["mem_used_percent"]
        if os_type == "windows":
            metric_names = ["Memory % Committed Bytes In Use", "mem_used_percent"]

        for metric_name in metric_names:
            try:
                listed = cloudwatch.list_metrics(
                    Namespace="CWAgent",
                    MetricName=metric_name,
                    Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                )
            except Exception:
                continue

            for metric_def in listed.get("Metrics", []) or []:
                dims = metric_def.get("Dimensions", []) or []
                try:
                    avg_val, peak_val, peak_at = self._get_metric_summary(
                        cloudwatch,
                        namespace="CWAgent",
                        metric_name=metric_name,
                        dimensions=dims,
                        start_time=start_time,
                        end_time=end_time,
                    )
                except Exception:
                    continue
                if avg_val is not None:
                    return avg_val, peak_val, metric_name, peak_at

        return None, None, None, None

    def _get_disk_free_min(
        self,
        cloudwatch,
        instance_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> float | None:
        ignored_fstypes = {
            "squashfs",
            "tmpfs",
            "devtmpfs",
            "overlay",
            "proc",
            "sysfs",
            "cgroup",
            "cgroup2",
            "cgroup2fs",
            "ramfs",
            "devpts",
            "securityfs",
            "tracefs",
            "pstore",
            "autofs",
            "fusectl",
            "configfs",
            "debugfs",
            "mqueue",
        }

        def _should_include_metric(dimensions: list[dict[str, str]]) -> bool:
            dim_map = {
                str(d.get("Name") or ""): str(d.get("Value") or "")
                for d in dimensions or []
            }
            fstype = dim_map.get("fstype", "").strip().lower()
            path = dim_map.get("path", "").strip().lower()
            device = dim_map.get("device", "").strip().lower()

            if path.startswith("/snap/"):
                return False
            if fstype in ignored_fstypes:
                return False
            if device.startswith("loop") and fstype == "squashfs":
                return False
            return True

        try:
            listed = cloudwatch.list_metrics(
                Namespace="CWAgent",
                MetricName="disk_used_percent",
                Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
            )
        except Exception:
            return None

        free_candidates: list[float] = []
        for metric_def in listed.get("Metrics", []) or []:
            dims = metric_def.get("Dimensions", []) or []
            if not _should_include_metric(dims):
                continue
            try:
                _avg_used, peak_used, _peak_at = self._get_metric_summary(
                    cloudwatch,
                    namespace="CWAgent",
                    metric_name="disk_used_percent",
                    dimensions=dims,
                    start_time=start_time,
                    end_time=end_time,
                )
            except Exception:
                continue
            if peak_used is None:
                continue
            free_candidates.append(100.0 - float(peak_used))

        if not free_candidates:
            return None
        return min(free_candidates)

    def _collect_instance_metrics(
        self,
        session,
        instance: dict[str, Any],
        start_time: datetime,
        end_time: datetime,
    ) -> dict[str, Any]:
        cloudwatch = session.client("cloudwatch", region_name=instance["region"])

        total_memory_bytes: float | None = None
        if instance.get("os_type") == "windows" and instance.get("instance_type"):
            total_memory_bytes = self._get_instance_total_memory_bytes(
                session, instance["region"], instance["instance_type"]
            )

        cpu_avg, cpu_peak, cpu_peak_at = self._get_cpu_usage(
            cloudwatch,
            instance["instance_id"],
            start_time,
            end_time,
        )
        mem_avg, mem_peak, mem_metric, mem_peak_at = self._get_memory_usage(
            cloudwatch,
            instance["instance_id"],
            instance["os_type"],
            start_time,
            end_time,
            total_memory_bytes=total_memory_bytes,
        )
        disk_free_min = self._get_disk_free_min(
            cloudwatch,
            instance["instance_id"],
            start_time,
            end_time,
        )

        status = classify_instance_status(
            cpu_peak=cpu_peak,
            memory_peak=mem_peak,
            disk_free_min=disk_free_min,
            thresholds=self.thresholds,
        )

        memory_note = None
        disk_note = None
        if mem_peak is None:
            memory_note = (
                "CWAgent memory metric tidak tersedia (agent/konfigurasi belum ada)"
            )
        if disk_free_min is None:
            disk_note = (
                "CWAgent disk metric tidak tersedia (agent/konfigurasi belum ada)"
            )

        return {
            **instance,
            "cpu_avg_12h": self._round2(cpu_avg),
            "cpu_peak_12h": self._round2(cpu_peak),
            "cpu_peak_at_12h": self._format_peak_time(cpu_peak_at),
            "memory_avg_12h": self._round2(mem_avg),
            "memory_peak_12h": self._round2(mem_peak),
            "memory_peak_at_12h": self._format_peak_time(mem_peak_at),
            "memory_metric": mem_metric,
            "memory_note": memory_note,
            "disk_free_min_percent": self._round2(disk_free_min),
            "disk_note": disk_note,
            "status": status,
        }

    @staticmethod
    def _build_summary(instance_rows: list[dict[str, Any]]) -> dict[str, int]:
        summary = {
            "normal": 0,
            "warning": 0,
            "critical": 0,
            "partial_data": 0,
            "total": len(instance_rows),
        }
        for row in instance_rows:
            status = str(row.get("status") or "").upper()
            if status == "CRITICAL":
                summary["critical"] += 1
            elif status == "WARNING":
                summary["warning"] += 1
            elif status == "NORMAL":
                summary["normal"] += 1
            else:
                summary["partial_data"] += 1
        return summary

    def check(self, profile: str, account_id: str) -> dict[str, Any]:
        try:
            session = self._create_session(profile)
            regions = self._discover_regions(session, profile=profile)
            instances = self._list_instances(session, regions)

            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=self.util_hours)

            rows: list[dict[str, Any]] = []
            for instance in instances:
                try:
                    rows.append(
                        self._collect_instance_metrics(
                            session, instance, start_time, end_time
                        )
                    )
                except Exception:
                    rows.append(
                        {
                            **instance,
                            "cpu_avg_12h": None,
                            "cpu_peak_12h": None,
                            "cpu_peak_at_12h": None,
                            "memory_avg_12h": None,
                            "memory_peak_12h": None,
                            "memory_peak_at_12h": None,
                            "memory_metric": None,
                            "memory_note": "Metric memory tidak dapat diambil",
                            "disk_free_min_percent": None,
                            "disk_note": "Metric disk tidak dapat diambil",
                            "status": "PARTIAL_DATA",
                        }
                    )

            return {
                "status": "success",
                "profile": profile,
                "account_id": account_id,
                "region": self.region,
                "generated_at": datetime.now()
                .astimezone()
                .strftime("%Y-%m-%d %H:%M:%S %Z"),
                "util_window": {
                    "hours": self.util_hours,
                    "from": start_time.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
                    "to": end_time.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
                },
                "instances": rows,
                "summary": self._build_summary(rows),
            }
        except Exception as exc:
            if is_credential_error(exc):
                return self._error_result(exc, profile, account_id)
            return {
                "status": "error",
                "profile": profile,
                "account_id": account_id,
                "region": self.region,
                "error": str(exc),
            }

    @staticmethod
    def _fmt_pct(value: float | None) -> str:
        if isinstance(value, (int, float)):
            return f"{float(value):.2f}%"
        return "N/A"

    def format_report(self, results: dict[str, Any]) -> str:
        if results.get("status") != "success":
            return f"ERROR: {results.get('error', 'unknown error')}"

        summary = results.get("summary", {})
        lines = [
            f"AWS UTILIZATION 3-CORE | Profile {results.get('profile')} | Window {self.util_hours}h",
            (
                "Summary: "
                f"NORMAL={summary.get('normal', 0)} "
                f"WARNING={summary.get('warning', 0)} "
                f"CRITICAL={summary.get('critical', 0)} "
                f"PARTIAL_DATA={summary.get('partial_data', 0)}"
            ),
            "Instances:",
        ]

        order = {"CRITICAL": 0, "WARNING": 1, "PARTIAL_DATA": 2, "NORMAL": 3}
        rows = sorted(
            results.get("instances", []),
            key=lambda row: (
                order.get(str((row or {}).get("status") or "NORMAL"), 9),
                str((row or {}).get("instance_id") or ""),
            ),
        )
        for row in rows:
            notes = []
            if row.get("memory_note"):
                notes.append(str(row.get("memory_note")))
            if row.get("disk_note"):
                notes.append(str(row.get("disk_note")))
            notes_text = f" | NOTE={'; '.join(notes)}" if notes else ""
            lines.append(
                (
                    f"- {row.get('instance_id')} ({row.get('name', '-')}) | "
                    f"OS={row.get('os_type', '-')}/{row.get('region', '-')} | "
                    f"CPU(avg/peak)={self._fmt_pct(row.get('cpu_avg_12h'))}/{self._fmt_pct(row.get('cpu_peak_12h'))} | "
                    f"MEM(avg/peak)={self._fmt_pct(row.get('memory_avg_12h'))}/{self._fmt_pct(row.get('memory_peak_12h'))} | "
                    f"DISK_FREE_MIN={self._fmt_pct(row.get('disk_free_min_percent'))} | "
                    f"STATUS={row.get('status', 'PARTIAL_DATA')}{notes_text}"
                )
            )
        return "\n".join(lines)

    def count_issues(self, result: dict) -> int:
        if result.get("status") != "success":
            return 0
        issue_count = 0
        for row in result.get("instances", []) or []:
            status = str((row or {}).get("status") or "").upper()
            if status in {"WARNING", "CRITICAL"}:
                issue_count += 1
        return issue_count

    def render_section(self, all_results: dict, errors: list) -> list[str]:
        lines: list[str] = ["", self.report_section_title]

        if not all_results and not errors:
            lines.append("Status: No data available")
            return lines

        if all_results:
            lines.append("Accounts:")
            for profile, result in all_results.items():
                if not isinstance(result, dict) or result.get("status") != "success":
                    msg = "invalid result payload"
                    if isinstance(result, dict):
                        msg = str(result.get("error") or msg)
                    lines.append(f"  * {profile}: ERROR - {msg}")
                    continue

                summary = result.get("summary") or {}
                account_id = result.get("account_id", "Unknown")
                lines.append(
                    (
                        f"  * {profile} ({account_id}) -> "
                        f"normal={summary.get('normal', 0)} | "
                        f"warning={summary.get('warning', 0)} | "
                        f"critical={summary.get('critical', 0)} | "
                        f"partial_data={summary.get('partial_data', 0)}"
                    )
                )

                order = {"CRITICAL": 0, "WARNING": 1, "PARTIAL_DATA": 2, "NORMAL": 3}
                rows = sorted(
                    result.get("instances", []) or [],
                    key=lambda row: (
                        order.get(str((row or {}).get("status") or "NORMAL"), 9),
                        str((row or {}).get("instance_id") or ""),
                    ),
                )
                for row in rows:
                    notes = []
                    if row.get("memory_note"):
                        notes.append(str(row.get("memory_note")))
                    if row.get("disk_note"):
                        notes.append(str(row.get("disk_note")))
                    notes_text = f" | note={'; '.join(notes)}" if notes else ""
                    lines.append(
                        (
                            f"    - {row.get('instance_id', 'unknown')} ({row.get('name', '-')}) | "
                            f"CPU peak={self._fmt_pct(row.get('cpu_peak_12h'))} | "
                            f"MEM peak={self._fmt_pct(row.get('memory_peak_12h'))} | "
                            f"DISK free min={self._fmt_pct(row.get('disk_free_min_percent'))} | "
                            f"status={row.get('status', 'PARTIAL_DATA')}{notes_text}"
                        )
                    )

        if errors:
            lines.append("Errors:")
            for profile, message in errors:
                lines.append(f"  * {profile}: ERROR - {message}")

        return lines
