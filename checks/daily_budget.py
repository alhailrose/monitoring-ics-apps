"""Daily budget checker for AWS Budgets (threshold + over budget)."""

from decimal import Decimal

import boto3

from .base import BaseChecker


ACCOUNT_LABELS = {
    "connect-prod": "Connect Prod (Non Cis)",
    "cis-erha": "CIS Erha",
    "dermies-max": "Dermies Max",
    "erha-buddy": "Erha Buddy",
    "public-web": "Public Web",
    "HRIS": "HRIS",
    "fee-doctor": "Fee Doctor",
    "tgw": "TGW",
    "iris-prod": "Iris Prod",
    "sfa": "SFA",
    "centralized-s3": "Centralized S3",
    "backup-hris": "Backup HRIS",
}


class DailyBudgetChecker(BaseChecker):
    def _account_name(self, profile):
        return ACCOUNT_LABELS.get(profile, profile.replace("-", " ").title())

    def _is_threshold_hit(self, percent, notif):
        if notif.get("NotificationType") != "ACTUAL":
            return False
        if notif.get("ComparisonOperator") != "GREATER_THAN":
            return False
        threshold = notif.get("Threshold")
        if threshold is None:
            return False
        return percent > float(threshold)

    def check(self, profile, account_id):
        try:
            session = boto3.Session(profile_name=profile, region_name=self.region)
            budgets = session.client("budgets", region_name="us-east-1")

            items = []
            token = None
            while True:
                kwargs = {"AccountId": account_id}
                if token:
                    kwargs["NextToken"] = token
                resp = budgets.describe_budgets(**kwargs)

                for budget in resp.get("Budgets", []):
                    if budget.get("TimeUnit") != "DAILY":
                        continue

                    name = budget.get("BudgetName", "")
                    limit = Decimal(
                        (budget.get("BudgetLimit") or {}).get("Amount", "0")
                    )
                    if limit <= 0:
                        continue

                    actual = Decimal(
                        (budget.get("CalculatedSpend") or {})
                        .get("ActualSpend", {})
                        .get("Amount", "0")
                    )
                    percent = float((actual / limit) * Decimal("100"))
                    over = actual - limit

                    notif_resp = budgets.describe_notifications_for_budget(
                        AccountId=account_id,
                        BudgetName=name,
                    )
                    threshold_hits = []
                    for n in notif_resp.get("Notifications", []):
                        if self._is_threshold_hit(percent, n):
                            threshold_hits.append(float(n.get("Threshold", 0)))

                    threshold_hits = sorted(set(threshold_hits))
                    items.append(
                        {
                            "budget_name": name,
                            "actual": float(actual),
                            "limit": float(limit),
                            "percent": percent,
                            "over_amount": float(over),
                            "is_over_budget": actual > limit,
                            "threshold_hits": threshold_hits,
                        }
                    )

                token = resp.get("NextToken")
                if not token:
                    break

            threshold_exceeded_count = sum(1 for i in items if i["threshold_hits"])
            over_budget_count = sum(1 for i in items if i["is_over_budget"])
            has_alert = threshold_exceeded_count > 0 or over_budget_count > 0

            return {
                "status": "ATTENTION REQUIRED" if has_alert else "OK",
                "profile": profile,
                "account_id": account_id,
                "account_name": self._account_name(profile),
                "items": sorted(items, key=lambda x: x["percent"], reverse=True),
                "threshold_exceeded_count": threshold_exceeded_count,
                "over_budget_count": over_budget_count,
            }
        except Exception as exc:
            return {
                "status": "error",
                "profile": profile,
                "account_id": account_id,
                "error": str(exc),
            }

    def format_report(self, results):
        if results.get("status") == "error":
            return f"ERROR: {results.get('error', '')}"

        acct = results.get("account_id", "")
        name = results.get("account_name", results.get("profile", ""))
        lines = [f"Account {acct} - {name}"]

        items = [
            x
            for x in results.get("items", [])
            if x.get("threshold_hits") or x.get("is_over_budget")
        ]
        if not items:
            lines.append("- Tidak ada budget melewati alert threshold")
            return "\n".join(lines)

        for it in items:
            base = (
                f"- {it['budget_name']}: ${it['actual']:.2f} / ${it['limit']:.2f} "
                f"({it['percent']:.2f}%)"
            )
            if it.get("is_over_budget"):
                base += f" -> Over ${it['over_amount']:.2f}"
            elif it.get("threshold_hits"):
                threshold_text = ", ".join(f"{t:.0f}%" for t in it["threshold_hits"])
                base += f" -> Exceeded alert threshold ({threshold_text})"
            lines.append(base)
        return "\n".join(lines)
