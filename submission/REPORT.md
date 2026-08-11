# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm:
- Repository URL: `https://github.com/aiInactionvin/Day13-K4-Minions1-Observability`
- Commit SHA cuối:
- Thành viên và vai trò:

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: **100/100**
- Tổng số traces: **186** tại thời điểm xác minh ngày 2026-08-11
- Số PII leak còn lại: **0**
- Link/đường dẫn dashboard: chạy `uvicorn dashboard.web:app --port 8501`, mở `http://127.0.0.1:8501`

## 3. Logging và tracing

- Evidence correlation ID: `submission/evidence/c_challenge_log.json` và `submission/evidence/c_challenge_trace.json`
- Evidence PII redaction: `submission/evidence/a_runtime_logs_redacted.jsonl`
- Evidence trace waterfall: trace `56a07306a7bd3b060a06b045b9cb3b14`; dữ liệu đã lọc tại `submission/evidence/c_challenge_trace.json`
- Giải thích một span đáng chú ý: `rag_retrieve` mất **2.504s/3.528s** của trace (khoảng **71%**). Đây là span chiếm phần lớn latency và khớp với incident `rag_slow`.

## 4. Prompt versioning

- Prompt name: `day13-chat`
- Version/label baseline: Version 1 (label: `production` / `baseline`, prompt_version: `1`)
- Version/label candidate: Version 2 (label: `production` / `candidate`, prompt_version: `2`)
- Trace ID của mỗi version:
  - **Baseline (Version 1 Trace ID)**: `13f13e09d108c329fc787e366230749c`
  - **Candidate (Version 2 Trace ID)**: `6dfd3e468054e96b88e80116aa0c92b4`
- Bằng chứng đổi label hoặc rollback: `submission/evidence/prompt_rollback.png`



## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: Đạt 6/6 panel hợp lệ theo contract `config/dashboard.yaml`
- Evidence dashboard: `submission/evidence/c_dashboard_rag_slow.png`
- SLO đã chọn và lý do:
  - **Latency P95 <= 3000ms (SLO 99.5%)**: Đảm bảo trải nghiệm thời gian thực cho người dùng, ngăn ngừa client timeout.
  - **Error Rate <= 2.0% (SLO 99.0%)**: Đảm bảo độ tin cậy và sẵn sàng của dịch vụ API.
  - **Daily Cost <= $2.50 (SLO 100.0%)**: Kiểm soát chi phí gọi FakeLLM/API token theo ngân sách.
  - **Quality Score Average >= 0.75 (SLO 95.0%)**: Đảm bảo chất lượng câu trả lời RAG + AI không bị sụt giảm.
- Alert rules và runbook:
  - Cấu hình Alert Rules: `config/alert_rules.yaml`
  - Hướng dẫn Runbook chi tiết: `docs/alerts.md`


## 6. Điều tra challenge

- Challenge ID: `day13-k4-observability-v1` (K4), incident `rag_slow`
- Triệu chứng từ metrics: P95 latency tăng lên **3528ms**, vượt SLO **3000ms**; error rate vẫn **0%**, cost/tokens/quality không tăng bất thường. Với 5 request concurrent, client latency tăng dần từ **3558ms** tới **14201.4ms**.
- Trace ID liên quan: `56a07306a7bd3b060a06b045b9cb3b14`
- Log line/correlation ID liên quan: `req-6bc65580`, app latency **3528ms**, evidence `submission/evidence/c_challenge_log.json`
- Root cause: incident thêm `time.sleep(2.5)` trong `rag_retrieve`; đây là thao tác blocking nên vừa làm retrieval chậm, vừa tuần tự hóa request khi chạy concurrent trên event loop.
- Fix action: tắt incident và loại bỏ blocking delay; với retrieval thật, dùng I/O bất đồng bộ và timeout có giới hạn.
- Preventive measure: giữ child span `rag_retrieve`, alert tail latency, thêm timeout/fallback và concurrent latency regression test trước release.

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| Hữu Khanh (Role C) | Dashboard 6 panel, load test baseline/incident, điều tra challenge, evidence và report | `2783c18` và commit hoàn thiện Role C | Metrics phát hiện triệu chứng; correlation ID nối logs với trace; child span định vị root cause. |
