# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: high_latency_p95
- Severity: P1 (Critical)
- SLI/SLO liên quan: Latency P95 (Mục tiêu <= 3000ms, SLO 99.5%)
- Điều kiện và thời gian duy trì: `latency_p95_ms > 3000ms` duy trì trong 5 phút
- Ảnh hưởng tới người dùng: Người dùng trải nghiệm thời gian phản hồi chậm, có thể gặp timeout ở client
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra Dashboard panel "Latency P95" và "Retrieval vs LLM latency" trong `data/logs.jsonl`.
  2. Mở Langfuse UI Traces để tìm các span có duration cao bất thường (RAG retrieval hay LLM generation).
  3. Lọc log trong `data/logs.jsonl` theo correlation ID của các request bị chậm để tìm nguyên nhân nút thắt (bottleneck).
- Mitigation tạm thời: Bật cache RAG hoặc chuyển đổi model fallback nếu LLM bị chậm.
- Owner: sre-team

## Alert 2

- Tên: high_error_rate
- Severity: P1 (Critical)
- SLI/SLO liên quan: Error rate (Mục tiêu <= 2.0%, SLO 99.0%)
- Điều kiện và thời gian duy trì: `error_rate_pct > 2%` duy trì trong 5 phút
- Ảnh hưởng tới người dùng: Người dùng nhận phản hồi lỗi HTTP 500 hoặc rớt kết nối dịch vụ
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra Dashboard panel "Error Rate" và "HTTP Status Code breakdown".
  2. Lọc các dòng log trong `data/logs.jsonl` có `level=error` hoặc `status_code >= 500`.
  3. Mở Langfuse UI Traces tìm error span / exception stack trace tương ứng.
- Mitigation tạm thời: Rollback prompt version vừa deploy gần nhất hoặc khởi động lại instance API.
- Owner: sre-team

## Alert 3

- Tên: low_quality_score
- Severity: P2 (Warning)
- SLI/SLO liên quan: Quality score (Mục tiêu >= 0.75, SLO 95.0%)
- Điều kiện và thời gian duy trì: `quality_score_avg < 0.75` duy trì trong 15 phút
- Ảnh hưởng tới người dùng: Chất lượng câu trả lời AI giảm sút, thông tin thiếu chính xác hoặc rò rỉ redaction
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra Dashboard panel "Quality Score Distribution".
  2. Đọc Langfuse Traces kiểm tra xem prompt version mới có làm giảm điểm chất lượng không.
  3. Đọc log kiểm tra xem có PII redaction bị rò rỉ làm tụt điểm chất lượng.
- Mitigation tạm thời: Rollback `production` label trên Langfuse UI về prompt version cũ đã kiểm chứng.
- Owner: ai-quality-team

