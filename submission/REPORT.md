# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm: K4-Minions1
- Repository URL: https://github.com/aiInactionvin/Day13-K4-Minions1-Observability.git
- Commit SHA cuối: điền bằng `git rev-parse HEAD` sau commit nộp cuối.
- Thành viên và vai trò:
  - Hoàng Duy Hưng / Tech Lead Backend: logging middleware, correlation ID, enrichment logs, PII redaction.
  - Sẻ Thế Hưng / SRE Alerts: Langfuse prompt versioning, SLO, alert rules, runbook.
  - Đặng Hữu Khanh / QA Chief Investigator: dashboard runtime, load test, challenge investigation, report evidence.

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: 100/100 (`submission/evidence/a_validate_logs_result.txt`)
- Tổng số traces: có prompt trace evidence cho baseline/candidate và 5 traces challenge thật đã export lên Langfuse (`submission/evidence/langfuse_challenge_traces.txt`).
- Số PII leak còn lại: 0 theo `validate_logs.py`
- Link/đường dẫn dashboard:
  - Runtime local: `uvicorn dashboard.web:app --reload --port 8501`
  - API dashboard: `http://127.0.0.1:8501/api/dashboard`
  - Evidence dashboard: `submission/evidence/c_dashboard_rag_slow.png`
  - Snapshot challenge: `submission/evidence/challenge_dashboard_snapshot.json`

## 3. Logging và tracing

- Evidence correlation ID:
  - `submission/evidence/a_runtime_logs_redacted.jsonl`
  - `submission/evidence/challenge_log_lines.jsonl`
  - Ví dụ challenge: `req-4543c0a8`, `req-42bb5092`, `req-d999af47`, `req-db359a5e`, `req-076fe46d`
- Evidence PII redaction:
  - `submission/evidence/a_runtime_logs_redacted.jsonl`
  - `validate_logs.py` báo `Potential PII leaks detected: 0`
- Evidence trace waterfall:
  - Prompt/Langfuse evidence: `submission/evidence/prompt_versions.png`, `submission/evidence/prompt_rollback.png`
  - Challenge Langfuse traces: `submission/evidence/langfuse_challenge_traces.txt`, `submission/evidence/langfuse_challenge_traces.json`
- Giải thích một span đáng chú ý:
  - Trace `53636ea160e6259182786f326635fbec` cho session `k4-challenge-s05` có `run` latency 3.565s và span con `rag_retrieve` latency 2.5s.
  - Trace `a0aa2d523a3f7ab539b966b0eb8bc51e` cho session `k4-challenge-s02` có `run` latency 2.651s và span con `rag_retrieve` latency 2.501s.
  - Đây là bằng chứng waterfall cho thấy bottleneck nằm ở retrieval, không phải error hay token/cost spike.

## 4. Prompt versioning

- Prompt name: `day13-chat`
- Version/label baseline: Version 1 (label: `production` / `baseline`, prompt_version: `1`)
- Version/label candidate: Version 2 (label: `production` / `candidate`, prompt_version: `2`)
- Trace ID của mỗi version:
  - Baseline (Version 1 Trace ID): `13f13e09d108c329fc787e366230749c`
  - Candidate (Version 2 Trace ID): `6dfd3e468054e96b88e80116aa0c92b4`
- Bằng chứng đổi label hoặc rollback: `submission/evidence/prompt_rollback.png`

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: Đạt 6/6 panel hợp lệ theo contract `config/dashboard.yaml` (`submission/evidence/c_validate_dashboard.txt`)
- Evidence dashboard:
  - `submission/evidence/c_dashboard_rag_slow.png`
  - `submission/evidence/c_dashboard_baseline.json`
  - `submission/evidence/c_dashboard_rag_slow.json`
  - `submission/evidence/challenge_dashboard_snapshot.json`
- SLO đã chọn và lý do:
  - Latency P95 <= 3000ms (SLO 99.5%): giữ trải nghiệm chat/API trong ngưỡng phản hồi chấp nhận được.
  - Error rate <= 2.0% (SLO 99.0%): bảo vệ reliability của API.
  - Daily cost <= $2.50 (SLO 100.0%): kiểm soát burn rate token/model.
  - Quality score average >= 0.75 (SLO 95.0%): phát hiện suy giảm chất lượng câu trả lời.
- Alert rules và runbook:
  - Cấu hình Alert Rules: `config/alert_rules.yaml`
  - Hướng dẫn Runbook chi tiết: `docs/alerts.md`

## 6. Điều tra challenge

- Challenge ID: `day13-k4-observability-v1`
- Incident chính thức: `rag_slow`
- Affected feature: `monitoring`
- Triệu chứng từ metrics:
  - Baseline P95: 1043ms
  - Challenge P95: 3563ms
  - Error rate: 0%
  - Average cost: khoảng $0.002/request
  - Average quality: 0.84
  - Kết luận: latency tăng rõ trong khi error, cost, token và quality không tăng tương ứng.
