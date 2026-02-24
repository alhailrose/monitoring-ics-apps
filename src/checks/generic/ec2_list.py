"""List EC2 instances and Savings Plans for a profile."""
import boto3
from datetime import datetime
from botocore.exceptions import BotoCoreError, ClientError

from src.checks.common.base import BaseChecker
from src.checks.common.aws_errors import is_credential_error


ALLOWED_SP_STATES = [
    "queued",
    "queued-deleted",
    "active",
    "payment-failed",
    "payment-pending",
    "retired",
    "returned",
    "pending-return",
]


class EC2ListChecker(BaseChecker):
    def __init__(self, region="ap-southeast-3", **kwargs):
        super().__init__(region=region, **kwargs)

    def _list_savings_plans(self, session):
        client = session.client("savingsplans", region_name="us-east-1")
        plans = []
        token = None
        while True:
            kwargs = {"states": ALLOWED_SP_STATES}
            if token:
                kwargs["nextToken"] = token
            resp = client.describe_savings_plans(**kwargs)
            for p in resp.get("savingsPlans", []):
                term = p.get("termDurationInSeconds")
                term_years = round(term / (365 * 24 * 3600)) if term else 0
                plan_type = p.get("savingsPlanType", "-")
                region = p.get("region") or ("All (Compute SP)" if plan_type == "Compute" else "-")
                plans.append(
                    {
                        "id": p.get("savingsPlanId", "-"),
                        "type": plan_type,
                        "term_years": term_years,
                        "state": p.get("state", "-"),
                        "region": region,
                        "start": p.get("start", "-"),
                        "end": p.get("end", "-"),
                        "payment": p.get("paymentOption", "-"),
                        "description": p.get("description", ""),
                    }
                )
            token = resp.get("nextToken")
            if not token:
                break
        return plans

    def _list_instances(self, session):
        ec2 = session.client("ec2", region_name=self.region)
        instances = []
        paginator = ec2.get_paginator("describe_instances")
        for page in paginator.paginate():
            for r in page.get("Reservations", []):
                for inst in r.get("Instances", []):
                    name = next((t["Value"] for t in inst.get("Tags", []) if t.get("Key") == "Name"), "-")
                    launch = inst.get("LaunchTime")
                    launch_str = launch.strftime("%Y-%m-%d %H:%M:%S") if isinstance(launch, datetime) else ""
                    instances.append(
                        {
                            "id": inst.get("InstanceId", "-"),
                            "name": name,
                            "type": inst.get("InstanceType", "-"),
                            "state": inst.get("State", {}).get("Name", "-"),
                            "az": inst.get("Placement", {}).get("AvailabilityZone", "-"),
                            "launch": launch_str,
                        }
                    )
        return instances

    def check(self, profile, account_id):
        try:
            session = boto3.Session(profile_name=profile, region_name=self.region)
            plans = self._list_savings_plans(session)
            instances = self._list_instances(session)
            return {
                "status": "success",
                "profile": profile,
                "account_id": account_id,
                "region": self.region,
                "savings_plans": plans,
                "instances": instances,
            }
        except (BotoCoreError, ClientError) as exc:
            if is_credential_error(exc):
                return self._error_result(exc, profile, account_id)
            return {
                "status": "error",
                "profile": profile,
                "account_id": account_id,
                "region": self.region,
                "error": str(exc),
            }

    def format_report(self, results):
        if results.get("status") != "success":
            return f"ERROR: {results.get('error')}"

        lines = []
        plans = results.get("savings_plans", [])
        instances = results.get("instances", [])
        lines.append(f"EC2 LIST | Profile {results.get('profile')} | Region {results.get('region')}")
        lines.append(f"Savings Plans: {len(plans)} found")
        for p in plans:
            lines.append(
                f"  - {p['id']} | {p['type']} | {p['term_years']}-year | {p['state']} | Region {p['region']} | Payment {p['payment']} | Start {p['start']} | End {p['end']}"
            )
        lines.append("")
        lines.append(f"Instances: {len(instances)} found")
        for inst in instances:
            lines.append(
                f"  - {inst['id']} | {inst['name']} | {inst['type']} | {inst['state']} | {inst['az']} | {inst['launch']}"
            )
        return "\n".join(lines)
