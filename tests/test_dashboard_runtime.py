from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from dashboard.analytics import build_dashboard_snapshot, load_jsonl


REPO_ROOT = Path(__file__).resolve().parents[1]


def _record(ts: str, event: str, **fields) -> dict:
    return {
        "ts": ts,
        "level": "info",
        "service": "api",
        "event": event,
        "correlation_id": fields.pop("correlation_id", "req-test000"),
        **fields,
    }


def test_dashboard_snapshot_matches_the_six_panel_contract(tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    records = [
        _record("2026-08-11T12:00:00Z", "request_received", correlation_id="req-00000001"),
        _record(
            "2026-08-11T12:00:01Z",
            "response_sent",
            correlation_id="req-00000001",
            feature="qa",
            model="fake-llm",
            latency_ms=1000,
            tokens_in=100,
            tokens_out=50,
            cost_usd=0.1,
            quality_score=0.8,
        ),
        _record("2026-08-11T12:01:00Z", "request_received", correlation_id="req-00000002"),
        _record(
            "2026-08-11T12:01:01Z",
            "response_sent",
            correlation_id="req-00000002",
            feature="qa",
            model="fake-llm",
            latency_ms=4000,
            tokens_in=200,
            tokens_out=100,
            cost_usd=0.2,
            quality_score=0.6,
        ),
        _record("2026-08-11T12:02:00Z", "request_received", correlation_id="req-00000003"),
        _record(
            "2026-08-11T12:02:01Z",
            "request_failed",
            correlation_id="req-00000003",
            error_type="TimeoutError",
        ),
        _record("2026-08-11T10:00:00Z", "request_received", correlation_id="req-old0000"),
    ]
    log_path.write_text(
        "\n".join(json.dumps(record) for record in records) + "\nnot-json\n",
        encoding="utf-8",
    )

    snapshot = build_dashboard_snapshot(
        log_path,
        REPO_ROOT / "config" / "dashboard.yaml",
        now=datetime(2026, 8, 11, 12, 3, tzinfo=timezone.utc),
    )

    assert set(snapshot["panels"]) == {
        "latency",
        "traffic",
        "errors",
        "cost",
        "tokens",
        "quality",
    }
    assert snapshot["meta"]["records_in_window"] == 6
    assert snapshot["meta"]["skipped_lines"] == 1
    assert snapshot["panels"]["latency"]["values"] == {
        "p50": 1000.0,
        "p95": 4000.0,
        "p99": 4000.0,
    }
    assert snapshot["panels"]["latency"]["status"] == "violated"
    assert snapshot["panels"]["traffic"]["count"] == 3
    assert snapshot["panels"]["errors"]["error_rate_pct"] == 33.33
    assert snapshot["panels"]["errors"]["breakdown"] == {"TimeoutError": 1}
    assert snapshot["panels"]["cost"]["total"] == 0.3
    assert snapshot["panels"]["tokens"]["tokens_in"] == 300
    assert snapshot["panels"]["tokens"]["tokens_out"] == 150
    assert snapshot["panels"]["quality"]["mean"] == 0.7
    assert snapshot["slow_requests"][0]["correlation_id"] == "req-00000002"


def test_load_jsonl_handles_a_missing_file(tmp_path: Path) -> None:
    records, skipped = load_jsonl(tmp_path / "missing.jsonl")

    assert records == []
    assert skipped == 0

