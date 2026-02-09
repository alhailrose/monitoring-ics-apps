"""Daily HRIS checker (EC2 CPU/Network/Disk/Memory + GuardDuty)."""
import boto3
from datetime import datetime, timedelta, timezone
from typing import List
from zoneinfo import ZoneInfo

from .base import BaseChecker

JKT = ZoneInfo("Asia/Jakarta")
WINDOW_HOURS = 12
PERIOD_SECONDS = 300

ACCOUNT_NAME = "HRIS"
ACCOUNT_ID = "493314732063"

# Instance configs: profile for EC2 metrics, cw_profile for CWAgent metrics
INSTANCES = {
    "webserver": {
        "id": "i-053c5b7302686e05d",
        "name": "aryanoble-prod-Window2019Base-webserver",
        "profile": "HRIS",
        "cw_profile": "HRIS",
        "image_id": "ami-07aac508243767ec7",
        "instance_type": "r5.xlarge",
        "disks": ["C:", "D:"],
    },
    "database": {
        "id": "i-0a22fd1fc782f71dc",
        "name": "aryanoble-prod-Windows2019+SQL2019Standard-database",
        "profile": "HRIS",
        "cw_profile": "backup-hris",
        "image_id": "ami-01de394c524569bc6",
        "instance_type": "r5.2xlarge",
        "disks": ["C:", "D:", "E:", "F:", "G:"],
    },
}

THRESHOLDS = {
    "CPUUtilization": 75,
    "NetworkIn": 500 * 1024 * 1024,    # 500 MB/5min
    "NetworkOut": 500 * 1024 * 1024,
    "Memory": 85,                       # % committed
    "Disk": 20,                         # % free space (below = warn)
}


def now_jkt():
    return datetime.now(timezone.utc).astimezone(JKT)


def human_mb(b):
    return f"{b / (1024**2):.0f} MB"


