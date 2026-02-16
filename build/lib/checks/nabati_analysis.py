"""
Nabati-specific analysis: CPU usage and cost reporting.
"""

import boto3
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from .base import BaseChecker


class NabatiAnalysis(BaseChecker):
    """Analyze CPU usage and costs for Nabati accounts."""

    def __init__(self, profile: str, region: str = "ap-southeast-3"):
        super().__init__(profile, region)
        self.account_names = {
            "core-network-ksni": "Core Network",
            "data-ksni": "Data",
            "dc-trans-ksni": "DC Trans",
            "edin-ksni": "EDIN",
            "eds-ksni": "EDS",
            "epc-ksni": "EPC",
            "erp-ksni": "ERP",
            "etl-ksni": "ETL",
            "hc-assessment-ksni": "HC Assessment",
            "hc-portal-ksni": "HCPortal",
            "ksni-master": "KSNI Master",
            "ngs-ksni": "NGS",
            "outdig-ksni": "Outdig",
            "outlet-ksni": "Outlet",
            "q-devpro": "Q DevPro",
            "sales-support-pma": "Sales Support",
            "website-ksni": "Website",
        }

    def get_instance_max_cpu(
        self, instance_id: str, start_time: datetime, end_time: datetime
    ) -> Tuple[float, str]:
        """Get maximum CPU utilization for an instance."""
        try:
            cloudwatch = self.session.client("cloudwatch", region_name=self.region)
            response = cloudwatch.get_metric_statistics(
                Namespace="AWS/EC2",
                MetricName="CPUUtilization",
                Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=["Maximum"],
            )

            if response["Datapoints"]:
                max_point = max(response["Datapoints"], key=lambda x: x["Maximum"])
                return max_point["Maximum"], max_point["Timestamp"].strftime(
                    "%d %b at %H:%M WIB"
                )
            return 0.0, ""
        except Exception:
            return 0.0, ""

    def get_instances(self) -> List[Dict]:
        """Get all EC2 instances."""
        try:
            ec2 = self.session.client("ec2", region_name=self.region)
            response = ec2.describe_instances()

            instances = []
            for reservation in response["Reservations"]:
                for instance in reservation["Instances"]:
                    instances.append(
                        {
                            "id": instance["InstanceId"],
                            "state": instance["State"]["Name"],
                        }
                    )
            return instances
        except Exception:
            return []

    def get_monthly_cost(self, start_date: str, end_date: str) -> float:
        """Get monthly cost for the account."""
        try:
            ce = self.session.client("ce", region_name="us-east-1")
            response = ce.get_cost_and_usage(
                TimePeriod={"Start": start_date, "End": end_date},
                Granularity="MONTHLY",
                Metrics=["UnblendedCost"],
            )

            if response["ResultsByTime"]:
                amount = response["ResultsByTime"][0]["Total"]["UnblendedCost"][
                    "Amount"
                ]
                return float(amount)
            return 0.0
        except Exception:
            return 0.0

    def run(self, month: str = None) -> Dict:
        """
        Run Nabati analysis for specified month.
        
        Args:
            month: Month in format 'YYYY-MM' (default: current month)
        """
        if not month:
            now = datetime.now()
            month = now.strftime("%Y-%m")

        year, mon = month.split("-")
        start_date = f"{year}-{mon}-01"

        # Calculate end date (first day of next month)
        if mon == "12":
            end_date = f"{int(year)+1}-01-01"
        else:
            end_date = f"{year}-{int(mon)+1:02d}-01"

        start_time = datetime.strptime(start_date, "%Y-%m-%d")
        end_time = datetime.strptime(end_date, "%Y-%m-%d")

        # Get instances
        instances = self.get_instances()

        if not instances:
            return {
                "profile": self.profile,
                "account_name": self.account_names.get(self.profile, self.profile),
                "max_cpu": 0.0,
                "max_cpu_instance": None,
                "max_cpu_time": "",
                "cost": 0.0,
                "no_instances": True,
            }

        # Find max CPU across all instances
        max_cpu = 0.0
        max_cpu_instance = None
        max_cpu_time = ""

        for instance in instances:
            cpu, timestamp = self.get_instance_max_cpu(
                instance["id"], start_time, end_time
            )
            if cpu > max_cpu:
                max_cpu = cpu
                max_cpu_instance = instance["id"]
                max_cpu_time = timestamp

        # Get cost
        cost = self.get_monthly_cost(start_date, end_date)

        return {
            "profile": self.profile,
            "account_name": self.account_names.get(self.profile, self.profile),
            "max_cpu": max_cpu,
            "max_cpu_instance": max_cpu_instance,
            "max_cpu_time": max_cpu_time,
            "cost": cost,
            "no_instances": False,
        }


def run_nabati_analysis(profiles: List[str], month: str = None) -> Dict:
    """Run Nabati analysis for multiple profiles in parallel."""
    results = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(
                NabatiAnalysis(profile).run, month
            ): profile
            for profile in profiles
        }

        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                profile = futures[future]
                results.append(
                    {
                        "profile": profile,
                        "account_name": profile,
                        "error": str(e),
                    }
                )

    return {"results": results, "month": month or datetime.now().strftime("%Y-%m")}
