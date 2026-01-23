#!/usr/bin/env python3
"""
CloudWatch cost & usage reporter.

Generates a top-N report (cost and usage) for Amazon CloudWatch across all
linked accounts visible from a payer/management account profile. Output is a
pretty Rich table and optional CSV export for sharing.
"""

from __future__ import annotations

import argparse
import csv
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Tuple

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from rich.console import Console
from rich.table import Table


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Report CloudWatch cost & usage per linked account."
    )
    parser.add_argument(
        "--profile",
        default="ksni-master",
        help="AWS CLI profile for the payer/management account (default: ksni-master)",
    )
    parser.add_argument(
        "--region",
        default="ap-southeast-3",
        help="Region to filter on (matches Cost Explorer REGION dimension). "
        "Use ALL or blank to include every region. Default: ap-southeast-3 (Jakarta).",
    )
    parser.add_argument(
        "--start",
        help="Start date (YYYY-MM-DD). Default: first day of current month.",
    )
    parser.add_argument(
        "--end",
        help="End date exclusive (YYYY-MM-DD). Default: tomorrow (covers MTD).",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Show only the top N accounts by cost (default: 10, 0 = show all).",
    )
    parser.add_argument(
        "--csv",
        dest="csv_path",
        help="Optional path to write CSV export.",
    )
    parser.add_argument(
        "--format",
        choices=["table", "markdown", "csv", "json"],
        default="table",
        help="Output format. 'csv' prints to stdout unless --csv is set. Default: table.",
    )
    return parser.parse_args()


def resolve_dates(args: argparse.Namespace) -> Tuple[str, str]:
    today = date.today()
    start = date.fromisoformat(args.start) if args.start else today.replace(day=1)
    end = date.fromisoformat(args.end) if args.end else today + timedelta(days=1)
    return start.isoformat(), end.isoformat()


def build_filter(region: str) -> Dict:
    """Cost Explorer filter for CloudWatch and optional region."""
    base = {"Dimensions": {"Key": "SERVICE", "Values": ["AmazonCloudWatch"]}}
    if region and region.upper() != "ALL":
        return {"And": [base, {"Dimensions": {"Key": "REGION", "Values": [region]}}]}
    return base


def fetch_account_names(session: boto3.Session) -> Dict[str, str]:
    """Best-effort account name lookup via Organizations."""
    names: Dict[str, str] = {}
    try:
        org = session.client("organizations")
        paginator = org.get_paginator("list_accounts")
        for page in paginator.paginate():
            for acc in page["Accounts"]:
                names[acc["Id"]] = acc["Name"]
    except Exception:
        pass  # Organizations access may be denied; fail gracefully.
    return names


def fetch_cost_usage(
    session: boto3.Session, time_range: Tuple[str, str], region: str
) -> List[Dict]:
    ce = session.client("ce")
    start, end = time_range
    resp = ce.get_cost_and_usage(
        TimePeriod={"Start": start, "End": end},
        Granularity="MONTHLY",
        Metrics=["UnblendedCost", "UsageQuantity"],
        Filter=build_filter(region),
        GroupBy=[{"Type": "DIMENSION", "Key": "LINKED_ACCOUNT"}],
    )
    groups = resp.get("ResultsByTime", [{}])[0].get("Groups", [])
    rows: List[Dict] = []
    for g in groups:
        acct = g["Keys"][0]
        m = g["Metrics"]
        rows.append(
            {
                "account": acct,
                "cost": Decimal(m["UnblendedCost"]["Amount"]),
                "usage": Decimal(m["UsageQuantity"]["Amount"]),
            }
        )
    return rows


def format_table(rows: List[Dict], names: Dict[str, str], start: str, end: str, region: str, top: int) -> Table:
    table = Table(title=f"CloudWatch Cost & Usage | Region: {region or 'ALL'} | {start} → {end} (end exclusive)")
    table.add_column("#", justify="right")
    table.add_column("Account")
    table.add_column("Name")
    table.add_column("UnblendedCost (USD)", justify="right")
    table.add_column("UsageQuantity", justify="right")

    rows_sorted = sorted(rows, key=lambda r: r["cost"], reverse=True)
    if top > 0:
        rows_sorted = rows_sorted[:top]

    for idx, r in enumerate(rows_sorted, start=1):
        acct = r["account"]
        name = names.get(acct, "")
        table.add_row(
            str(idx),
            acct,
            name,
            f"${r['cost']:.2f}",
            f"{r['usage']}",
        )

    total_cost = sum(r["cost"] for r in rows)
    total_usage = sum(r["usage"] for r in rows)
    table.add_row("", "", "TOTAL", f"${total_cost:.2f}", f"{total_usage}")
    return table


