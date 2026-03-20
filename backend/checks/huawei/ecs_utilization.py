"""Huawei ECS utilization checker (Cloud Eye metrics via hcloud CLI)."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from typing import Any

from backend.checks.common.base import BaseChecker
from backend.domain.formatting.reports import (
    build_huawei_utilization_customer_report,
    classify_huawei_memory_behavior,
)


def sanitize_json(raw: str) -> str:
    start_obj = raw.find("{")
    start_arr = raw.find("[")
    starts = [s for s in (start_obj, start_arr) if s != -1]
    if not starts:
        return raw.strip()
    return raw[min(starts) :].strip()


def profile_to_account(profile: str) -> str:
    return profile[:-3] if profile.endswith("-ro") else profile


def classify_memory_behavior(row: dict[str, Any], rise_threshold: float) -> str:
    # Compatibility alias for existing imports/tests.
    return classify_huawei_memory_behavior(row, rise_threshold)


class HcloudCli:
    def __init__(
        self,
        read_timeout: int = 30,
        connect_timeout: int = 10,
        retry_count: int = 2,
        max_attempts: int = 2,
    ) -> None:
        self.read_timeout = int(read_timeout)
        self.connect_timeout = int(connect_timeout)
        self.retry_count = int(retry_count)
        self.max_attempts = max(1, int(max_attempts))

    def _with_transport_flags(self, args: list[str]) -> list[str]:
        out = list(args)
        if not any(a.startswith("--cli-read-timeout=") for a in out):
            out.append(f"--cli-read-timeout={self.read_timeout}")
        if not any(a.startswith("--cli-connect-timeout=") for a in out):
            out.append(f"--cli-connect-timeout={self.connect_timeout}")
        if not any(a.startswith("--cli-retry-count=") for a in out):
            out.append(f"--cli-retry-count={self.retry_count}")
        return out

    @staticmethod
    def _is_timeout_error(message: str) -> bool:
        text = (message or "").lower()
        return "timed out" in text or "timeout" in text

    @staticmethod
    def _is_invalid_param_error(message: str) -> bool:
        text = (message or "").lower()
        return "invalid parameter" in text

    def _process_timeout_seconds(self) -> int:
        # Hard-stop hcloud process to avoid indefinite hangs in interactive mode.
        return max(10, self.read_timeout + self.connect_timeout + 5)

    def run_json(self, args: list[str]) -> tuple[dict[str, Any] | list[Any] | None, str | None]:
        last_error: str | None = None
        use_transport_flags = True
        process_timeout = self._process_timeout_seconds()

        for attempt in range(self.max_attempts):
            cmd_args = self._with_transport_flags(args) if use_transport_flags else list(args)
            try:
                proc = subprocess.run(
                    ["hcloud", *cmd_args],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=process_timeout,
                )
            except FileNotFoundError:
                return None, "hcloud binary not found in PATH"
            except subprocess.TimeoutExpired as exc:
                timed_out_after = int(getattr(exc, "timeout", process_timeout) or process_timeout)
                last_error = f"hcloud command timed out after {timed_out_after} seconds"
                should_retry = attempt < (self.max_attempts - 1)
                if should_retry:
                    continue
                break

            out = proc.stdout or ""
            err = proc.stderr or ""
            cleaned = sanitize_json(out)

            if cleaned:
                try:
                    data = json.loads(cleaned)
                    return data, None
                except Exception:
                    last_error = (err.strip() or out.strip() or "failed to parse hcloud output as json")[:500]
            else:
                last_error = err.strip() or "empty response from hcloud"

            if use_transport_flags and self._is_invalid_param_error(last_error or ""):
                use_transport_flags = False
                continue

            should_retry = attempt < (self.max_attempts - 1) and self._is_timeout_error(last_error or "")
            if not should_retry:
                break

        return None, last_error


class HuaweiECSUtilizationChecker(BaseChecker):
    """Utilization-only checker for Huawei ECS (CPU/Memory)."""

    report_section_title = "HUAWEI ECS MEMORY HOTSPOTS"
    issue_label = "memory hotspot findings"
    recommendation_text = "PERFORMANCE REVIEW: Investigate ECS memory hotspot instances"

    def __init__(self, region: str = "ap-southeast-4", **kwargs):
        super().__init__(region=region, **kwargs)
        self.util_hours = int(kwargs.get("util_hours", 12))
        self.rise_threshold = float(kwargs.get("rise_threshold", 70.0))
        self.top = int(kwargs.get("top", 10))
        self.page_limit = int(kwargs.get("page_limit", 1000))
        self.cli = HcloudCli()

    def _list_server_map(self, profile: str, region: str) -> tuple[dict[str, dict[str, str]], str | None]:
        out: dict[str, dict[str, str]] = {}
        offset = 1
        fetched = 0
        total_count: int | None = None
        last_err: str | None = None

        while True:
            data, err = self.cli.run_json(
                [
                    "ECS",
                    "ListServersDetails",
                    f"--cli-profile={profile}",
                    f"--cli-region={region}",
                    f"--limit={self.page_limit}",
                    f"--offset={offset}",
                    "--cli-output=json",
                ]
            )
            if not isinstance(data, dict):
                last_err = err
                if out:
                    break
                return {}, err

            servers = data.get("servers") or []
            if not isinstance(servers, list):
                servers = []

            count_val = data.get("count")
            if isinstance(count_val, int):
                total_count = count_val

            if not servers:
                break

            fetched += len(servers)
            for row in servers:
                sid = str(row.get("id", ""))
                if not sid:
                    continue
                out[sid] = {
                    "name": str(row.get("name", "-")),
                    "status": str(row.get("status", "-")),
                }

            if total_count is not None:
                if fetched >= total_count:
                    break
            elif len(servers) < self.page_limit:
                break
            offset += 1

        if not out and last_err:
            return {}, last_err
        return out, None

    def _list_metrics(self, profile: str, region: str, namespace: str, metric_name: str) -> list[dict[str, Any]]:
        metrics: list[dict[str, Any]] = []
        start_token: str | None = None
        seen_tokens: set[str] = set()
        total_count: int | None = None

        while True:
            args = [
                "CES",
                "ListMetrics",
                f"--cli-profile={profile}",
                f"--cli-region={region}",
                f"--limit={self.page_limit}",
                f"--namespace={namespace}",
                f"--metric_name={metric_name}",
                "--cli-output=json",
            ]
            if start_token:
                args.append(f"--start={start_token}")

            data, _ = self.cli.run_json(args)
            if not isinstance(data, dict):
                break

            page_metrics = data.get("metrics") or []
            if not isinstance(page_metrics, list):
                page_metrics = []

            for item in page_metrics:
                if isinstance(item, dict):
                    metrics.append(item)

            meta_data = data.get("meta_data")
            if isinstance(meta_data, dict):
                total_val = meta_data.get("total")
                if isinstance(total_val, int):
                    total_count = total_val
                next_token = meta_data.get("marker")
            else:
                next_token = None

            if total_count is not None and len(metrics) >= total_count:
                break

            if not isinstance(next_token, str) or not next_token:
                break
            if next_token in seen_tokens:
                break
            seen_tokens.add(next_token)
            start_token = next_token

            if not page_metrics:
                break

        return metrics

    def _metric_instance_ids(self, metrics: list[dict[str, Any]]) -> list[str]:
        ids: set[str] = set()
        for m in metrics:
            for d in m.get("dimensions") or []:
                if d.get("name") == "instance_id" and d.get("value"):
                    ids.add(str(d["value"]))
        return sorted(ids)

    def _show_metric_data(
        self,
        profile: str,
        region: str,
        namespace: str,
        metric_name: str,
        instance_id: str,
        from_ms: int,
        to_ms: int,
    ) -> tuple[float | None, float | None, int | None, int | None, int | None, float | None]:
        data, _ = self.cli.run_json(
            [
                "CES",
                "ShowMetricData",
                f"--cli-profile={profile}",
                f"--cli-region={region}",
                f"--namespace={namespace}",
                f"--metric_name={metric_name}",
                f"--dim.0=instance_id,{instance_id}",
                "--filter=average",
                "--period=300",
                f"--from={from_ms}",
                f"--to={to_ms}",
                "--cli-output=json",
            ]
        )
        if not isinstance(data, dict):
            return None, None, None, None, None, None

        datapoints = data.get("datapoints") or []
        if not datapoints:
            return None, None, None, None, None, None

        datapoints = sorted(datapoints, key=lambda x: x.get("timestamp", 0))
        latest = datapoints[-1].get("average")
        latest_ts = datapoints[-1].get("timestamp")

        samples: list[tuple[int, float]] = []
        for dp in datapoints:
            avg = dp.get("average")
            ts = dp.get("timestamp")
            if isinstance(avg, (int, float)) and isinstance(ts, int):
                samples.append((ts, float(avg)))

        if not samples:
            return (
                float(latest) if isinstance(latest, (int, float)) else None,
                None,
                int(latest_ts) if isinstance(latest_ts, int) else None,
                None,
                None,
                None,
            )

        peak_idx = max(range(len(samples)), key=lambda i: samples[i][1])
        peak_ts, peak_val = samples[peak_idx]

        rise_start_idx = peak_idx
        while rise_start_idx > 0 and samples[rise_start_idx - 1][1] <= samples[rise_start_idx][1]:
            rise_start_idx -= 1
        rise_start_ts = samples[rise_start_idx][0] if rise_start_idx < peak_idx else None

        avg_12h = sum(v for _, v in samples) / len(samples)
        return (
            float(latest) if isinstance(latest, (int, float)) else None,
            peak_val,
            int(latest_ts) if isinstance(latest_ts, int) else None,
            peak_ts,
            rise_start_ts,
            avg_12h,
        )

    def _top_utilization(
        self,
        profile: str,
        region: str,
        server_map: dict[str, dict[str, str]],
        namespace: str,
        metric_name: str,
        from_ms: int,
        to_ms: int,
    ) -> tuple[list[dict[str, Any]], float | None]:
        metrics = self._list_metrics(profile, region, namespace=namespace, metric_name=metric_name)
        ids = self._metric_instance_ids(metrics)
        rows: list[dict[str, Any]] = []

        for iid in ids:
            latest, peak, latest_ts, peak_ts, rise_start_ts, avg_12h = self._show_metric_data(
                profile,
                region,
                namespace,
                metric_name,
                iid,
                from_ms,
                to_ms,
            )
            if latest is None:
                continue
            meta = server_map.get(iid, {})
            rows.append(
                {
                    "instance_id": iid,
                    "name": meta.get("name", "-"),
                    "status": meta.get("status", "-"),
                    "latest": round(float(latest), 2),
                    "peak": round(float(peak), 2) if peak is not None else None,
                    "avg_12h": round(float(avg_12h), 2) if avg_12h is not None else None,
                    "timestamp_ms": latest_ts,
                    "peak_time_ms": peak_ts,
                    "rise_start_ms": rise_start_ts,
                }
            )

        rows.sort(key=lambda x: x["latest"], reverse=True)
        avg_candidates = [float(x["avg_12h"]) for x in rows if isinstance(x.get("avg_12h"), (int, float))]
        avg_profile = round(sum(avg_candidates) / len(avg_candidates), 2) if avg_candidates else None
        return rows, avg_profile

    @staticmethod
    def _pick_peak_row(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
        candidates = [r for r in rows if isinstance(r.get("peak"), (int, float))]
        if not candidates:
            return None
        return max(candidates, key=lambda r: float(r["peak"]))

    def check(self, profile: str, account_id: str) -> dict[str, Any]:
        cfg_data, cfg_err = self.cli.run_json(["configure", "show", f"--cli-profile={profile}"])
        if not isinstance(cfg_data, dict):
            return {
                "status": "error",
                "profile": profile,
                "region": self.region,
                "error": cfg_err or "profile config not found",
            }

        cfg_region = str(cfg_data.get("region") or "")
        resolved_region = self.region or cfg_region or "ap-southeast-4"

        end_ms = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
        start_ms = end_ms - (self.util_hours * 3600 * 1000)

        server_map, err = self._list_server_map(profile, resolved_region)
        if err and not server_map:
            return {
                "status": "error",
                "profile": profile,
                "region": resolved_region,
                "error": err,
            }

        cpu_rows, cpu_avg_12h = self._top_utilization(
            profile,
            resolved_region,
            server_map,
            "SYS.ECS",
            "cpu_util",
            start_ms,
            end_ms,
        )
        mem_rows, mem_avg_12h = self._top_utilization(
            profile,
            resolved_region,
            server_map,
            "AGT.ECS",
            "mem_usedPercent",
            start_ms,
            end_ms,
        )

        cpu_peak = self._pick_peak_row(cpu_rows)
        mem_peak = self._pick_peak_row(mem_rows)

        hot_mem: list[dict[str, Any]] = []
        for row in mem_rows:
            peak = row.get("peak")
            if isinstance(peak, (int, float)) and float(peak) > self.rise_threshold:
                row_copy = dict(row)
                row_copy["behavior"] = classify_memory_behavior(row_copy, self.rise_threshold)
                hot_mem.append(row_copy)

        profile_account = profile_to_account(profile)
        sso_account_id = ((cfg_data.get("ssoAuth") or {}).get("accountId")) or account_id

        return {
            "status": "success",
            "profile": profile,
            "account": profile_account,
            "account_id": sso_account_id,
            "region": resolved_region,
            "generated_at": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
            "util_window": {
                "from_ms": start_ms,
                "to_ms": end_ms,
                "from": datetime.fromtimestamp(start_ms / 1000).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
                "to": datetime.fromtimestamp(end_ms / 1000).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
            },
            "rise_threshold": self.rise_threshold,
            "util": {
                "ecs_total": len(server_map),
                "cpu_avg_12h": cpu_avg_12h,
                "cpu_peak_overall": cpu_peak,
                "mem_avg_12h": mem_avg_12h,
                "mem_peak_overall": mem_peak,
                "top_mem_hot": hot_mem[: self.top],
            },
        }

    def format_report(self, results: dict[str, Any]) -> str:
        return build_huawei_utilization_customer_report(results)

    def count_issues(self, result: dict) -> int:
        if result.get("status") != "success":
            return 0

        util = result.get("util")
        if not isinstance(util, dict):
            return 0

        top_mem_hot = util.get("top_mem_hot")
        if isinstance(top_mem_hot, list):
            return len(top_mem_hot)
        return 0

    def render_section(self, all_results: dict, errors: list) -> list[str]:
        lines: list[str] = ["", self.report_section_title]
        error_profiles = {profile for profile, _ in errors}

        if not all_results and not errors:
            lines.append("Status: No data available")
            return lines

        if all_results:
            lines.append("Accounts:")
            for profile, result in all_results.items():
                account_id = result.get("account_id", "Unknown") if isinstance(result, dict) else "Unknown"
                if not isinstance(result, dict) or result.get("status") != "success":
                    if profile in error_profiles:
                        continue
                    msg = result.get("error", "invalid result payload") if isinstance(result, dict) else "invalid result payload"
                    lines.append(f"  * {profile} ({account_id}): ERROR - {msg}")
                    continue

                util = result.get("util")
                top_mem_hot = util.get("top_mem_hot") if isinstance(util, dict) else None

                if not isinstance(top_mem_hot, list) or len(top_mem_hot) == 0:
                    lines.append(f"  * {profile} ({account_id}): no data for hot memory instances")
                    continue

                lines.append(f"  * {profile} ({account_id}): {len(top_mem_hot)} hot memory instance(s)")
                for item in top_mem_hot:
                    if isinstance(item, dict):
                        name = item.get("name") or item.get("instance_id") or "unknown-instance"
                        peak = item.get("peak")
                        behavior = item.get("behavior")
                        detail = f"    - {name}"
                        if peak is not None:
                            detail += f" peak={peak}"
                        if behavior:
                            detail += f" behavior={behavior}"
                        lines.append(detail)
                    else:
                        lines.append(f"    - {item}")

        if errors:
            lines.append("Errors:")
            for profile, message in errors:
                lines.append(f"  * {profile}: ERROR - {message}")

        return lines
