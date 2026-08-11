# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm:
- Repository URL:
- Commit SHA cuối:
- Thành viên và vai trò:

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`:
- Tổng số traces:
- Số PII leak còn lại:
- Link/đường dẫn dashboard:

## 3. Logging và tracing

- Evidence correlation ID:
- Evidence PII redaction:
- Evidence trace waterfall:
- Giải thích một span đáng chú ý:

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
- Evidence dashboard: `submission/evidence/dashboard.png`
- SLO đã chọn và lý do:
  - **Latency P95 <= 3000ms (SLO 99.5%)**: Đảm bảo trải nghiệm thời gian thực cho người dùng, ngăn ngừa client timeout.
  - **Error Rate <= 2.0% (SLO 99.0%)**: Đảm bảo độ tin cậy và sẵn sàng của dịch vụ API.
  - **Daily Cost <= $2.50 (SLO 100.0%)**: Kiểm soát chi phí gọi FakeLLM/API token theo ngân sách.
  - **Quality Score Average >= 0.75 (SLO 95.0%)**: Đảm bảo chất lượng câu trả lời RAG + AI không bị sụt giảm.
- Alert rules và runbook:
  - Cấu hình Alert Rules: `config/alert_rules.yaml`
  - Hướng dẫn Runbook chi tiết: `docs/alerts.md`


## 6. Điều tra challenge

- Challenge ID:
- Triệu chứng từ metrics:
- Trace ID liên quan:
- Log line/correlation ID liên quan:
- Root cause:
- Fix action:
- Preventive measure:

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| | | | |
