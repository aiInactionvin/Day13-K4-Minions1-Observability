from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "dashboard.yaml"
DEFAULT_LOG_PATH = REPO_ROOT / "data" / "logs.jsonl"


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    return None


def load_jsonl(path: Path) -> tuple[list[dict[str, Any]], int]:
    """Read valid JSON objects and count malformed/non-object lines."""
    if not path.exists():
        return [], 0

    records: list[dict[str, Any]] = []
    skipped = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            skipped += 1
            continue
        if not isinstance(payload, dict):
            skipped += 1
            continue
        records.append(payload)
    return records, skipped


def _percentile(values: Iterable[float], percentile: int) -> float:
    """Nearest-rank percentile, matching an operations-oriented P95/P99 view."""
    ordered = sorted(values)
    if not ordered:
        return 0.0
    rank = max(1, math.ceil((percentile / 100) * len(ordered)))
    return float(ordered[min(rank - 1, len(ordered) - 1)])


def _minute(timestamp: datetime) -> str:
    return timestamp.replace(second=0, microsecond=0).isoformat().replace("+00:00", "Z")


def _threshold_status(value: float | None, threshold: dict[str, Any]) -> str:
    if value is None:
        return "no_data"
    target = _number(threshold.get("value"))
    if target is None:
        return "unknown"
    operator = threshold.get("operator")
    if operator == "lte":
        return "healthy" if value <= target else "violated"
    if operator == "gte":
        return "healthy" if value >= target else "violated"
    return "unknown"


