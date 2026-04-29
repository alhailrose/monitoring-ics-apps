"""AWS Lambda Functions checker — lists functions and surfaces runtime / error-rate issues."""

import logging
from datetime import datetime, timezone, timedelta
from botocore.exceptions import BotoCoreError, ClientError

from backend.checks.common.base import BaseChecker
from backend.checks.common.aws_errors import is_credential_error

logger = logging.getLogger(__name__)

_WIB = timezone(timedelta(hours=7))

# Runtimes that AWS has deprecated or is actively deprecating
DEPRECATED_RUNTIMES = {
    "nodejs",
    "nodejs4.3",
    "nodejs6.10",
    "nodejs8.10",
    "nodejs10.x",
    "nodejs12.x",
    "python2.7",
    "python3.6",
    "python3.7",
    "dotnetcore1.0",
    "dotnetcore2.0",
    "dotnetcore2.1",
    "java8",
    "ruby2.5",
}


class LambdaFunctionChecker(BaseChecker):
    report_section_title = "LAMBDA FUNCTIONS"
    issue_label = "Lambda issues"
    recommendation_text = "LAMBDA REVIEW: Update deprecated runtimes and investigate error-prone functions"

    def check(self, profile, account_id):
        try:
            session = self._get_session(profile)
            client = session.client("lambda", region_name=self.region)
            logs_client = session.client("logs", region_name=self.region)

            functions = []
            paginator = client.get_paginator("list_functions")
            for page in paginator.paginate():
                for fn in page.get("Functions", []):
                    runtime = fn.get("Runtime", "unknown")
                    deprecated = runtime in DEPRECATED_RUNTIMES

                    # Check recent errors via CloudWatch Insights (best-effort)
                    error_count = self._get_error_count(logs_client, fn["FunctionName"])

                    functions.append({
                        "name": fn["FunctionName"],
                        "runtime": runtime,
                        "memory_mb": fn.get("MemorySize", 0),
                        "timeout_s": fn.get("Timeout", 0),
                        "last_modified": fn.get("LastModified", ""),
                        "code_size_mb": round(fn.get("CodeSize", 0) / 1_048_576, 2),
                        "deprecated_runtime": deprecated,
                        "error_count_24h": error_count,
                    })

            deprecated_count = sum(1 for f in functions if f["deprecated_runtime"])
            error_count_total = sum(f["error_count_24h"] for f in functions)

            return {
                "status": "success",
                "profile": profile,
                "account_id": account_id,
                "region": self.region,
                "total": len(functions),
                "deprecated_runtimes": deprecated_count,
                "functions_with_errors": sum(1 for f in functions if f["error_count_24h"] > 0),
                "error_count_24h": error_count_total,
                "functions": functions,
            }

        except (BotoCoreError, ClientError) as exc:
            if is_credential_error(exc):
                return self._error_result(exc, profile, account_id)
            return {
                "status": "error",
                "profile": profile,
                "account_id": account_id,
                "error": str(exc),
            }
        except Exception as exc:
            return self._error_result(exc, profile, account_id)

    def _get_error_count(self, logs_client, function_name: str) -> int:
        """Return error log count from the last 24 h (best-effort, 0 on any failure)."""
        try:
            log_group = f"/aws/lambda/{function_name}"
            end_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            start_ms = end_ms - 86_400_000  # 24 h
            resp = logs_client.filter_log_events(
                logGroupName=log_group,
                startTime=start_ms,
                endTime=end_ms,
                filterPattern="ERROR",
                limit=10,
            )
            return len(resp.get("events", []))
        except Exception:
            return 0

    def format_report(self, results):
        if results.get("status") != "success":
            return f"ERROR: {results.get('error')}"

        lines = []
        lines.append(f"┌─ LAMBDA CHECK | {results['profile']} ({results['account_id']}) | {results['region']}")
        lines.append(f"│  Functions total : {results['total']}")
        lines.append(f"│  Deprecated runtimes : {results['deprecated_runtimes']}")
        lines.append(f"│  Functions with errors (24h) : {results['functions_with_errors']}")

        deprecated = [f for f in results.get("functions", []) if f["deprecated_runtime"]]
        if deprecated:
            lines.append("│")
            lines.append("│  ⚠ Deprecated runtimes:")
            for fn in deprecated[:10]:
                lines.append(f"│    - {fn['name']} ({fn['runtime']})")

        errored = [f for f in results.get("functions", []) if f["error_count_24h"] > 0]
        if errored:
            lines.append("│")
            lines.append("│  ⚠ Functions with errors (24h):")
            for fn in sorted(errored, key=lambda x: -x["error_count_24h"])[:10]:
                lines.append(f"│    - {fn['name']} : {fn['error_count_24h']} errors")

        status = "⚠ Issues found" if (deprecated or errored) else "✓ All functions healthy"
        lines.append(f"└─ Status: {status}")
        return "\n".join(lines)

    def count_issues(self, result: dict) -> int:
        if result.get("status") != "success":
            return 0
        return result.get("deprecated_runtimes", 0) + result.get("functions_with_errors", 0)

    def render_section(self, all_results: dict, errors: list) -> list[str]:
        lines = ["", "LAMBDA FUNCTIONS"]
        if errors:
            lines.append(f"Status: ERROR - {len(errors)} account(s) failed")
            for prof, err in errors[:5]:
                lines.append(f"  * {prof}: {err}")
            return lines

        total_fns = sum(r.get("total", 0) for r in all_results.values())
        total_deprecated = sum(r.get("deprecated_runtimes", 0) for r in all_results.values())
        total_errored = sum(r.get("functions_with_errors", 0) for r in all_results.values())

        lines.append(f"Total functions: {total_fns}")
        if total_deprecated > 0:
            lines.append(f"⚠ Deprecated runtimes: {total_deprecated}")
            for prof, r in all_results.items():
                for fn in r.get("functions", []):
                    if fn["deprecated_runtime"]:
                        lines.append(f"  * {prof} / {fn['name']} ({fn['runtime']})")
        if total_errored > 0:
            lines.append(f"⚠ Functions with errors (24h): {total_errored}")
        if total_deprecated == 0 and total_errored == 0:
            lines.append("Status: CLEAR - No Lambda issues detected")
        return lines
