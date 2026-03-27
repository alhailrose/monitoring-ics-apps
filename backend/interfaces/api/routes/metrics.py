"""Metric sample query endpoints."""

import csv
import html
from io import StringIO

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

from backend.interfaces.api.dependencies import get_check_repository

router = APIRouter(prefix="/metrics", tags=["metrics"])


class MetricAccountResponse(BaseModel):
    id: str
    profile_name: str
    display_name: str


class MetricCustomerResponse(BaseModel):
    id: str
    display_name: str


class MetricItemResponse(BaseModel):
    id: str
    check_run_id: str
    customer: MetricCustomerResponse
    account: MetricAccountResponse
    check_name: str
    metric_name: str
    metric_status: str
    value_num: float | None = None
    unit: str | None = None
    resource_role: str | None = None
    resource_id: str | None = None
    resource_name: str | None = None
    service_type: str | None = None
    section_name: str | None = None
    created_at: str


class MetricListResponse(BaseModel):
    total: int
    items: list[MetricItemResponse]


class MetricTimeseriesItem(BaseModel):
    date: str
    metric_name: str
    account_id: str
    account_display_name: str
    avg_value: float | None = None
    max_value: float | None = None
    sample_count: int


class MetricTimeseriesResponse(BaseModel):
    items: list[MetricTimeseriesItem]


class WorkloadCoverageResponse(BaseModel):
    total_runs: int
    expected_runs: int
    completion_rate: float
    days_met_target: int
    days_missing_target: int


class WorkloadDailyRunResponse(BaseModel):
    date: str
    runs: int


class WorkloadFluctuationResponse(BaseModel):
    metric_name: str
    sample_count: int
    days_with_samples: int
    avg_value: float
    min_value: float
    max_value: float
    daily_avg_range: float


class WorkloadResourceFluctuationResponse(BaseModel):
    account_display_name: str
    resource_id: str
    resource_name: str
    metric_name: str
    sample_count: int
    days_with_samples: int
    avg_value: float
    min_value: float
    max_value: float
    daily_avg_range: float


class MonthlyStuckItemResponse(BaseModel):
    check_name: str
    account_display_name: str
    severity: str
    title: str
    age_days: int
    last_seen_at: str


class MonthlyStuckSummaryResponse(BaseModel):
    threshold_days: int
    guardduty_active: int
    cloudwatch_active: int
    guardduty_stuck: int
    cloudwatch_stuck: int
    items: list[MonthlyStuckItemResponse] = Field(default_factory=list)


class MonthlyCostAccountResponse(BaseModel):
    account_display_name: str
    anomalies_today_peak: float
    anomalies_total_peak: float


class MonthlyCostSummaryResponse(BaseModel):
    impacted_accounts: int
    accounts: list[MonthlyCostAccountResponse] = Field(default_factory=list)


class WorkloadMonthlyReportResponse(BaseModel):
    customer_id: str
    month: str
    metric_fluctuations: list[WorkloadFluctuationResponse]
    resource_fluctuations: list[WorkloadResourceFluctuationResponse] = Field(
        default_factory=list
    )
    stuck_summary: MonthlyStuckSummaryResponse = Field(
        default_factory=lambda: MonthlyStuckSummaryResponse(
            threshold_days=7,
            guardduty_active=0,
            cloudwatch_active=0,
            guardduty_stuck=0,
            cloudwatch_stuck=0,
        )
    )
    cost_summary: MonthlyCostSummaryResponse = Field(
        default_factory=lambda: MonthlyCostSummaryResponse(impacted_accounts=0)
    )


def _public_monthly_report_payload(report: dict) -> dict:
    return {
        "customer_id": report.get("customer_id"),
        "month": report.get("month"),
        "metric_fluctuations": report.get("metric_fluctuations", []),
        "resource_fluctuations": report.get("resource_fluctuations", []),
        "stuck_summary": report.get("stuck_summary", {}),
        "cost_summary": report.get("cost_summary", {}),
    }


def _fmt_num(value: float | int | None) -> str:
    if value is None:
        return "-"
    if isinstance(value, int):
        return str(value)
    return f"{value:.2f}"


