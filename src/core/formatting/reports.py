"""Report formatting exports and reusable report builders."""

from __future__ import annotations

from datetime import datetime
from typing import Any

def build_whatsapp_backup(*args, **kwargs):
    from src.core.runtime.reports import build_whatsapp_backup as _impl
    return _impl(*args, **kwargs)


def build_whatsapp_rds(*args, **kwargs):
    from src.core.runtime.reports import build_whatsapp_rds as _impl
    return _impl(*args, **kwargs)


def build_whatsapp_alarm(*args, **kwargs):
    from src.core.runtime.reports import build_whatsapp_alarm as _impl
    return _impl(*args, **kwargs)


def _fmt_pct(val: Any) -> str:
    if isinstance(val, (int, float)):
        return f"{float(val):.2f}%"
    return "-"


def _time_only(ms: Any) -> str:
    if isinstance(ms, int):
        return datetime.fromtimestamp(ms / 1000).astimezone().strftime("%H:%M:%S %Z")
    return "-"


def huawei_time_range_short(row: dict[str, Any]) -> str:
    start = row.get("rise_start_ms")
    peak = row.get("peak_time_ms")
    if isinstance(start, int) and isinstance(peak, int) and start < peak:
        start_txt = datetime.fromtimestamp(start / 1000).astimezone().strftime("%H:%M:%S")
        peak_txt = datetime.fromtimestamp(peak / 1000).astimezone().strftime("%H:%M:%S %Z")
        return f"{start_txt}–{peak_txt}"
    return _time_only(peak)


def classify_huawei_memory_behavior(row: dict[str, Any], rise_threshold: float) -> str:
    peak = row.get("peak")
    if not isinstance(peak, (int, float)):
        return "NO_DATA"

    peak_v = float(peak)
    if peak_v <= rise_threshold:
        return "NORMAL"

    latest = row.get("latest")
    avg = row.get("avg_12h")
    latest_v = float(latest) if isinstance(latest, (int, float)) else None
    avg_v = float(avg) if isinstance(avg, (int, float)) else None

    if latest_v is not None and avg_v is not None:
        sustained_high = latest_v >= rise_threshold and avg_v >= rise_threshold
        near_peak = (peak_v - latest_v) <= 3.0 and (peak_v - avg_v) <= 5.0
        if sustained_high and near_peak:
            return "HIGH_STABLE"

    if avg_v is not None and avg_v >= rise_threshold and (peak_v - avg_v) <= 5.0:
        return "HIGH_STABLE"
    if latest_v is not None and latest_v >= rise_threshold and (peak_v - latest_v) <= 3.0:
        return "HIGH_STABLE"

    return "SPIKE"


def _report_date_ddmmyyyy(results: dict[str, Any]) -> str:
    date_src = str(((results.get("util_window") or {}).get("to")) or "")
    date_part = date_src.split(" ")[0]
    try:
        return datetime.strptime(date_part, "%Y-%m-%d").strftime("%d.%m.%Y")
    except Exception:
        return datetime.now().strftime("%d.%m.%Y")


def _profile_to_account(profile: str) -> str:
    return profile[:-3] if profile.endswith("-ro") else profile