def format_markdown(rows: List[Dict], names: Dict[str, str], start: str, end: str, region: str, top: int) -> str:
    header = f"CloudWatch Cost & Usage | Region: {region or 'ALL'} | {start} → {end} (end exclusive)\n"
    cols = ["#", "Account", "Name", "UnblendedCost (USD)", "UsageQuantity"]
    lines = []
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("|" + "|".join([" --- "]*len(cols)) + "|")
    rows_sorted = sorted(rows, key=lambda r: r["cost"], reverse=True)
    if top > 0:
        rows_sorted = rows_sorted[:top]
    for idx, r in enumerate(rows_sorted, start=1):
        lines.append(
            "| {idx} | {acct} | {name} | ${cost:.2f} | {usage:.2f} |".format(
                idx=idx,
                acct=r["account"],
                name=names.get(r["account"], ""),
                cost=r["cost"],
                usage=r["usage"],
            )
        )
    total_cost = sum(r["cost"] for r in rows)
    total_usage = sum(r["usage"] for r in rows)
    lines.append(
        "|  |  | TOTAL | ${:.2f} | {:.2f} |".format(total_cost, total_usage)
    )
    return header + "\n".join(lines)


def format_json(rows: List[Dict], names: Dict[str, str]) -> List[Dict]:
    out = []
    for r in rows:
        out.append(
            {
                "account": r["account"],
                "name": names.get(r["account"], ""),
                "unblended_cost_usd": float(r["cost"]),
                "usage_quantity": float(r["usage"]),
            }
        )
    return sorted(out, key=lambda x: x["unblended_cost_usd"], reverse=True)


def maybe_write_csv(rows: List[Dict], names: Dict[str, str], path: str) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["account", "name", "unblended_cost_usd", "usage_quantity"])
        for r in sorted(rows, key=lambda r: r["cost"], reverse=True):
            writer.writerow(
                [r["account"], names.get(r["account"], ""), f"{r['cost']}", f"{r['usage']}"]
            )


def main() -> None:
    args = parse_args()
    start, end = resolve_dates(args)
    console = Console()

    try:
        session = boto3.Session(profile_name=args.profile)
    except Exception as exc:
        console.print(f"[red]Failed to load profile {args.profile}: {exc}[/red]")
        raise SystemExit(1)

    names = fetch_account_names(session)

    try:
        rows = fetch_cost_usage(session, (start, end), args.region)
    except (BotoCoreError, ClientError) as exc:
        console.print(f"[red]Cost Explorer query failed: {exc}[/red]")
        raise SystemExit(2)

    if args.format == "table":
        table = format_table(rows, names, start, end, args.region, args.top)
        console.print(table)
    elif args.format == "markdown":
        md = format_markdown(rows, names, start, end, args.region, args.top)
        console.print(md)
    elif args.format == "csv":
        # stdout CSV unless a file path is given
        if args.csv_path:
            maybe_write_csv(rows, names, args.csv_path)
            console.print(f"[green]CSV written to {args.csv_path}[/green]")
        else:
            writer = csv.writer(console.file)
            writer.writerow(["account", "name", "unblended_cost_usd", "usage_quantity"])
            for r in sorted(rows, key=lambda r: r["cost"], reverse=True):
                writer.writerow(
                    [r["account"], names.get(r["account"], ""), f"{r['cost']}", f"{r['usage']}"]
                )
    elif args.format == "json":
        import json

        data = format_json(rows, names)
        console.print_json(data=data)
    else:
        console.print("[red]Unknown format[/red]")

    # CSV export if requested separately
    if args.csv_path and args.format != "csv":
        maybe_write_csv(rows, names, args.csv_path)
        console.print(f"[green]CSV written to {args.csv_path}[/green]")


if __name__ == "__main__":
    main()