def _render_metric_line_chart(metric_name: str, points: list[dict]) -> str:
    if len(points) < 2:
        return (
            f"<div class='card'><h3>{html.escape(metric_name)}</h3>"
            "<p class='meta'>Data harian belum cukup untuk trend chart.</p></div>"
        )

    width = 640
    height = 210
    pad = 28
    plot_w = width - (pad * 2)
    plot_h = height - (pad * 2)

    avg_vals = [float(p.get("avg_value") or 0.0) for p in points]
    max_vals = [float(p.get("max_value") or 0.0) for p in points]
    all_vals = avg_vals + max_vals
    min_v = min(all_vals)
    max_v = max(all_vals)
    span = max_v - min_v
    if span == 0:
        span = 1.0

    def _xy(index: int, value: float) -> tuple[float, float]:
        x = pad + (index * (plot_w / max(1, len(points) - 1)))
        y = height - pad - ((value - min_v) / span) * plot_h
        return x, y

    avg_poly = " ".join(
        f"{_xy(i, v)[0]:.2f},{_xy(i, v)[1]:.2f}" for i, v in enumerate(avg_vals)
    )
    max_poly = " ".join(
        f"{_xy(i, v)[0]:.2f},{_xy(i, v)[1]:.2f}" for i, v in enumerate(max_vals)
    )

    first_date = html.escape(str(points[0].get("date", "-")))
    last_date = html.escape(str(points[-1].get("date", "-")))

    return (
        "<div class='card'>"
        f"<h3>{html.escape(metric_name)}</h3>"
        "<svg viewBox='0 0 640 210' class='line-chart' role='img' aria-label='trend chart'>"
        f"<line x1='{pad}' y1='{height - pad}' x2='{width - pad}' y2='{height - pad}' stroke='#d1d5db' stroke-width='1' />"
        f"<line x1='{pad}' y1='{pad}' x2='{pad}' y2='{height - pad}' stroke='#d1d5db' stroke-width='1' />"
        f"<polyline fill='none' stroke='#2563eb' stroke-width='2' points='{avg_poly}' />"
        f"<polyline fill='none' stroke='#f97316' stroke-width='2' points='{max_poly}' />"
        f"<text x='{pad}' y='{height - 8}' font-size='10' fill='#6b7280'>{first_date}</text>"
        f"<text x='{width - pad}' y='{height - 8}' text-anchor='end' font-size='10' fill='#6b7280'>{last_date}</text>"
        f"<text x='{pad}' y='12' font-size='10' fill='#6b7280'>max {_fmt_num(max_v)}</text>"
        f"<text x='{pad}' y='{height - pad + 12}' font-size='10' fill='#6b7280'>min {_fmt_num(min_v)}</text>"
        "</svg>"
        "<p class='meta'>Biru = avg harian, Oranye = puncak harian</p>"
        "</div>"
    )