def build_huawei_utilization_customer_report(
    results: dict[str, Any],
    title: str = "Daily Monitoring Utilisasi ECS Darmahenwa",
) -> str:
    if results.get("status") != "success":
        return f"ERROR: {results.get('error', 'unknown error')}"

    rise_threshold = float(results.get("rise_threshold", 70.0))
    util = results.get("util") or {}
    account = str(results.get("account", results.get("profile", "-")))

    lines: list[str] = []
    lines.append(f"{title} ({account})")
    lines.append(_report_date_ddmmyyyy(results))
    lines.append("")

    cpu_row = util.get("cpu_peak_overall") or {}
    cpu_avg = util.get("cpu_avg_12h")
    cpu_host = cpu_row.get("name", "-")
    cpu_peak = cpu_row.get("peak")

    if isinstance(cpu_peak, (int, float)) and isinstance(cpu_avg, (int, float)):
        lines.append(
            f"Utilisasi CPU tidak melewati ambang {rise_threshold:.0f}%; rata-rata 12 jam sekitar {_fmt_pct(cpu_avg)} "
            f"dengan puncak {_fmt_pct(cpu_peak)} ({cpu_host})."
        )
    else:
        lines.append("Data utilisasi CPU tidak tersedia pada periode ini.")

    mem_row = util.get("mem_peak_overall") or {}
    mem_avg = mem_row.get("avg_12h", util.get("mem_avg_12h"))
    mem_peak = mem_row.get("peak")
    mem_host = mem_row.get("name", "-")

    if not isinstance(mem_peak, (int, float)) or not isinstance(mem_avg, (int, float)):
        lines.append("Data utilisasi memory tidak tersedia pada periode ini.")
    elif float(mem_peak) <= rise_threshold:
        lines.append(
            f"Utilisasi memory tidak melewati ambang {rise_threshold:.0f}%; rata-rata 12 jam sekitar {_fmt_pct(mem_avg)} "
            f"dengan puncak {_fmt_pct(mem_peak)} ({mem_host})."
        )
    else:
        behavior = classify_huawei_memory_behavior(mem_row, rise_threshold)
        if behavior == "HIGH_STABLE":
            lines.append(
                f"Utilisasi memory berada pada level tinggi (>{rise_threshold:.0f}%) dan cenderung stabil; rata-rata 12 jam sekitar "
                f"{_fmt_pct(mem_avg)} dengan puncak {_fmt_pct(mem_peak)} ({mem_host})."
            )
        else:
            lines.append(
                f"Terdapat kenaikan signifikan memory (>{rise_threshold:.0f}%) dengan puncak {_fmt_pct(mem_peak)} pada {mem_host}, "
                f"dengan rentang kenaikan {huawei_time_range_short(mem_row)}."
            )

    spikes: list[str] = []
    stable: list[str] = []
    for row in util.get("top_mem_hot") or []:
        item = f"{row.get('name', '-')} peak {_fmt_pct(row.get('peak'))}"
        behavior = row.get("behavior") or classify_huawei_memory_behavior(row, rise_threshold)
        if behavior == "SPIKE":
            spikes.append(item)
        else:
            stable.append(item)

    lines.append("")
    lines.append("[BLOCK - SPIKE / IDLE TINGGI]")
    if spikes:
        lines.append(f"- SPIKE: {', '.join(spikes)}.")
    if stable:
        lines.append(f"- HIGH-STABLE: {', '.join(stable)}.")
    if not spikes and not stable:
        lines.append("- Tidak ada temuan SPIKE/HIGH-STABLE pada periode ini.")
    lines.append("- IDLE tinggi tidak dijadikan alert utama karena laporan menggunakan metrik usage.")
    return "\n".join(lines)


