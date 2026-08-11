# Script thuyết trình Day 13 Observability

## 0. Mở đầu

Chào thầy/cô và các bạn. Nhóm K4-Minions1 làm bài Day 13 với mục tiêu biến một AI API chạy được nhưng khó quan sát thành một hệ thống có thể phát hiện, giải thích và xử lý sự cố bằng bằng chứng.

Thông điệp chính của nhóm là: health check `200 OK` không đủ cho AI agent. Một agent có thể vẫn trả HTTP 200 nhưng latency tăng, cost tăng, tool chậm, hoặc câu trả lời giảm chất lượng. Vì vậy nhóm dùng observability theo luồng: metrics để thấy triệu chứng, trace để khoanh vùng bước lỗi, và log để chứng minh root cause bằng correlation ID.

## 1. Nhóm đã instrument những gì

Đầu tiên, ở tầng logging, mỗi request đi qua middleware sẽ có `correlation_id` dạng `req-...`. ID này được đưa vào response header và bind vào structured log để các event `request_received`, `response_sent`, hoặc `request_failed` có thể nối lại cùng một request.

Log cũng được enrich với `user_id_hash`, `session_id`, `feature`, `model`, `env`, latency, token, cost và quality score. PII được scrub trước khi render JSON, nên email, số điện thoại, CCCD hoặc credit card test không xuất hiện nguyên văn trong log. Kết quả `validate_logs.py` hiện là 100/100 và không phát hiện PII leak.

Ở tầng tracing, nhóm dùng Langfuse. Trace có metadata prompt version, prompt label, session ID, user hash và correlation ID. Nhóm cũng thêm span riêng `rag_retrieve`, để khi retrieval chậm thì waterfall không chỉ hiện agent chậm chung chung mà chỉ rõ bước retrieval đang chiếm thời gian.

Ở tầng dashboard, nhóm dựng 6 panel đúng contract theo `config/dashboard.yaml` và `dashboard/analytics.py`. Cụ thể thiết kế và công thức tính toán cho từng panel như sau:

1. **Panel 1: Latency Percentiles (P50, P90, P95, P99)**:
   - **Mục đích**: Giám sát độ trễ phản hồi của hệ thống, phân biệt giữa request bình thường và các request bị chậm ở đuôi (tail latency).
   - **Công thức**: Lọc tất cả log `event == "response_sent"`, lấy danh sách `latency_ms` sắp xếp tăng dần:
     $$\text{P50} = \text{percentile}(latency\_ms, 50) \quad (\text{Mức trung bình})$$
     $$\text{P95} = \text{percentile}(latency\_ms, 95) \quad (\text{SLO Threshold: } \le 3000\text{ms})$$
     $$\text{P99} = \text{percentile}(latency\_ms, 99) \quad (\text{Tail latency tối đa})$$

2. **Panel 2: Traffic (Request Volume & RPS)**:
   - **Mục đích**: Đo lưu lượng người dùng truy cập theo thời gian real-time.
   - **Công thức**:
     $$\text{Total Requests} = \text{count}(event == \text{"request\_received"})$$
     $$\text{RPS (Request Per Second)} = \frac{\text{Total Requests}}{\text{Time Window (seconds)}}$$

3. **Panel 3: Error Rate (%)**:
   - **Mục đích**: Theo dõi tỷ lệ sự cố và độ sẵn sàng của ứng dụng.
   - **Công thức**:
     $$\text{Error Rate (\%)} = \frac{\text{count}(event == \text{"request\_failed"} \text{ OR } status\_code \ge 500)}{\text{Total Requests}} \times 100\% \quad (\text{SLO Threshold: } \le 2\%)$$

4. **Panel 4: Daily Cost ($ USD)**:
   - **Mục đích**: Kiểm soát ngân sách API chi trả cho mô hình AI LLM.
   - **Công thức tính từng request**:
     $$\text{cost\_usd} = \left(\frac{tokens\_in}{1,000,000} \times \$3\right) + \left(\frac{tokens\_out}{1,000,000} \times \$15\right)$$
   - **Tổng chi phí**: $\text{Total Cost} = \sum cost\_usd \quad (\text{SLO Threshold: } \le \$2.50/\text{ngày})$

5. **Panel 5: Token Consumption (Input vs Output Tokens)**:
   - **Mục đích**: Giám sát độ dài dữ liệu đầu vào (Prompt + RAG Docs) và đầu ra (Completion Answer).
   - **Công thức**:
     $$\text{Avg Input Tokens} = \text{mean}(tokens\_in), \quad \text{Avg Output Tokens} = \text{mean}(tokens\_out)$$

6. **Panel 6: Quality Proxy Score Distribution**:
   - **Mục đích**: Đánh giá chất lượng câu trả lời AI và độ an toàn dữ liệu.
   - **Công thức**: $\text{Quality Avg} = \text{mean}(quality\_score) \quad (\text{SLO Threshold: } \ge 0.75)$
   - Điểm chất lượng được tính bằng Heuristic: khởi tạo `0.5`, `+0.2` nếu có RAG Docs, `+0.1` nếu độ dài câu trả lời $>40$, `-0.2` nếu bị rò rỉ dữ liệu hoặc dính PII Redaction.