def _render_monthly_report_html(report: dict) -> str:
    monthly = html.escape(str(report.get("month", "-")))
    customer_id = html.escape(str(report.get("customer_id", "-")))
    stuck = report.get("stuck_summary", {}) or {}
    cost_summary = report.get("cost_summary", {}) or {}

    metric_rows = "".join(
        (
            "<tr>"
            f"<td>{html.escape(str(item.get('metric_name', '-')))}</td>"
            f"<td>{int(item.get('sample_count', 0) or 0)}</td>"
            f"<td>{int(item.get('days_with_samples', 0) or 0)}</td>"
            f"<td>{_fmt_num(item.get('avg_value'))}</td>"
            f"<td>{_fmt_num(item.get('min_value'))}</td>"
            f"<td>{_fmt_num(item.get('max_value'))}</td>"
            f"<td>{_fmt_num(item.get('daily_avg_range'))}</td>"
            "</tr>"
        )
        for item in (report.get("metric_fluctuations", []) or [])[:25]
    )
    if not metric_rows:
        metric_rows = "<tr><td colspan='7'>Belum ada data metric workload</td></tr>"

    resource_rows = "".join(
        (
            "<tr>"
            f"<td>{html.escape(str(item.get('account_display_name', '-')))}</td>"
            f"<td>{html.escape(str(item.get('resource_id', '-')))}</td>"
            f"<td>{html.escape(str(item.get('resource_name', '-')))}</td>"
            f"<td>{html.escape(str(item.get('metric_name', '-')))}</td>"
            f"<td>{int(item.get('sample_count', 0) or 0)}</td>"
            f"<td>{_fmt_num(item.get('daily_avg_range'))}</td>"
            "</tr>"
        )
        for item in (report.get("resource_fluctuations", []) or [])[:50]
    )
    if not resource_rows:
        resource_rows = (
            "<tr><td colspan='6'>Belum ada data resource-level fluctuation</td></tr>"
        )

    stuck_rows = "".join(
        (
            "<tr>"
            f"<td>{html.escape(str(item.get('check_name', '-')))}</td>"
            f"<td>{html.escape(str(item.get('account_display_name', '-')))}</td>"
            f"<td>{html.escape(str(item.get('title', '-')))}</td>"
            f"<td>{html.escape(str(item.get('severity', '-')))}</td>"
            f"<td>{int(item.get('age_days', 0) or 0)}</td>"
            "</tr>"
        )
        for item in (stuck.get("items", []) or [])[:25]
    )
    if not stuck_rows:
        stuck_rows = "<tr><td colspan='5'>Tidak ada issue stuck aktif</td></tr>"

    cost_rows = "".join(
        (
            "<tr>"
            f"<td>{html.escape(str(item.get('account_display_name', '-')))}</td>"
            f"<td>{_fmt_num(item.get('anomalies_today_peak'))}</td>"
            f"<td>{_fmt_num(item.get('anomalies_total_peak'))}</td>"
            "</tr>"
        )
        for item in (cost_summary.get("accounts", []) or [])[:25]
    )
    if not cost_rows:
        cost_rows = "<tr><td colspan='3'>Tidak ada cost anomaly signifikan pada periode ini</td></tr>"

    metric_instance_hints: dict[str, list[str]] = {}
    for item in report.get("resource_fluctuations", []) or []:
        metric = str(item.get("metric_name", ""))
        if not metric:
            continue
        res_label = str(item.get("resource_name") or item.get("resource_id") or "")
        if not res_label:
            continue
        metric_instance_hints.setdefault(metric, [])
        if res_label not in metric_instance_hints[metric]:
            metric_instance_hints[metric].append(res_label)

    series = report.get("metric_daily_series", []) or []
    chart_cards = "".join(
        _render_metric_line_chart(
            (
                f"{str(item.get('metric_name', '-'))}"
                + (
                    f" (Top instances: {', '.join(metric_instance_hints.get(str(item.get('metric_name', '')), [])[:3])})"
                    if metric_instance_hints.get(str(item.get("metric_name", "")))
                    else ""
                )
            ),
            list(item.get("points", []) or []),
        )
        for item in series[:6]
    )
    if not chart_cards:
        chart_cards = "<div class='card'><p class='meta'>Belum ada data chart harian untuk bulan ini.</p></div>"

    resource_series = report.get("resource_daily_series", []) or []
    resource_chart_cards = "".join(
        _render_metric_line_chart(
            f"{str(item.get('account_display_name', '-'))} / {str(item.get('resource_name', '-'))} ({str(item.get('resource_id', '-'))}) - {str(item.get('metric_name', '-'))}",
            list(item.get("points", []) or []),
        )
        for item in resource_series[:6]
    )
    if not resource_chart_cards:
        resource_chart_cards = "<div class='card'><p class='meta'>Belum ada chart per instance/resource untuk bulan ini.</p></div>"

    return f"""
<!doctype html>
<html>
<head>
  <meta charset='utf-8' />
  <title>Workload Monthly Report {monthly}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #111827; }}
    h1, h2 {{ margin: 0 0 12px 0; }}
    .meta {{ margin-bottom: 18px; color: #4b5563; }}
    .card {{ border: 1px solid #e5e7eb; border-radius: 8px; padding: 14px; margin-bottom: 16px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
    th, td {{ border: 1px solid #e5e7eb; padding: 6px 8px; font-size: 12px; text-align: left; }}
    th {{ background: #f9fafb; }}
    h3 {{ margin: 0 0 8px 0; font-size: 14px; }}
    .charts-grid {{ display: grid; grid-template-columns: repeat(2, minmax(300px, 1fr)); gap: 12px; }}
    .line-chart {{ width: 100%; height: auto; display: block; }}
  </style>
</head>
<body>
  <h1>Workload Monthly Report</h1>
  <p class='meta'>Customer ID: {customer_id} · Month: {monthly}</p>

  <h2>Daily Trend Charts</h2>
  <div class='charts-grid'>
    {chart_cards}
  </div>

  <h2>Resource Trend Charts (by Instance)</h2>
  <div class='charts-grid'>
    {resource_chart_cards}
  </div>

  <div class='card'>
    <h2>Stuck Issues (>= {int(stuck.get("threshold_days", 7) or 7)} hari)</h2>
    <p>
      GuardDuty aktif: {int(stuck.get("guardduty_active", 0) or 0)} (stuck: {int(stuck.get("guardduty_stuck", 0) or 0)}) ·
      CloudWatch aktif: {int(stuck.get("cloudwatch_active", 0) or 0)} (stuck: {int(stuck.get("cloudwatch_stuck", 0) or 0)})
    </p>
    <table>
      <thead><tr><th>Check</th><th>Account</th><th>Issue</th><th>Severity</th><th>Age Days</th></tr></thead>
      <tbody>{stuck_rows}</tbody>
    </table>
  </div>

  <div class='card'>
    <h2>Cost Anomaly Highlights</h2>
    <p>Impacted accounts: {int(cost_summary.get("impacted_accounts", 0) or 0)}</p>
    <table>
      <thead><tr><th>Account</th><th>Peak Anomalies Today</th><th>Peak Anomalies Total</th></tr></thead>
      <tbody>{cost_rows}</tbody>
    </table>
  </div>

  <div class='card'>
    <h2>Metric Fluctuation (Top)</h2>
    <table>
      <thead><tr><th>Metric</th><th>Samples</th><th>Days</th><th>Avg</th><th>Min</th><th>Max</th><th>Daily Avg Range</th></tr></thead>
      <tbody>{metric_rows}</tbody>
    </table>
  </div>

  <div class='card'>
    <h2>Resource Fluctuation (Top)</h2>
    <table>
      <thead><tr><th>Account</th><th>Resource ID</th><th>Resource Name</th><th>Metric</th><th>Samples</th><th>Daily Avg Range</th></tr></thead>
      <tbody>{resource_rows}</tbody>
    </table>
  </div>
</body>
</html>
""".strip()