class DailyHRISChecker(BaseChecker):
    def __init__(self, region: str = "ap-southeast-3"):
        super().__init__(region)

    def _get_metric_data(self, cw, namespace, metric_name, dimensions):
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=WINDOW_HOURS)
        r = cw.get_metric_statistics(
            Namespace=namespace, MetricName=metric_name,
            Dimensions=dimensions,
            StartTime=start, EndTime=end,
            Period=PERIOD_SECONDS, Statistics=["Average"],
        )
        pts = sorted(r.get("Datapoints", []), key=lambda x: x["Timestamp"])
        if not pts:
            return None
        vals = [p["Average"] for p in pts]
        times = [p["Timestamp"] for p in pts]
        return {"values": vals, "timestamps": times, "last": vals[-1], "max": max(vals), "min": min(vals)}

    def _breach_range(self, data, threshold, comparator):
        if not data:
            return None
        vals, times = data["values"], data["timestamps"]
        if comparator == "above":
            breached = [(t, v) for t, v in zip(times, vals) if v > threshold]
        else:
            breached = [(t, v) for t, v in zip(times, vals) if v < threshold]
        if not breached:
            return None
        peak = max(breached, key=lambda x: x[1]) if comparator == "above" else min(breached, key=lambda x: x[1])
        first = breached[0][0].astimezone(JKT).strftime("%H:%M")
        last = breached[-1][0].astimezone(JKT).strftime("%H:%M")
        return peak[1], first, last

    def _check_guardduty(self, session):
        try:
            gd = session.client("guardduty", region_name=self.region)
            detectors = gd.list_detectors().get("DetectorIds", [])
            if not detectors:
                return "no-data", "GuardDuty tidak aktif"
            detector_id = detectors[0]
            end = datetime.now(timezone.utc)
            start = end.replace(hour=0, minute=0, second=0, microsecond=0)
            findings = gd.list_findings(
                DetectorId=detector_id,
                FindingCriteria={
                    "Criterion": {
                        "updatedAt": {"GreaterThanOrEqual": int(start.timestamp() * 1000)},
                        "severity": {"GreaterThanOrEqual": 4},
                    }
                },
            ).get("FindingIds", [])
            if not findings:
                return "ok", "GuardDuty = Tidak ada findings medium/high terbaru pada hari ini"
            return "warn", f"GuardDuty = {len(findings)} findings medium/high ditemukan hari ini"
        except Exception as e:
            return "error", f"GuardDuty = Error: {e}"

    def _check_instance(self, inst_cfg):
        ec2_session = boto3.Session(profile_name=inst_cfg["profile"], region_name=self.region)
        cw_ec2 = ec2_session.client("cloudwatch", region_name=self.region)

        cw_agent_session = boto3.Session(profile_name=inst_cfg["cw_profile"], region_name=self.region)
        cw_agent = cw_agent_session.client("cloudwatch", region_name=self.region)

        inst_id = inst_cfg["id"]
        inst_name = inst_cfg["name"]
        ec2_dims = [{"Name": "InstanceId", "Value": inst_id}]
        results = []

        # CPU
        cpu = self._get_metric_data(cw_ec2, "AWS/EC2", "CPUUtilization", ec2_dims)
        thr = THRESHOLDS["CPUUtilization"]
        if cpu:
            bd = self._breach_range(cpu, thr, "above")
            if cpu["last"] > thr:
                results.append(("warn", f"Utilisasi CPU = {cpu['last']:.0f}% (di atas {thr}%) pada {inst_name} | max {cpu['max']:.0f}% pukul {bd[1]}-{bd[2]} WIB" if bd else f"Utilisasi CPU = {cpu['last']:.0f}% pada {inst_name}"))
            elif bd:
                results.append(("past-warn", f"Utilisasi CPU = CPU sempat mengalami spike hingga {bd[0]:.0f}% pada {inst_name} pukul {bd[1]}-{bd[2]} WIB"))
            else:
                results.append(("ok", f"Utilisasi CPU = {cpu['last']:.0f}% normal pada {inst_name}"))

        # NetworkIn
        netin = self._get_metric_data(cw_ec2, "AWS/EC2", "NetworkIn", ec2_dims)
        thr_net = THRESHOLDS["NetworkIn"]
        if netin:
            bd = self._breach_range(netin, thr_net, "above")
            if bd:
                results.append(("past-warn", f"Utilisasi NetworkIn = terdapat Spike pada instance {inst_name} | max {human_mb(bd[0])}/5min pukul {bd[1]}-{bd[2]} WIB"))
            else:
                results.append(("ok", f"Utilisasi NetworkIn = normal pada {inst_name}"))

        # NetworkOut
        netout = self._get_metric_data(cw_ec2, "AWS/EC2", "NetworkOut", ec2_dims)
        if netout:
            bd = self._breach_range(netout, thr_net, "above")
            if bd:
                results.append(("past-warn", f"Utilisasi NetworkOut = terdapat Spike pada instance {inst_name} | max {human_mb(bd[0])}/5min pukul {bd[1]}-{bd[2]} WIB"))
            else:
                results.append(("ok", f"Utilisasi NetworkOut = normal pada {inst_name}"))

        # Memory (CWAgent)
        agent_dims = [
            {"Name": "InstanceId", "Value": inst_id},
            {"Name": "ImageId", "Value": inst_cfg["image_id"]},
            {"Name": "objectname", "Value": "Memory"},
            {"Name": "InstanceType", "Value": inst_cfg["instance_type"]},
        ]
        mem = self._get_metric_data(cw_agent, "CWAgent", "Memory % Committed Bytes In Use", agent_dims)
        thr_mem = THRESHOLDS["Memory"]
        if mem:
            bd = self._breach_range(mem, thr_mem, "above")
            if mem["last"] > thr_mem:
                msg = f"Memory = {mem['last']:.0f}% used (tinggi > {thr_mem}%) pada {inst_name}"
                if bd:
                    msg += f" | max {bd[0]:.0f}% pukul {bd[1]}-{bd[2]} WIB"
                results.append(("warn", msg))
            elif bd:
                results.append(("past-warn", f"Memory = {mem['last']:.0f}% used pada {inst_name} (sempat > {thr_mem}% | max {bd[0]:.0f}% pukul {bd[1]}-{bd[2]} WIB)"))
            else:
                results.append(("ok", f"Memory = {mem['last']:.0f}% used pada {inst_name} (normal)"))

        # Disk per drive (CWAgent)
        thr_disk = THRESHOLDS["Disk"]
        for drive in inst_cfg["disks"]:
            disk_dims = [
                {"Name": "InstanceId", "Value": inst_id},
                {"Name": "instance", "Value": drive},
                {"Name": "ImageId", "Value": inst_cfg["image_id"]},
                {"Name": "objectname", "Value": "LogicalDisk"},
                {"Name": "InstanceType", "Value": inst_cfg["instance_type"]},
            ]
            disk = self._get_metric_data(cw_agent, "CWAgent", "LogicalDisk % Free Space", disk_dims)
            if disk:
                bd = self._breach_range(disk, thr_disk, "below")
                if disk["last"] < thr_disk:
                    results.append(("warn", f"Disk {drive} pada {inst_name} = {disk['last']:.0f}% free (rendah < {thr_disk}%) | min {disk['min']:.0f}%"))
                elif bd:
                    results.append(("past-warn", f"Disk {drive} pada {inst_name} = {disk['last']:.0f}% free (sempat < {thr_disk}% | min {bd[0]:.0f}% pukul {bd[1]}-{bd[2]} WIB)"))
                else:
                    results.append(("ok", f"Disk {drive} pada {inst_name} = {disk['last']:.0f}% free (normal)"))

        return results

    def check(self, profile=None, account_id=None):
        try:
            session = boto3.Session(profile_name="HRIS", region_name=self.region)

            # GuardDuty
            gd_status, gd_msg = self._check_guardduty(session)

            # Per-instance checks
            instance_results = {}
            any_warn = False
            for role, cfg in INSTANCES.items():
                checks = self._check_instance(cfg)
                instance_results[role] = {"name": cfg["name"], "checks": checks}
                if any(s == "warn" for s, _ in checks):
                    any_warn = True

            if gd_status == "warn":
                any_warn = True

            return {
                "status": "ATTENTION REQUIRED" if any_warn else "OK",
                "account_name": ACCOUNT_NAME,
                "account_id": ACCOUNT_ID,
                "guardduty": {"status": gd_status, "message": gd_msg},
                "instances": instance_results,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def format_report(self, results):
        if results.get("status") == "error":
            return f"ERROR: {results.get('error')}"

        now = now_jkt()
        greeting = "Selamat Pagi" if 5 <= now.hour < 18 else "Selamat Malam"
        waktu = "Pagi" if 5 <= now.hour < 18 else "Malam"
        date_str = now.strftime("%d-%m-%Y")

        lines: List[str] = []
        lines.append(f"{greeting} Team,")
        lines.append(f"Berikut Daily report untuk akun id {results.get('account_name')} ({results.get('account_id')}) pada {waktu} ini")
        lines.append(date_str)

        # GuardDuty
        gd = results.get("guardduty", {})
        lines.append(f"* {gd.get('message', 'GuardDuty = N/A')}")

        # Per-instance metrics
        for role, data in results.get("instances", {}).items():
            for status, msg in data.get("checks", []):
                lines.append(f"* {msg}")

        return "\n".join(lines)
