"""AWS VPC checker — audits VPCs for flow log coverage and open security groups."""

import logging
from botocore.exceptions import BotoCoreError, ClientError

from backend.checks.common.base import BaseChecker
from backend.checks.common.aws_errors import is_credential_error

logger = logging.getLogger(__name__)

# Ports considered sensitive — open to 0.0.0.0/0 or ::/0 will be flagged
SENSITIVE_PORTS = {22, 3389, 3306, 5432, 27017, 6379, 11211}


class VPCFlowLogChecker(BaseChecker):
    report_section_title = "VPC SECURITY"
    issue_label = "VPC security issues"
    recommendation_text = "VPC REVIEW: Enable flow logs on all VPCs and restrict sensitive port exposure"

    def check(self, profile, account_id):
        try:
            session = self._get_session(profile)
            ec2 = session.client("ec2", region_name=self.region)

            vpcs = self._list_vpcs(ec2)
            vpc_ids = [v["id"] for v in vpcs]

            # Determine which VPCs have flow logs
            flow_log_vpc_ids = self._get_flow_log_vpc_ids(ec2, vpc_ids)
            for v in vpcs:
                v["flow_logs_enabled"] = v["id"] in flow_log_vpc_ids

            # Check security groups for risky rules
            risky_sgs = self._find_risky_security_groups(ec2)

            vpcs_without_logs = [v for v in vpcs if not v["flow_logs_enabled"]]

            return {
                "status": "success",
                "profile": profile,
                "account_id": account_id,
                "region": self.region,
                "vpc_count": len(vpcs),
                "vpcs_without_flow_logs": len(vpcs_without_logs),
                "risky_security_groups": len(risky_sgs),
                "vpcs": vpcs,
                "risky_sgs": risky_sgs,
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

    def _list_vpcs(self, ec2) -> list[dict]:
        vpcs = []
        paginator = ec2.get_paginator("describe_vpcs")
        for page in paginator.paginate():
            for vpc in page.get("Vpcs", []):
                name = next(
                    (t["Value"] for t in vpc.get("Tags", []) if t.get("Key") == "Name"),
                    vpc.get("VpcId", "-"),
                )
                vpcs.append({
                    "id": vpc["VpcId"],
                    "name": name,
                    "cidr": vpc.get("CidrBlock", "-"),
                    "is_default": vpc.get("IsDefault", False),
                    "state": vpc.get("State", "-"),
                })
        return vpcs

    def _get_flow_log_vpc_ids(self, ec2, vpc_ids: list[str]) -> set[str]:
        if not vpc_ids:
            return set()
        try:
            resp = ec2.describe_flow_logs(
                Filter=[{"Name": "resource-id", "Values": vpc_ids}]
            )
            return {fl["ResourceId"] for fl in resp.get("FlowLogs", []) if fl.get("FlowLogStatus") == "ACTIVE"}
        except Exception:
            return set()

    def _find_risky_security_groups(self, ec2) -> list[dict]:
        risky = []
        paginator = ec2.get_paginator("describe_security_groups")
        for page in paginator.paginate():
            for sg in page.get("SecurityGroups", []):
                for rule in sg.get("IpPermissions", []):
                    from_port = rule.get("FromPort", 0)
                    to_port = rule.get("ToPort", 65535)
                    # open to world
                    open_ipv4 = any(r.get("CidrIp") in ("0.0.0.0/0",) for r in rule.get("IpRanges", []))
                    open_ipv6 = any(r.get("CidrIpv6") in ("::/0",) for r in rule.get("Ipv6Ranges", []))
                    if not (open_ipv4 or open_ipv6):
                        continue
                    # check if any sensitive port is in range
                    for port in SENSITIVE_PORTS:
                        if from_port <= port <= to_port:
                            risky.append({
                                "sg_id": sg["GroupId"],
                                "sg_name": sg.get("GroupName", "-"),
                                "vpc_id": sg.get("VpcId", "-"),
                                "port": port,
                                "open_to": "0.0.0.0/0" if open_ipv4 else "::/0",
                            })
                            break  # one entry per SG is enough
        return risky

    def format_report(self, results):
        if results.get("status") != "success":
            return f"ERROR: {results.get('error')}"

        lines = []
        lines.append(f"┌─ VPC CHECK | {results['profile']} ({results['account_id']}) | {results['region']}")
        lines.append(f"│  VPCs total              : {results['vpc_count']}")
        lines.append(f"│  Without flow logs       : {results['vpcs_without_flow_logs']}")
        lines.append(f"│  Risky security groups   : {results['risky_security_groups']}")

        no_logs = [v for v in results.get("vpcs", []) if not v.get("flow_logs_enabled")]
        if no_logs:
            lines.append("│")
            lines.append("│  ⚠ VPCs without flow logs:")
            for v in no_logs:
                lines.append(f"│    - {v['id']} ({v['name']}) {v['cidr']}")

        risky = results.get("risky_sgs", [])
        if risky:
            lines.append("│")
            lines.append("│  ⚠ Open sensitive ports:")
            for sg in risky[:10]:
                lines.append(f"│    - {sg['sg_id']} ({sg['sg_name']}) port {sg['port']} open to {sg['open_to']}")

        issues = results["vpcs_without_flow_logs"] + results["risky_security_groups"]
        lines.append(f"└─ Status: {'⚠ Issues found' if issues else '✓ VPC config compliant'}")
        return "\n".join(lines)

    def count_issues(self, result: dict) -> int:
        if result.get("status") != "success":
            return 0
        return result.get("vpcs_without_flow_logs", 0) + result.get("risky_security_groups", 0)

    def render_section(self, all_results: dict, errors: list) -> list[str]:
        lines = ["", "VPC SECURITY"]
        if errors:
            lines.append(f"Status: ERROR - {len(errors)} account(s) failed")
            for prof, err in errors[:5]:
                lines.append(f"  * {prof}: {err}")
            return lines

        total_no_logs = sum(r.get("vpcs_without_flow_logs", 0) for r in all_results.values())
        total_risky = sum(r.get("risky_security_groups", 0) for r in all_results.values())

        if total_no_logs > 0:
            lines.append(f"⚠ VPCs without flow logs: {total_no_logs}")
        if total_risky > 0:
            lines.append(f"⚠ Risky security groups: {total_risky}")
            for prof, r in all_results.items():
                for sg in r.get("risky_sgs", [])[:5]:
                    lines.append(f"  * {prof} / {sg['sg_id']} port {sg['port']} open to {sg['open_to']}")
        if total_no_logs == 0 and total_risky == 0:
            lines.append("Status: CLEAR - VPC configuration compliant")
        return lines