def _render_monthly_report_csv(report: dict) -> str:
    output = StringIO()
    writer = csv.writer(output)

    stuck = report.get("stuck_summary", {}) or {}
    cost_summary = report.get("cost_summary", {}) or {}

    writer.writerow(["section", "field", "value"])
    writer.writerow(["meta", "customer_id", report.get("customer_id")])
    writer.writerow(["meta", "month", report.get("month")])
    writer.writerow(["stuck", "threshold_days", stuck.get("threshold_days")])
    writer.writerow(["stuck", "guardduty_active", stuck.get("guardduty_active")])
    writer.writerow(["stuck", "guardduty_stuck", stuck.get("guardduty_stuck")])
    writer.writerow(["stuck", "cloudwatch_active", stuck.get("cloudwatch_active")])
    writer.writerow(["stuck", "cloudwatch_stuck", stuck.get("cloudwatch_stuck")])
    writer.writerow(
        ["cost", "impacted_accounts", cost_summary.get("impacted_accounts")]
    )
    writer.writerow([])

    writer.writerow(
        [
            "metric_fluctuations",
            "metric_name",
            "sample_count",
            "days_with_samples",
            "avg_value",
            "min_value",
            "max_value",
            "daily_avg_range",
        ]
    )
    for row in report.get("metric_fluctuations", []) or []:
        writer.writerow(
            [
                "metric_fluctuations",
                row.get("metric_name"),
                row.get("sample_count"),
                row.get("days_with_samples"),
                row.get("avg_value"),
                row.get("min_value"),
                row.get("max_value"),
                row.get("daily_avg_range"),
            ]
        )
    writer.writerow([])

    writer.writerow(
        [
            "resource_fluctuations",
            "account_display_name",
            "resource_id",
            "resource_name",
            "metric_name",
            "sample_count",
            "days_with_samples",
            "avg_value",
            "min_value",
            "max_value",
            "daily_avg_range",
        ]
    )
    for row in report.get("resource_fluctuations", []) or []:
        writer.writerow(
            [
                "resource_fluctuations",
                row.get("account_display_name"),
                row.get("resource_id"),
                row.get("resource_name"),
                row.get("metric_name"),
                row.get("sample_count"),
                row.get("days_with_samples"),
                row.get("avg_value"),
                row.get("min_value"),
                row.get("max_value"),
                row.get("daily_avg_range"),
            ]
        )

    writer.writerow([])
    writer.writerow(
        [
            "stuck_items",
            "check_name",
            "account_display_name",
            "title",
            "severity",
            "age_days",
            "last_seen_at",
        ]
    )
    for row in stuck.get("items", []) or []:
        writer.writerow(
            [
                "stuck_items",
                row.get("check_name"),
                row.get("account_display_name"),
                row.get("title"),
                row.get("severity"),
                row.get("age_days"),
                row.get("last_seen_at"),
            ]
        )

    writer.writerow([])
    writer.writerow(
        [
            "cost_accounts",
            "account_display_name",
            "anomalies_today_peak",
            "anomalies_total_peak",
        ]
    )
    for row in cost_summary.get("accounts", []) or []:
        writer.writerow(
            [
                "cost_accounts",
                row.get("account_display_name"),
                row.get("anomalies_today_peak"),
                row.get("anomalies_total_peak"),
            ]
        )

    return output.getvalue()


