"""AWS ECS checker — lists clusters/services, surfaces stopped tasks and unhealthy services."""

import logging
from botocore.exceptions import BotoCoreError, ClientError

from backend.checks.common.base import BaseChecker
from backend.checks.common.aws_errors import is_credential_error

logger = logging.getLogger(__name__)


class ECSServiceChecker(BaseChecker):
    report_section_title = "ECS SERVICES"
    issue_label = "ECS service issues"
    recommendation_text = "ECS REVIEW: Investigate stopped/unhealthy services and restart tasks"

    def check(self, profile, account_id):
        try:
            session = self._get_session(profile)
            client = session.client("ecs", region_name=self.region)

            clusters = self._list_clusters(client)
            services = []
            stopped_tasks_total = 0

            for cluster_arn in clusters:
                cluster_name = cluster_arn.split("/")[-1]
                svcs = self._list_services(client, cluster_arn)
                for svc in svcs:
                    svc["cluster"] = cluster_name
                    services.append(svc)

                # Check for recently stopped tasks (potential crash-loops)
                stopped = self._list_stopped_tasks(client, cluster_arn)
                stopped_tasks_total += stopped

            unhealthy = [s for s in services if s.get("running", 0) < s.get("desired", 0)]

            return {
                "status": "success",
                "profile": profile,
                "account_id": account_id,
                "region": self.region,
                "cluster_count": len(clusters),
                "service_count": len(services),
                "unhealthy_services": len(unhealthy),
                "stopped_tasks": stopped_tasks_total,
                "services": services,
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

    def _list_clusters(self, client) -> list[str]:
        arns = []
        paginator = client.get_paginator("list_clusters")
        for page in paginator.paginate():
            arns.extend(page.get("clusterArns", []))
        return arns

    def _list_services(self, client, cluster_arn: str) -> list[dict]:
        service_arns = []
        paginator = client.get_paginator("list_services")
        for page in paginator.paginate(cluster=cluster_arn):
            service_arns.extend(page.get("serviceArns", []))

        services = []
        # describe_services accepts max 10 at a time
        for i in range(0, len(service_arns), 10):
            batch = service_arns[i:i + 10]
            resp = client.describe_services(cluster=cluster_arn, services=batch)
            for svc in resp.get("services", []):
                services.append({
                    "name": svc.get("serviceName", "-"),
                    "status": svc.get("status", "-"),
                    "desired": svc.get("desiredCount", 0),
                    "running": svc.get("runningCount", 0),
                    "pending": svc.get("pendingCount", 0),
                    "launch_type": svc.get("launchType", "FARGATE"),
                })
        return services

    def _list_stopped_tasks(self, client, cluster_arn: str) -> int:
        """Count recently stopped tasks (best-effort)."""
        try:
            resp = client.list_tasks(cluster=cluster_arn, desiredStatus="STOPPED", maxResults=100)
            return len(resp.get("taskArns", []))
        except Exception:
            return 0

    def format_report(self, results):
        if results.get("status") != "success":
            return f"ERROR: {results.get('error')}"

        lines = []
        lines.append(f"┌─ ECS CHECK | {results['profile']} ({results['account_id']}) | {results['region']}")
        lines.append(f"│  Clusters  : {results['cluster_count']}")
        lines.append(f"│  Services  : {results['service_count']}")
        lines.append(f"│  Unhealthy : {results['unhealthy_services']}")
        lines.append(f"│  Stopped tasks (recent) : {results['stopped_tasks']}")

        unhealthy = [s for s in results.get("services", []) if s.get("running", 0) < s.get("desired", 0)]
        if unhealthy:
            lines.append("│")
            lines.append("│  ⚠ Unhealthy services (running < desired):")
            for svc in unhealthy[:15]:
                lines.append(f"│    [{svc['cluster']}] {svc['name']} — {svc['running']}/{svc['desired']} running")

        ok = results["unhealthy_services"] == 0 and results["stopped_tasks"] == 0
        lines.append(f"└─ Status: {'✓ All services healthy' if ok else '⚠ Issues found'}")
        return "\n".join(lines)

    def count_issues(self, result: dict) -> int:
        if result.get("status") != "success":
            return 0
        return result.get("unhealthy_services", 0) + (1 if result.get("stopped_tasks", 0) > 0 else 0)

    def render_section(self, all_results: dict, errors: list) -> list[str]:
        lines = ["", "ECS SERVICES"]
        if errors:
            lines.append(f"Status: ERROR - {len(errors)} account(s) failed")
            for prof, err in errors[:5]:
                lines.append(f"  * {prof}: {err}")
            return lines

        total_unhealthy = sum(r.get("unhealthy_services", 0) for r in all_results.values())
        total_stopped = sum(r.get("stopped_tasks", 0) for r in all_results.values())
        total_services = sum(r.get("service_count", 0) for r in all_results.values())

        lines.append(f"Total services: {total_services}")
        if total_unhealthy > 0:
            lines.append(f"⚠ Unhealthy services: {total_unhealthy}")
            for prof, r in all_results.items():
                for svc in r.get("services", []):
                    if svc.get("running", 0) < svc.get("desired", 0):
                        lines.append(f"  * {prof} / [{svc['cluster']}] {svc['name']} {svc['running']}/{svc['desired']}")
        if total_stopped > 0:
            lines.append(f"⚠ Stopped tasks total: {total_stopped}")
        if total_unhealthy == 0 and total_stopped == 0:
            lines.append("Status: CLEAR - All ECS services healthy")
        return lines
