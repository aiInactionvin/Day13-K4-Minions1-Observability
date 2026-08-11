# Script thuyết trình Day 13 Observability

## 0. Mở đầu

Chào thầy/cô và các bạn. Nhóm K4-Minions1 làm bài Day 13 với mục tiêu biến một AI API chạy được nhưng khó quan sát thành một hệ thống có thể phát hiện, giải thích và xử lý sự cố bằng bằng chứng.

Thông điệp chính của nhóm là: health check `200 OK` không đủ cho AI agent. Một agent có thể vẫn trả HTTP 200 nhưng latency tăng, cost tăng, tool chậm, hoặc câu trả lời giảm chất lượng. Vì vậy nhóm dùng observability theo luồng: metrics để thấy triệu chứng, trace để khoanh vùng bước lỗi, và log để chứng minh root cause bằng correlation ID.

## 1. Nhóm đã instrument những gì

Đầu tiên, ở tầng logging, mỗi request đi qua middleware sẽ có `correlation_id` dạng `req-...`. ID này được đưa vào response header và bind vào structured log để các event `request_received`, `response_sent`, hoặc `request_failed` có thể nối lại cùng một request.

Log cũng được enrich với `user_id_hash`, `session_id`, `feature`, `model`, `env`, latency, token, cost và quality score. PII được scrub trước khi render JSON, nên email, số điện thoại, CCCD hoặc credit card test không xuất hiện nguyên văn trong log. Kết quả `validate_logs.py` hiện là 100/100 và không phát hiện PII leak.

Ở tầng tracing, nhóm dùng Langfuse. Trace có metadata prompt version, prompt label, session ID, user hash và correlation ID. Nhóm cũng thêm span riêng `rag_retrieve`, để khi retrieval chậm thì waterfall không chỉ hiện agent chậm chung chung mà chỉ rõ bước retrieval đang chiếm thời gian.

Ở tầng dashboard, nhóm dựng 6 panel đúng contract: latency percentiles, traffic, error rate, cost, tokens và quality proxy. Dashboard còn có investigation queue để lấy những request chậm nhất cùng correlation ID.

## 2. Cách đọc dashboard trước khi vào trace

Khi có incident, nhóm không đọc log thô ngay. Chúng ta nhìn dashboard trước.

Panel đầu tiên là latency percentiles. P50 cho biết request bình thường, P95/P99 cho biết tail latency. Trong challenge, baseline P95 là khoảng `1043ms`, còn challenge P95 tăng lên `3563ms` ở batch export Langfuse mới nhất.

Tiếp theo nhìn error rate. Error rate vẫn là `0%`, nghĩa là hệ thống không crash. Đây là kiểu lỗi nguy hiểm của AI system: user vẫn nhận response, nhưng chậm hơn nhiều.

Sau đó nhìn cost, token và quality. Cost trung bình khoảng `$0.002/request`, quality trung bình khoảng `0.84`, không có spike rõ. Vì vậy giả thuyết ban đầu là không phải model sinh output quá dài, không phải lỗi API, mà là một bước trong pipeline bị chậm.

## 3. Challenge đã chạy như thế nào

Challenge chính thức là:

```text
challenge_id = day13-k4-observability-v1
incident = rag_slow
affected_feature = monitoring
```

Nhóm chạy:

```bash
python scripts/inject_incident.py
python scripts/load_test.py --challenge --concurrency 5
python scripts/inject_incident.py --disable
```

Các request challenge có correlation ID:

```text
req-4543c0a8
req-42bb5092
req-d999af47
req-db359a5e
req-076fe46d
```

Trong log, các request này đều thuộc feature `monitoring`, đều trả HTTP 200, nhưng `response_sent.latency_ms` nằm khoảng `2650ms` đến `3563ms`.

## 4. Cách bắt lỗi qua Langfuse

Sau khi có correlation ID từ dashboard, nhóm mở Langfuse và lọc theo session hoặc trace metadata.

Ví dụ:

```text
session_id = k4-challenge-s05
correlation_id = req-4543c0a8
trace_id = 53636ea160e6259182786f326635fbec
```

Trace URL:

```text
https://us.cloud.langfuse.com/project/cmsocay5s00ilad0d966g488c/traces/53636ea160e6259182786f326635fbec
```

Khi mở waterfall, ta đọc từ span cha xuống span con:

```text
run              ~3.565s
rag_retrieve     2.5s
```

Như vậy phần lớn latency nằm ở `rag_retrieve`. Đây là bằng chứng trực tiếp hơn việc chỉ nhìn tổng latency. Một trace khác:

```text
session_id = k4-challenge-s02
correlation_id = req-d999af47
trace_id = a0aa2d523a3f7ab539b966b0eb8bc51e
run latency = 2.651s
rag_retrieve latency = 2.501s
```

Kết luận từ trace: bottleneck nằm ở retrieval/RAG, không phải LLM generation.

## 5. Nối trace về log bằng correlation ID

Sau khi biết span `rag_retrieve` chậm, nhóm quay lại log để chứng minh request cụ thể.

Ví dụ log line của `req-4543c0a8` có:

```text
event = response_sent
session_id = k4-challenge-s05
feature = monitoring
latency_ms = 3563
error_type = none
quality_score = 0.8
```

Điều này chứng minh ba điểm:

1. Request thật sự là request challenge.
2. Request không fail, vì có `response_sent`.
3. Latency cao khớp với trace waterfall.

Đây là luồng Metrics -> Trace -> Logs:

```text
Dashboard P95 tăng
-> mở trace chậm trong Langfuse
-> thấy rag_retrieve chiếm 2.5s
-> dùng correlation ID lọc log để chứng minh request và response
```

## 6. Root cause

Root cause là incident `rag_slow`. Trong code practice/challenge, khi state này bật, retriever sleep thêm 2.5 giây.

Bằng chứng:

```text
app/mock_rag.py
if STATE["rag_slow"]:
    time.sleep(2.5)
```

Nên đây là một sự cố retrieval latency. Nó không làm error rate tăng, không làm token tăng, nhưng làm trải nghiệm user chậm đi rõ rệt.

## 7. Phương án xử lý

Mitigation ngay:

1. Tắt incident hoặc rollback thay đổi gây chậm:

```bash
python scripts/inject_incident.py --disable
```

2. Nếu đây là production thật, bật cache retrieval hoặc route sang retriever fallback.
3. Nếu nguyên nhân do vector index/filter, rollback index config hoặc rebuild index.

Fix lâu dài:

1. Giữ span riêng `rag_retrieve` trong Langfuse để thấy retrieval latency trực tiếp.
2. Thêm alert symptom-based cho latency P95, ví dụ `latency_p95_ms > 3000ms trong 5 phút`.
3. Trong dashboard, giữ investigation queue hiển thị correlation ID của request chậm nhất.
4. Thêm regression test hoặc synthetic check cho retrieval latency.
5. Nếu retrieval phụ thuộc vector store thật, thêm timeout, retry có backoff, circuit breaker và fallback response.

## 8. Kết luận

Qua challenge này, nhóm chứng minh observability không chỉ là có dashboard đẹp. Observability giúp trả lời được câu hỏi production quan trọng: hệ thống đang có vấn đề gì, request nào bị ảnh hưởng, bước nào là root cause, và sửa thế nào.

Với AI agent, HTTP 200 không đồng nghĩa hệ thống khỏe. Trong challenge này, error rate bằng 0 nhưng P95 tăng mạnh. Nhờ metrics, trace và structured logs có correlation ID, nhóm xác định được nguyên nhân là `rag_retrieve` chậm khoảng 2.5 giây và đưa ra mitigation/fix cụ thể.