@router.get("/timeseries", response_model=MetricTimeseriesResponse)
def get_metric_timeseries(
    check_name: str = Query(...),
    customer_id: str | None = Query(None),
    account_id: str | None = Query(None),
    days: int = Query(14, ge=1, le=90),
    repo=Depends(get_check_repository),
):
    items = repo.get_metric_timeseries(
        check_name=check_name,
        customer_id=customer_id,
        account_id=account_id,
        days=days,
    )
    return {"items": items}


@router.get("/workload-monthly-report", response_model=WorkloadMonthlyReportResponse)
def get_workload_monthly_report(
    customer_id: str = Query(...),
    year: int | None = Query(None, ge=2020, le=2100),
    month: int | None = Query(None, ge=1, le=12),
    target_runs_per_day: int = Query(2, ge=1, le=24),
    stuck_days_threshold: int = Query(7, ge=1, le=90),
    repo=Depends(get_check_repository),
):
    report = repo.get_workload_monthly_report(
        customer_id=customer_id,
        year=year,
        month=month,
        target_runs_per_day=target_runs_per_day,
        stuck_days_threshold=stuck_days_threshold,
    )
    return _public_monthly_report_payload(report)


@router.get("/workload-monthly-report/html")
def get_workload_monthly_report_html(
    customer_id: str = Query(...),
    year: int | None = Query(None, ge=2020, le=2100),
    month: int | None = Query(None, ge=1, le=12),
    target_runs_per_day: int = Query(2, ge=1, le=24),
    stuck_days_threshold: int = Query(7, ge=1, le=90),
    repo=Depends(get_check_repository),
):
    report = repo.get_workload_monthly_report(
        customer_id=customer_id,
        year=year,
        month=month,
        target_runs_per_day=target_runs_per_day,
        stuck_days_threshold=stuck_days_threshold,
    )
    return HTMLResponse(content=_render_monthly_report_html(report))


@router.get("/workload-monthly-report/csv")
def get_workload_monthly_report_csv(
    customer_id: str = Query(...),
    year: int | None = Query(None, ge=2020, le=2100),
    month: int | None = Query(None, ge=1, le=12),
    target_runs_per_day: int = Query(2, ge=1, le=24),
    stuck_days_threshold: int = Query(7, ge=1, le=90),
    repo=Depends(get_check_repository),
):
    report = repo.get_workload_monthly_report(
        customer_id=customer_id,
        year=year,
        month=month,
        target_runs_per_day=target_runs_per_day,
        stuck_days_threshold=stuck_days_threshold,
    )
    month_label = str(report.get("month", "monthly"))
    csv_text = _render_monthly_report_csv(report)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=workload-monthly-{month_label}.csv"
        },
    )


@router.get("", response_model=MetricListResponse)
def list_metrics(
    customer_id: str | None = Query(None),
    check_name: str | None = Query(None),
    metric_name: str | None = Query(None),
    metric_status: str | None = Query(None),
    account_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    repo=Depends(get_check_repository),
):
    samples, total = repo.list_metric_samples(
        customer_id=customer_id,
        check_name=check_name,
        metric_name=metric_name,
        metric_status=metric_status,
        account_id=account_id,
        limit=limit,
        offset=offset,
    )

    items = []
    for sample in samples:
        account = sample.account
        items.append(
            {
                "id": sample.id,
                "check_run_id": sample.check_run_id,
                "customer": {
                    "id": account.customer.id,
                    "display_name": account.customer.display_name,
                },
                "account": {
                    "id": account.id,
                    "profile_name": account.profile_name,
                    "display_name": account.display_name,
                },
                "check_name": sample.check_name,
                "metric_name": sample.metric_name,
                "metric_status": sample.metric_status,
                "value_num": sample.value_num,
                "unit": sample.unit,
                "resource_role": sample.resource_role,
                "resource_id": sample.resource_id,
                "resource_name": sample.resource_name,
                "service_type": sample.service_type,
                "section_name": sample.section_name,
                "created_at": sample.created_at.isoformat(),
            }
        )

    return {"total": total, "items": items}