def _panel_config(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    panels = config["dashboard"]["panels"]
    return {panel["id"]: panel for panel in panels}


def build_dashboard_snapshot(
    log_path: Path = DEFAULT_LOG_PATH,
    config_path: Path = DEFAULT_CONFIG_PATH,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    dashboard_config = config["dashboard"]
    panel_config = _panel_config(config)
    window_minutes = int(dashboard_config["time_range_minutes"])

    current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    cutoff = current_time - timedelta(minutes=window_minutes)
    all_records, skipped_lines = load_jsonl(log_path)

    timed_records: list[tuple[dict[str, Any], datetime]] = []
    for record in all_records:
        timestamp = _parse_timestamp(record.get("ts"))
        if timestamp is not None and cutoff <= timestamp <= current_time + timedelta(minutes=1):
            timed_records.append((record, timestamp))

    request_records = [(record, ts) for record, ts in timed_records if record.get("event") == "request_received"]
    response_records = [(record, ts) for record, ts in timed_records if record.get("event") == "response_sent"]
    failure_records = [(record, ts) for record, ts in timed_records if record.get("event") == "request_failed"]

    latencies = [value for record, _ in response_records if (value := _number(record.get("latency_ms"))) is not None]
    costs = [value for record, _ in response_records if (value := _number(record.get("cost_usd"))) is not None]
    qualities = [value for record, _ in response_records if (value := _number(record.get("quality_score"))) is not None]
    tokens_in = sum(int(value) for record, _ in response_records if (value := _number(record.get("tokens_in"))) is not None)
    tokens_out = sum(int(value) for record, _ in response_records if (value := _number(record.get("tokens_out"))) is not None)

    traffic_by_minute: defaultdict[str, int] = defaultdict(int)
    cost_by_minute: defaultdict[str, float] = defaultdict(float)
    error_by_minute: defaultdict[str, int] = defaultdict(int)
    for _, timestamp in request_records:
        traffic_by_minute[_minute(timestamp)] += 1
    for record, timestamp in response_records:
        cost_by_minute[_minute(timestamp)] += _number(record.get("cost_usd")) or 0.0
    for _, timestamp in failure_records:
        error_by_minute[_minute(timestamp)] += 1

    minute_keys = sorted(set(traffic_by_minute) | set(cost_by_minute) | set(error_by_minute))
    series = [
        {
            "minute": minute_key,
            "traffic": traffic_by_minute[minute_key],
            "cost_usd": round(cost_by_minute[minute_key], 6),
            "errors": error_by_minute[minute_key],
        }
        for minute_key in minute_keys
    ]

    latency_values = {
        "p50": round(_percentile(latencies, 50), 2),
        "p95": round(_percentile(latencies, 95), 2),
        "p99": round(_percentile(latencies, 99), 2),
    }
    latest_rate = float(series[-1]["traffic"]) if series else None
    error_rate = (len(failure_records) / len(request_records) * 100) if request_records else None
    total_cost = round(sum(costs), 6)
    quality_mean = round(mean(qualities), 4) if qualities else None
    error_breakdown = Counter(str(record.get("error_type") or "UnknownError") for record, _ in failure_records)

    latency_threshold = panel_config["latency"]["threshold"]
    traffic_threshold = panel_config["traffic"]["threshold"]
    error_threshold = panel_config["errors"]["threshold"]
    cost_threshold = panel_config["cost"]["threshold"]
    token_threshold = panel_config["tokens"]["threshold"]
    quality_threshold = panel_config["quality"]["threshold"]

    panels = {
        "latency": {
            "title": panel_config["latency"]["title"],
            "unit": panel_config["latency"]["unit"],
            "values": latency_values,
            "sample_count": len(latencies),
            "threshold": latency_threshold,
            "status": _threshold_status(latency_values["p95"] if latencies else None, latency_threshold),
        },
        "traffic": {
            "title": panel_config["traffic"]["title"],
            "unit": panel_config["traffic"]["unit"],
            "count": len(request_records),
            "rate_per_minute": latest_rate or 0.0,
            "threshold": traffic_threshold,
            "status": _threshold_status(latest_rate, traffic_threshold),
        },
        "errors": {
            "title": panel_config["errors"]["title"],
            "unit": panel_config["errors"]["unit"],
            "error_count": len(failure_records),
            "error_rate_pct": round(error_rate, 2) if error_rate is not None else 0.0,
            "breakdown": dict(sorted(error_breakdown.items())),
            "threshold": error_threshold,
            "status": _threshold_status(error_rate, error_threshold),
        },
        "cost": {
            "title": panel_config["cost"]["title"],
            "unit": panel_config["cost"]["unit"],
            "total": total_cost,
            "threshold": cost_threshold,
            "status": _threshold_status(total_cost if costs else None, cost_threshold),
        },
        "tokens": {
            "title": panel_config["tokens"]["title"],
            "unit": panel_config["tokens"]["unit"],
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "threshold": token_threshold,
            "status": _threshold_status(float(max(tokens_in, tokens_out)) if response_records else None, token_threshold),
        },
        "quality": {
            "title": panel_config["quality"]["title"],
            "unit": panel_config["quality"]["unit"],
            "mean": quality_mean or 0.0,
            "sample_count": len(qualities),
            "threshold": quality_threshold,
            "status": _threshold_status(quality_mean, quality_threshold),
        },
    }

    slow_requests = []
    for record, timestamp in sorted(
        response_records,
        key=lambda item: _number(item[0].get("latency_ms")) or 0.0,
        reverse=True,
    )[:10]:
        slow_requests.append(
            {
                "ts": timestamp.isoformat().replace("+00:00", "Z"),
                "correlation_id": record.get("correlation_id", "MISSING"),
                "session_id": record.get("session_id", ""),
                "feature": record.get("feature", ""),
                "model": record.get("model", ""),
                "latency_ms": _number(record.get("latency_ms")) or 0.0,
                "cost_usd": _number(record.get("cost_usd")) or 0.0,
                "quality_score": _number(record.get("quality_score")),
            }
        )

    return {
        "meta": {
            "title": dashboard_config["title"],
            "generated_at": current_time.isoformat().replace("+00:00", "Z"),
            "time_range_minutes": window_minutes,
            "refresh_seconds": int(dashboard_config["refresh_seconds"]),
            "source": str(log_path),
            "records_in_window": len(timed_records),
            "skipped_lines": skipped_lines,
        },
        "panels": panels,
        "series": series,
        "slow_requests": slow_requests,
    }