- Trace ID liên quan:
  - `53636ea160e6259182786f326635fbec` - session `k4-challenge-s05`, correlation ID `req-4543c0a8`, `rag_retrieve` span 2.5s
  - `f1d5572b7608f60cb3af281fc705d43d` - session `k4-challenge-s01`, correlation ID `req-42bb5092`, `rag_retrieve` span 2.5s
  - `a0aa2d523a3f7ab539b966b0eb8bc51e` - session `k4-challenge-s02`, correlation ID `req-d999af47`, `rag_retrieve` span 2.501s
  - `75bb62dbd3ff6eaf85136f348d35a957` - session `k4-challenge-s03`, correlation ID `req-db359a5e`, `rag_retrieve` span 2.5s
  - `37f8c33b5ceed690fd5c774730a29e89` - session `k4-challenge-s04`, correlation ID `req-076fe46d`, `rag_retrieve` span 2.5s
- Log line/correlation ID liên quan:
  - `req-4543c0a8` - `latency_ms=3563`, session `k4-challenge-s05`
  - `req-42bb5092` - `latency_ms=2650`, session `k4-challenge-s01`
  - `req-d999af47` - `latency_ms=2650`, session `k4-challenge-s02`
  - `req-db359a5e` - `latency_ms=2650`, session `k4-challenge-s03`
  - `req-076fe46d` - `latency_ms=2650`, session `k4-challenge-s04`
  - Evidence: `submission/evidence/challenge_log_lines.jsonl`
- Root cause:
  - Incident `rag_slow` làm bước RAG/retrieval bị delay thêm khoảng 2.5s.
  - Bằng chứng code: `app/mock_rag.py` sleep `2.5s` khi `STATE["rag_slow"]` bật.
  - Bằng chứng metrics/log: mọi request challenge feature `monitoring` đều có `response_sent.latency_ms` khoảng 2650ms, không có `request_failed`.
- Fix action:
  - Tắt incident: `python scripts/inject_incident.py --disable`
  - Nếu là production thật: rollback thay đổi vector-store/index gần nhất, bật cache retrieval tạm thời, hoặc route sang retriever fallback.
- Preventive measure:
  - Thêm span riêng cho `rag_retrieve` để Langfuse waterfall chỉ rõ retrieval latency thay vì chỉ thấy agent duration tổng.
  - Alert symptom-based cho latency P95 và dashboard investigation queue theo correlation ID.
  - Thêm runbook: Metrics P95 -> chọn slow correlation ID -> mở Langfuse trace -> lọc log cùng `correlation_id`.

## 7. Cách bắt challenge qua Langfuse và xử lý

1. Bật Langfuse bằng `.env` của project được Lab Coach cấp: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`, `LANGFUSE_PROMPT_NAME=day13-chat`, `LANGFUSE_PROMPT_LABEL=production`.
2. Chạy API: `uvicorn app.main:app --reload --env-file .env`.
3. Bật challenge: `python scripts/inject_incident.py`.
4. Chạy input chính thức: `python scripts/load_test.py --challenge --concurrency 5`.
5. Trên dashboard, lấy slow correlation ID, ví dụ `req-4543c0a8`.
6. Trong Langfuse, lọc trace theo metadata/session:
   - `session_id=k4-challenge-s02`
   - tag/metadata feature `monitoring`
   - prompt metadata `prompt_name=day13-chat`, `prompt_label=production`
7. Mở trace waterfall:
   - Nếu span retrieval/tool hiện riêng và duration ~2.5s, kết luận root cause là retrieval.
   - Nếu chỉ có agent/generation span, dùng trace để lấy prompt/session và dùng `correlation_id` trong log để chứng minh latency server.
8. Xử lý:
   - Mitigation ngay: disable incident/rollback infra retriever/cache hoặc fallback retriever.
   - Fix lâu dài: instrument span `rag_retrieve`, add alert P95, add dashboard slow-request queue, thêm regression test cho retrieval latency.

## 8. Đóng góp cá nhân

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| Role A | Middleware correlation ID, log enrichment, PII redaction | `71de070`, `4847ed0` | Correlation ID cần được bind sớm và scrub PII trước khi render JSON log. |
| Role B | Langfuse prompt evidence, SLO, alert rules, runbook | `b5fe014`, merge `6e77c67` | Alert tốt phải symptom-based, có owner và runbook xử lý. |
| Role C | Dashboard runtime, challenge run, metric-log evidence, report | `2783c18` + report update | Debug incident hiệu quả theo luồng metrics -> trace/log -> root cause. |