## 2. Cách đọc dashboard trước khi vào trace

Khi có incident, nhóm không đọc log thô ngay. Chúng ta nhìn dashboard trước.

Panel đầu tiên là latency percentiles. P50 cho biết request bình thường, P95/P99 cho biết tail latency. Trong lượt chạy thực tế vừa xong:
- **Baseline Latency P95**: `~155ms` (Hệ thống chạy bình thường, phản hồi nhanh).
- **Challenge Latency P95**: Tăng vọt lên `~2660ms` ngay sau khi kích hoạt kịch bản `rag_slow`.

Tiếp theo nhìn error rate. Error rate vẫn là `0%`, nghĩa là hệ thống không crash. Đây là kiểu lỗi nguy hiểm của AI system: user vẫn nhận response `200 OK`, nhưng chậm hơn gấp hơn 17 lần.

Sau đó nhìn cost, token và quality. Cost trung bình khoảng `$0.0018 - $0.0025/request`, quality trung bình đạt `0.8 - 0.9`, không có spike rõ. Vì vậy giả thuyết ban đầu là không phải model sinh output quá dài, không phải lỗi API 500, mà là một bước trong pipeline bị chậm.

## 3. Thiết lập Kịch bản Challenge chính thức

Kịch bản Challenge được thiết lập và kích hoạt tự động:

```bash
# Bước 1: Kích hoạt sự cố challenge (chạy ngầm mô phỏng nghẽn RAG)
python scripts/inject_incident.py

# Bước 2: Bơm lưu lượng test song song 5 luồng
python scripts/load_test.py --challenge --concurrency 5

# Bước 3: Tắt sự cố sau khi đã ghi nhận bằng chứng
python scripts/inject_incident.py --disable
```

Thông số kịch bản Challenge ghi nhận vừa thực thi:

```text
challenge_id = day13-k4-observability-v1
cohort = K4
incident = rag_slow
affected_feature = monitoring
```

Các request challenge thực tế thu được trong lượt chạy mới nhất:

```text
req-dacf0d26 (session: k4-challenge-s02 | latency: 2660ms)
req-47264123 (session: k4-challenge-s01 | latency: 2659ms)
req-5d08285d (session: k4-challenge-s05 | latency: 2660ms)
req-9f8e77cb (session: k4-challenge-s03 | latency: 2659ms)
req-9c4971ce (session: k4-challenge-s04 | latency: 2660ms)
```

Trong log, các request này đều thuộc feature `monitoring`, đều trả HTTP 200, nhưng `response_sent.latency_ms` nằm khoảng `2659ms` đến `2660ms`.

## 4. Cách đọc Trace và Bắt lỗi qua Langfuse

Khi xảy ra sự cố (chậm hoặc báo lỗi), quy trình đọc Trace và bắt lỗi qua Langfuse được thực hiện theo 4 bước chuẩn SRE:

```text
Dashboard báo Alert (P95 > 3000ms hoặc Error Rate > 2%)
  └──> Lấy correlation_id từ Investigation Queue (vd: req-47264123)
        └──> Mở Langfuse UI ➔ Lọc theo metadata correlation_id hoặc session_id
              └──> Soi Waterfall Trace ➔ Chỉ ra đúng Span thủ phạm (rag_retrieve = 2.5s)
                    └──> Tra ngược log thô data/logs.jsonl để xác nhận root cause
```

Ví dụ chi tiết từ vết Trace vừa đẩy lên Langfuse:

```text
session_id = k4-challenge-s01
correlation_id = req-47264123
feature = monitoring
user_id_hash = f00ba60b3772
model = claude-sonnet-4-5
```

**Kỹ thuật phân tích Waterfall Trace trên Langfuse:**

1. **Nhìn Span Tổng (`run`):** Thời gian xử lý tổng cộng là `~2.659s`.
2. **Soi các Span Con (`rag_retrieve` vs `llm_generate`):**
   - Span **`rag_retrieve`**: Chiếm `2.500s` (Tô màu cam/dài bất thường).
   - Span **`llm_generate`**: Chỉ chiếm `0.159s` (Rất nhanh).
3. **Bắt lỗi khi xảy ra Exception (Tool / API Fail):**
   - Nếu xảy ra lỗi HTTP 500 (ví dụ scenario `tool_fail`), Span bị lỗi trên Langfuse sẽ đổi sang màu **ĐỎ (Status: ERROR)**.
   - Nhấp trực tiếp vào Span màu đỏ để đọc **Exception Stack Trace**, thông điệp lỗi chi tiết và mã `error_type`.

## 5. Nối trace về log bằng correlation ID

Sau khi biết span `rag_retrieve` chậm, nhóm quay lại log để chứng minh request cụ thể.

Ví dụ log line của `req-47264123` có:

```text
event = response_sent
session_id = k4-challenge-s01
feature = monitoring
latency_ms = 2659
error_type = none
quality_score = 0.8
```

Điều này chứng minh ba điểm:

1. Request thật sự là request challenge.
2. Request không fail, vì có `response_sent`.
3. Latency cao (2659ms) khớp chính xác với trace waterfall trên Langfuse UI.


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