def build_huawei_legacy_consolidated_report(
    all_results: dict[str, dict[str, Any]],
    errors: list[tuple[str, str]],
    ordered_profiles: list[str],
    title: str = "Daily Monitoring Utilisasi ECS Darmahenwa",
) -> str:
    date_source = None
    for profile in ordered_profiles:
        result = all_results.get(profile) or {}
        util_window = result.get("util_window") if isinstance(result, dict) else None
        if isinstance(util_window, dict) and util_window.get("to"):
            date_source = str(util_window.get("to"))
            break

    if date_source:
        date_part = date_source.split(" ")[0]
        try:
            report_date = datetime.strptime(date_part, "%Y-%m-%d").strftime("%d.%m.%Y")
        except Exception:
            report_date = datetime.now().strftime("%d.%m.%Y")
    else:
        report_date = datetime.now().strftime("%d.%m.%Y")

    errors_by_profile = {profile: message for profile, message in errors}

    lines: list[str] = [title, report_date, ""]
    no_data_accounts: list[str] = []
    display_index = 1

    for profile in ordered_profiles:
        result = all_results.get(profile) or {}
        account = str(result.get("account") or _profile_to_account(profile))

        profile_error = errors_by_profile.get(profile)
        if not profile_error and isinstance(result, dict) and result.get("status") == "error":
            profile_error = str(result.get("error") or "unknown error")

        if profile_error:
            lines.append(f"{display_index}. {account}")
            lines.append(f"   ERROR: {profile_error}")
            lines.append("")
            display_index += 1
            continue

        if not isinstance(result, dict) or result.get("status") != "success":
            no_data_accounts.append(account)
            continue

        rise_threshold = float(result.get("rise_threshold", 70.0))
        util = result.get("util") or {}

        cpu_row = util.get("cpu_peak_overall") or {}
        cpu_avg = util.get("cpu_avg_12h")
        cpu_host = cpu_row.get("name", "-")
        cpu_peak = cpu_row.get("peak")
        cpu_has_data = isinstance(cpu_peak, (int, float)) and isinstance(cpu_avg, (int, float))

        mem_row = util.get("mem_peak_overall") or {}
        mem_avg = mem_row.get("avg_12h", util.get("mem_avg_12h"))
        mem_peak = mem_row.get("peak")
        mem_host = mem_row.get("name", "-")
        mem_has_data = isinstance(mem_peak, (int, float)) and isinstance(mem_avg, (int, float))

        top_mem_hot = util.get("top_mem_hot") or []
        if not cpu_has_data and not mem_has_data and not top_mem_hot:
            no_data_accounts.append(account)
            continue

        lines.append(f"{display_index}. {account}")
        display_index += 1

        if cpu_has_data:
            lines.append(
                f"   Utilisasi CPU tidak melewati ambang {rise_threshold:.0f}%; rata-rata 12 jam sekitar {_fmt_pct(cpu_avg)} "
                f"dengan puncak {_fmt_pct(cpu_peak)} ({cpu_host})."
            )
        else:
            lines.append("   Data utilisasi CPU tidak tersedia pada periode ini.")

        if not mem_has_data:
            lines.append("   Data utilisasi memory tidak tersedia pada periode ini.")
        else:
            if not isinstance(mem_peak, (int, float)):
                lines.append("   Data utilisasi memory tidak tersedia pada periode ini.")
                continue
            mem_peak_value = mem_peak
            if mem_peak_value <= rise_threshold:
                lines.append(
                    f"   Utilisasi memory tidak melewati ambang {rise_threshold:.0f}%; rata-rata 12 jam sekitar {_fmt_pct(mem_avg)} "
                    f"dengan puncak {_fmt_pct(mem_peak)} ({mem_host})."
                )
            else:
                behavior = classify_huawei_memory_behavior(mem_row, rise_threshold)
                if behavior == "HIGH_STABLE":
                    lines.append(
                        f"   Utilisasi memory berada pada level tinggi (>{rise_threshold:.0f}%) dan cenderung stabil; rata-rata 12 jam sekitar "
                        f"{_fmt_pct(mem_avg)} dengan puncak {_fmt_pct(mem_peak)} ({mem_host})."
                    )
                else:
                    lines.append(
                        f"   Terdapat spike sesaat pada memory dengan puncak {_fmt_pct(mem_peak)} ({mem_host}); "
                        "tidak dijadikan alert utama."
                    )

        spikes: list[str] = []
        stable: list[str] = []
        for row in util.get("top_mem_hot") or []:
            if not isinstance(row, dict):
                continue
            item = f"{row.get('name', '-')} peak {_fmt_pct(row.get('peak'))}"
            behavior = row.get("behavior") or classify_huawei_memory_behavior(row, rise_threshold)
            if behavior == "SPIKE":
                spikes.append(item)
            elif behavior == "HIGH_STABLE":
                stable.append(item)

        lines.append("")
        lines.append("   [BLOCK - SPIKE / IDLE TINGGI]")
        if stable:
            lines.append(f"   - HIGH-STABLE: {', '.join(stable)}.")
        if not stable:
            lines.append("   - Tidak ada temuan HIGH-STABLE pada periode ini.")
        lines.append("   - IDLE tinggi tidak dijadikan alert utama karena laporan menggunakan metrik usage.")
        lines.append("")

    if no_data_accounts:
        lines.append("Akun tanpa data utilisasi:")
        for account in no_data_accounts:
            lines.append(f"- {account}")

    return "\n".join(lines).rstrip()


__all__ = [
    "build_whatsapp_backup",
    "build_whatsapp_rds",
    "build_whatsapp_alarm",
    "build_huawei_utilization_customer_report",
    "build_huawei_legacy_consolidated_report",
    "classify_huawei_memory_behavior",
    "huawei_time_range_short",
]
