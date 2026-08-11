# Day 13 — Monitoring, Logging & Observability

> **AICB-P1 · Ngày 13 · VinUniversity 2026** · Giảng viên (VinUni) · 69 slides
> *Biết agent đang chạy thế nào trước khi user phàn nàn*
>
> **Câu hỏi khung:** *"Agent bạn deploy hôm Day 12 chạy ngon. 3 ngày sau: latency tăng gấp đôi, cost tăng 300%, và 1 trên 20 câu trả lời là bịa. Bạn biết những điều này khi nào? — Khi user phàn nàn. Đó là cách tệ nhất, và đắt nhất, để phát hiện vấn đề."*

**Deliverable cuối ngày:** Agent có observability đầy đủ — *bạn biết nó chạy thế nào mà không cần hỏi user.*
- Structured logging pipeline: JSON, correlation ID, input/output đã redact PII
- Tracing: Langfuse (hoặc backend zero-key) connected, ≥ 10 traces
- Dashboard: latency P50/95/99 + TTFT, cost/ngày, error rate, token usage, tool-call success
- ≥ 3 alert rules → Slack (symptom-based); 1 daily cost budget alert; 1 incident note đọc từ trace

---

## 1. Vì sao agent cần observability

Day 12 đã có: agent deployed, public URL, health check, basic auth. **Nhưng chưa trả lời được:** agent đang chậm hay nhanh? tốn bao nhiêu tiền mỗi ngày? bao nhiêu request fail (hoặc trả lời sai)? khi nào cần scale up?

> Health check *"200 OK"* không có nghĩa câu trả lời đúng.

| **Monitoring** | **Observability** |
|---|---|
| Theo dõi các câu hỏi **đã biết trước** | **Thuộc tính** của hệ thống: hỏi câu **mới** mà không cần deploy code |
| Dashboard + alert dựng sẵn | Telemetry đủ giàu (metrics + logs + traces) |
| Trả lời: *"X có hỏng không?"* | Trả lời: *"TẠI SAO X hỏng?"* |
| **"Known-knowns"** | **"Unknown-unknowns"** |

**Observability AI khác gì monitoring phần mềm truyền thống?**
- **Không test bằng so sánh string** — cùng input, output khác nhau mỗi lần. Phải đo **chất lượng**, không chỉ pass/fail
- **App không "crash"** — vẫn trả 200 OK nhưng câu trả lời tệ dần. Không có exception để bắt
- **Cost tính theo token** — một bug loop có thể đốt budget trong vài giờ; CPU/RAM không nói cho bạn biết
- **Failure mode riêng của AI** — hallucinated tool args, vòng lặp vô tận, context overflow, prompt injection

**Cost of not monitoring:** silent failures · gradual degradation (P95 tăng 10ms/tuần → 6 tuần sau chậm gấp đôi) · surprise bills · debugging nightmare (không log, không trace → không reproduce, không fix).

Observability là một **feedback loop**: `Agent System → Observe (metrics) → Analyze (compare) → Act (fix/scale)` → quay lại. Hai chỉ số cốt lõi: **MTTD** (Mean Time To Detect) và **MTTR** (Mean Time To Recover).

---

## 2. 3 Pillars + Pillar thứ 4

| Pillar | Trả lời | Nội dung |
|---|---|---|
| **Metrics** — đo lường | Bao nhiêu? Bao lâu? | Latency, error rate, cost per day |
| **Logs** — ghi chép | Gì xảy ra? | Input, output, errors, timestamps |
| **Traces** — theo dõi | Tại sao? | End-to-end journey, bottleneck, root cause |
| **Eval (thứ 4)** — chất lượng | Câu trả lời **có còn đúng không?** | Đo chất lượng output liên tục trên production |

**Vì sao cần pillar thứ 4:** HTTP 200 khác correctness · latency thấp khác hữu ích · error rate 0% khác không đốt tiền.

**Chọn pillar theo câu hỏi cần trả lời** (đừng thu thập telemetry chỉ vì có thể — mỗi data point đều tốn tiền lưu trữ):

| Câu hỏi | Pillar | Công cụ |
|---|---|---|
| "Error rate có tăng không?" | Metrics | Prometheus, Grafana |
| "Request req-abc đã làm gì?" | Logs | Loki, JSON logs |
| "Chậm ở bước nào trong agent loop?" | Traces | Langfuse, Tempo |
| "Câu trả lời còn đúng không?" | Eval (4th) | LLM-judge, RAGAS |

> **Day 13 vs Day 14:** Day 13 đo chất lượng **liên tục trên production** (online). Day 14 đo chất lượng **có hệ thống bằng benchmark** (offline).

---

## 3. AI-Specific Metrics

**4 nhóm metrics cho AI agent:**

| Performance | Cost | Quality (pillar 4) | Reliability |
|---|---|---|---|
| Latency P50/P95/P99 | Tokens per request (in/out) | Hallucination / faithfulness | Error rate, uptime |
| Time to first token (TTFT) | Cost per request / per task | Task completion rate | Tool-call success rate |
| Throughput (req/s, tokens/s) | Cost per day/user/feature | Thumbs up/down rate | Retry rate, loop rate |
| LLM call duration | Cache hit rate | Guardrail trigger rate | Retrieval recall/empty-result |

**Google SRE 4 Golden Signals** (Latency, Traffic, Errors, Saturation) **+ 2 cho AI agent**: **Cost** ($/request, $/user) và **Quality** (hallucination rate, CSAT, groundedness).

**RED vs USE:** RED (request-centric: Rate, Errors, Duration — góc nhìn user) và USE (resource-centric: Utilization, Saturation, Errors — góc nhìn resource). *Kết hợp:* agent chậm (RED: Duration P95 tăng) → debug bằng USE (LLM rate-limit utilization 95%) → bị throttle → upgrade tier hoặc fallback.

### Latency: percentiles + TTFT
- P50 ≈ 2.5s · P95 ≈ 5s · P99 ≈ 8s+. **Trung bình (average) ẩn long tail — P95 mới là trải nghiệm thật.** Reasoning mode là lớp latency riêng (chậm hơn 5–30×) — tách ra khi đo.
- **TTFT** (Time To First Token): quyết định cảm giác "nhanh". Điển hình 2026: P50 ≈ 0.5–1.0s, P95 ≈ 1.5–2.5s.
- **Vì sao P99 quan trọng:** agent có P99 = 5s, user chat 10 lượt → `P = 1 − 0.99¹⁰ ≈ 9.6%`. 1/10 user gặp lag rất tệ; 1.000 user/ngày → 96 user bức xúc. *"Every 100ms of latency cost 1% of sales"* (Amazon/Google/Meta).
- **Tail latency compounds** trong agentic workflow nhiều bước — 5 bước mỗi bước có P99 riêng → gần như chắc chắn 1 bước chạm tail. **Đo P99 cho cả pipeline**, không chỉ từng call.

### Token & Cost — output đắt hơn input

| Model (2026) | Input $/1M | Output $/1M | Tỉ lệ out:in |
|---|---|---|---|
| Claude Haiku 4.5 | 1 | 5 | 5× |
| Claude Sonnet 4.6 | 3 | 15 | 5× |
| Claude Opus 4.8 | 5 | 25 | 5× |
| OpenAI GPT-5.5 | 5 | 30 | 6× |
| Gemini 3.1 Pro | 2 | 12 | 6× |

> **`cost-per-task` ≠ `cost-per-LLM-call`** — 1 task của agent có thể gọi LLM nhiều lần (plan + tool + synthesize). Đo cost theo **task**, rollup theo ngày/user/feature. Dashboard token phải **tách input vs output**.

### Quality metrics — kim tự tháp 4 tầng

| Tầng | Nội dung | Vai trò |
|---|---|---|
| **L4: Outcome** | Task success, revenue, retention | Ground truth nhưng lag hàng tuần |
| **L3: User Signal** | Thumbs up/down, CSAT, follow-up | Confirm trend |
| **L2: LLM-as-Judge** | Relevance, faithfulness (RAGAS) | Alert |
| **L1: Automated Heuristic** | Format, length, toxicity, PII leak | Rẻ, realtime — nhưng không nói được quality thực |

**Hallucination — phát hiện thế nào?** Không có 1 metric duy nhất → cần combo: check mỗi claim có trong retrieved context không (RAGAS faithfulness, TruLens) · extract entities cross-check DB/API · gọi LLM 3 lần (temp 0.7), mâu thuẫn → nghi ngờ (cost 3× → chỉ sample 1%) · tín hiệu gián tiếp từ user (regenerate/rephrase rate, abandon/escalate rate).
> **Air Canada (2024):** chatbot bịa chính sách bereavement fare. Nếu có **groundedness check** với policy DB → block từ đầu, tránh kiện tụng.

**Tool-call & retrieval:** success/schema-fail rate, timeout rate, loop rate, args hallucination · Recall@k, empty-result rate, chunk relevance, retrieval latency. *Một agent "chạy ok" nhưng tool-call success 60% nghĩa là 40% câu trả lời dựa trên dữ liệu sai hoặc thiếu.*

**Error taxonomy** — track `error_type` trong log để alert fire là biết ngay gọi ai:

| Loại lỗi | Cách handle |
|---|---|
| LLM API 5xx | Retry (exponential backoff), fallback model |
| LLM timeout | Circuit breaker, client timeout < server |
| Tool call failed | Retry, graceful degradation |
| Tool schema invalid | Re-prompt với error feedback |
| Guardrail block | Log + user-friendly message |
| Empty response | Alternate prompt, escalate to human |
| Context overflow | Truncate, summarize history |

**Drift — khi data/model thay đổi âm thầm:** *data drift* (input distribution đổi) · *concept drift* (mapping input→output đổi) · *model drift* (provider update model). Phát hiện bằng PSI (`< 0.1` stable · `0.1–0.25` mild · `> 0.25` significant → cần retrain), KL-divergence, embedding drift.
> 2024: OpenAI silently update GPT-4 → format output đổi → nhiều pipeline breaks âm thầm.

**Metric nào cho ai:** Engineering → latency P95, error rate, tool-call failure · Product → satisfaction, task completion, hallucination rate · Finance/Ops → cost/ngày, tokens/request, cost by model · Leadership → adoption, cost vs value, uptime. **Dashboard cho stakeholder phải nói bằng ngôn ngữ business.**

---

## 4. Structured Logging

Log không cấu trúc = ghi chú tay: khó search, khó aggregate. Structured logging biến log thành **DATA query được** (filter theo field, aggregate, correlate across services).

```json
{
  "ts": "2026-03-18T10:23:45Z", "level": "INFO",
  "correlation_id": "req-abc123", "event": "agent_response",
  "latency_ms": 1250, "input_tokens": 640, "output_tokens": 250,
  "cost_usd": 0.0057, "model": "claude-sonnet-4-6"
}
```

**Log gì cho 1 LLM call:** `correlation_id` · model + version, provider · **prompt template id** (KHÔNG log raw prompt chứa PII) · input/output_tokens, latency_ms, TTFT · tool calls + kết quả (đã sanitize), finish_reason · cost_usd · eval score, error + stack trace.

| ✅ Nên log | ❌ KHÔNG log |
|---|---|
| Input (đã sanitize), output summary | PII (tên, SĐT, CCCD, email) |
| Tool calls + results | Full prompts chứa sensitive data |
| Latency, tokens, cost | API keys, tokens, secrets |
| Errors + stack traces, correlation ID | Raw user data chưa sanitize; quá nhiều DEBUG ở production |

**PII redaction:** regex (email, SĐT, thẻ, CCCD) · NER/entity detection · hashing/tokenization · allowlist chỉ log field đã duyệt. Tool: **Microsoft Presidio** (OSS/MIT, 50+ loại PII — tiếng Việt yếu, cần custom recognizer cho CCCD/SĐT VN).
> **Redact tại điểm phát sinh** (trước khi vào pipeline log/trace), không phải ở cuối. Log PII = vi phạm PDPL (Việt Nam) / GDPR.

**Log levels:** DEBUG (dev only) · INFO (normal flow, milestone) · WARN (degraded nhưng vẫn chạy) · ERROR (failed, cần attention). **Production chạy INFO**; khi debug issue cụ thể, tạm bật DEBUG cho 1 request ID rồi tắt lại.

**Correlation ID** nối mọi log entry của 1 request dù đi qua nhiều service — cũng là mầm của `trace_id`. Dùng `structlog` + `contextvars` để bind tự động (`bind_contextvars(correlation_id=..., user_id=..., feature=...)`) → mọi `log.info` tự động có 3 fields trên.

**Log sampling** — 100k req/ngày × 10 log/req = 1M entries/ngày; Datadog ~$0.10/1k → ~$100/ngày chỉ riêng log:
- **Head** (quyết định ngay đầu trace — rẻ, có thể miss errors) · **Tail** (quyết định sau khi xong — đắt, giữ 100% errors) · **Reservoir** (giữ N mẫu uniform)
- Công thức thực dụng: **100% ERROR + WARN · 10% INFO · 1% DEBUG · 100% request >10s · 100% cost >$1/req**
- Sampling giảm cost 10–100× nhưng mất visibility vào normal pattern. **Giữ 100% errors là non-negotiable.**

**Log aggregation stacks:** ELK (full-text search mạnh, tự host) · Loki (label-based, rẻ, tự host) · Datadog Logs (~$0.10/GB, setup nhanh, đắt ở scale) · CloudWatch (~$0.50/GB, tích hợp IAM) · BigQuery (~$0.02/GB, analytics SQL, long retention).
> **Cho lab:** Langfuse tự là log store cho LLM call (free tier). Dev local: `stdout` JSON + `jq` là đủ. Đừng dựng cluster Elasticsearch cho MVP.

**Audit log tách biệt app log:** app log để debug (retention 30–90 ngày, có thể sample/sửa/xóa, dev team truy cập) — audit log để compliance/forensics (retention 2–7 năm, **không sample, append-only**, truy cập restricted).

---

## 5. Distributed Tracing cho Agent

**Span → Trace:** mỗi hàng ngang là 1 **span**; tất cả spans của 1 request tạo thành 1 **trace**; span con lồng trong span cha. Nhìn trace biết ngay **bottleneck ở đâu**.

```
# Span tree của 1 agent run
invoke_agent ecommerce-agent          2500ms
|- chat claude-sonnet-4-6   (plan)     400ms
|- execute_tool check_stock            600ms  ← chậm!
|- chat claude-sonnet-4-6   (plan)     300ms
`- chat claude-sonnet-4-6   (synthesize) 1200ms
```
> Agent loop = chuỗi LLM ↔ tool. Ở ví dụ trên 2 LLM call chiếm 64% latency ⇒ tối ưu prompt/model trước.

**OpenTelemetry (OTel)** — chuẩn mở, vendor-neutral: instrument code **một lần** bằng OTel → gửi tới bất kỳ backend nào (Langfuse / Tempo / Datadog) mà không sửa code. `AI Service (OTel SDK) → OTel Collector → Backend`.

**Đọc trace = đọc cây span:** bước nào lâu nhất, bước nào lỗi, bước nào lặp.

---

## 6. Production Stack: Prometheus + Grafana

```
AI Service (OTel SDK) → OTel Collector → ┬→ Prometheus (metrics) ┬→ Grafana (dashboards)
                                          ├→ Loki (logs)          ┘
                                          └→ Tempo (traces) ──→ Langfuse (LLM UI)
```
- Instrument 1 lần (OTel) → Collector fan-out 3 backend chuyên biệt; Grafana vẽ tất cả, Langfuse nhận trace LLM song song
- Prometheus: **Counter / Gauge / Histogram** (phân phối → P95/P99); dashboard nên lưu JSON/YAML trong git (**Dashboard-as-Code**), review qua PR
> ⚠️ **Cardinality là kẻ đốt tiền thầm lặng:** label `user_id`/raw prompt → bùng nổ time-series. Coinbase từng nhận hóa đơn Datadog **$65 triệu (2022)** phần lớn vì việc này. Chỉ dùng label thấp-cardinality (`model`, `status`).

---

## 7. Dashboard Design — 3 layers

| Layer | Nội dung | Cho ai |
|---|---|---|
| **Layer 1: Overview** | Health, uptime, key alerts | Leadership |
| **Layer 2: Detail** | Latency, cost, error rate, tokens | Engineering |
| **Layer 3: Drill-down** | Traces, log search, root cause | Debugging |

> Mỗi stakeholder chỉ cần nhìn 1 layer. Leadership cần overview, không cần trace. Engineer cần drill-down, không cần revenue chart.

**5 anti-patterns:** (1) *"Wall of metrics"* — 30 panel, giới hạn 6–8 panel/layer · (2) time range mặc định quá dài (default 1 giờ cho ops) · (3) không có baseline/threshold line — luôn vẽ đường SLO lên chart · (4) metric không có đơn vị/context (*"Cost: 1250"* là gì?) · (5) không auto-refresh (ops cần 15–30s).
> Test: đưa dashboard cho người ngoài team xem 30s → họ nói được *"hệ thống OK"* hay *"có vấn đề ở X"* không? Nếu không, redesign.

---

## 8. Alerting

**Alert rules cho AI agent:**

| Metric | Threshold | Severity | Channel |
|---|---|---|---|
| Latency P95 | > 5 giây | Warning | Slack |
| Error rate | > 5% | Critical | Slack + Email |
| Daily cost | > budget ngày | Critical | Email + SMS |
| Tool-call failure | > 10% | Warning | Slack |
| Eval score | tụt > 10% | Warning | Slack |
| Uptime | < 99% | Critical | PagerDuty |

**Symptom-based (NÊN page)** — alert trên cái **user cảm nhận được**: error rate/latency vượt ngưỡng, "câu trả lời sai tăng vọt". Ít false positive, luôn thật.
**Cause-based (để DEBUG)** — alert trên nguyên nhân **có thể**: "CPU 80%", "cache miss cao". Có thể chưa ảnh hưởng user, nhiều noise. Dùng để chẩn đoán, không phải để gọi người.

**Alert fatigue:** quá nhiều alert không quan trọng → mọi người bắt đầu ignore → alert thật bị lẫn trong noise → team mất tin tưởng hệ thống. *Cách tránh (Google SRE):* chỉ page khi cần **hành động ngay** · mỗi page phải đòi **trí tuệ** (không robotic) · page về vấn đề **mới**, chưa từng thấy · phần còn lại → ticket/dashboard.
> Nếu team ignore alert thường xuyên, hệ thống alerting đang **tệ hơn không có**.

**Alert anatomy — template cho mỗi alert:** title rõ (`[P1] Agent P95 latency > 5s cho feature=summary`) · severity (P1 page ngay / P2 giờ hành chính / P3 ticket) · impact (*"5% user đang bị chậm > 5s"*) · current value vs threshold · dashboard link (pre-filtered) + trace link (top 10 chậm nhất) · **runbook link** + on-call owner.
> Alert không có runbook = alert không thể xử lý lúc 3 giờ sáng. Viết runbook là một phần của việc "tạo alert", không phải nice-to-have.

**On-call:** SEV1 (down/critical) → page ngay · SEV2 (degraded) → Slack, giờ làm · SEV3 (minor) → ticket · escalation primary → secondary → lead. Bối cảnh VN: on-call theo UTC+7, tránh deploy lớn dịp Tết, nghĩa vụ báo cáo sự cố dữ liệu **72 giờ** theo PDPL.

---

## 9. Debug 1 incident bằng trace

**Tình huống:** user báo agent phản hồi rất chậm từ 9h sáng, không có deploy nào rõ ràng.
- ❌ Sai lầm thường gặp: lao vào đọc log thô của hàng nghìn request
- ✅ Đúng: **metric (khoanh vùng) → log (lọc theo correlation_id) → trace (tìm bước chậm)**

| Bước | Hành động | Kết quả |
|---|---|---|
| **1–2. Metric → Log** | Dashboard: P95 nhảy 2.5s → 5s lúc 9h; token/request **không đổi**, error rate bình thường ⇒ không phải LLM, không phải lỗi — là một bước nào đó chậm đi. Lọc log `latency_ms > 4000` sau 9h → lấy vài `correlation_id` | Khoanh vùng từ "cả hệ thống" → "request này" |
| **3. Mở trace** | Span tree cho thấy `execute_tool rag_retrieve` = 2800ms (trước 600ms) ⇐ **ROOT CAUSE**. LLM vẫn bình thường, rag_retrieve chậm 4.6× → điều tra vector store | Không có trace: đoán mò. Có trace: thấy thủ phạm trong 30 giây |
| **4. Root cause + Fix + Postmortem** | Một index filter của vector store bị bỏ trong deploy hạ tầng 8h45 → mỗi truy vấn quét toàn bộ. Postmortem: timeline · tác động (MTTD/MTTR) · root cause · cái gì đã giúp phát hiện · action items. **Trách hệ thống, không trách người** | Quy trình dùng lại cho mọi incident |

> Mỗi pillar thu hẹp không gian tìm kiếm cho pillar sau: *"cả hệ thống"* → *"request này"* → *"span này"*.

**Bài học từ sự cố thật (2024–2025):**
- **Replit AI agent (7/2025)** — agent xoá DB production dù đang "code freeze", mất dữ liệu 1.206 lãnh đạo + 1.196 công ty. Tệ hơn: agent **bịa** 4.000 user giả và nói rollback bất khả thi (thực ra rollback được). ⇒ Least-privilege + tách dev/prod; tin telemetry/backup độc lập, KHÔNG tin agent tự thuật.
- **Air Canada (Moffatt v. Air Canada, 2024)** — chatbot bịa chính sách vé tang lễ → toà buộc hãng bồi thường CA$650; lập luận "chatbot là thực thể riêng" bị bác. ⇒ Câu trả lời sai = trách nhiệm pháp lý.
- **Klarna** — dồn AI thay 700 agent rồi quay xe thuê lại người vì chất lượng. ⇒ Tỉ lệ "AI xử lý X%" (mean) che giấu variance ở tail — theo dõi phân phối, không chỉ trung bình.

---

## 10. Human Feedback & Online Eval

| Offline Eval (Day 14) | Online Eval (Day 13) |
|---|---|
| Test set cố định, expected answers | Traffic thật, không có ground truth |
| Chạy trước khi ship (CI gate) | Chạy liên tục trên production |
| Bắt regression | Bắt suy thoái + drift |

**Thu human feedback:** explicit (thumbs up/down, rating sao) rõ ràng nhưng tỉ lệ phản hồi thấp; implicit (regenerate, copy, rời đi, hỏi lại, escalate-to-human) nhiều tín hiệu, cần diễn giải.
> **Implicit signal thường nhiều và trung thực hơn explicit rating.** Log cả hai, gắn vào trace.

**Eval-as-Metric loop:** `Sample 1% production → LLM-judge / RAGAS → Gauge metric → Alert nếu tụt`. Chất lượng trở thành metric như latency. LLM-judge cũng tốn tiền → sample thay vì chấm 100%.

**Feedback → Dataset → Cải thiện:** câu trả lời tệ (thumbs-down / judge thấp) → gom thành dataset → thành test case cho Day 14 → sửa prompt/model → đo lại.
> ⚠️ **Judge drift:** LLM-judge cũng thay đổi theo thời gian/phiên bản. Theo dõi **phân phối** điểm (không chỉ mean); định kỳ kiểm bằng gold set người chấm.

**Vòng lặp trưởng thành:** observability → eval → cải thiện → observability.

---

## 11. Privacy & Compliance khi logging

**Vì sao AI logging rủi ro PII cao:** user gõ **tự do** vào prompt (tên, SĐT, CCCD, bệnh án, thông tin tài chính) · full tracing capture **cả prompt lẫn output** → kho PII ngoài ý muốn · trace/log thường gửi sang **SaaS nước ngoài** (Datadog, LangSmith) = chuyển dữ liệu xuyên biên giới.

> Trong OTel GenAI semconv, `gen_ai.tool.call.arguments` và nội dung prompt/completion là **opt-in** đúng vì lý do PII — mặc định KHÔNG capture nội dung nhạy cảm.

**Kỹ thuật:** redact/mask tại điểm phát sinh · allowlist field được log · log **template id**, không log raw prompt · hash định danh thay vì lưu gốc.

**Retention / Access / Audit:** đặt TTL theo loại data (trace chi tiết 7–30 ngày; metric tổng hợp dài) · RBAC, chỉ cấp khi cần · ghi lại ai truy cập telemetry, hỗ trợ quyền xoá/truy cập của user.
> **PDPL Việt Nam** (Luật 91/2025, hiệu lực 1/1/2026): báo cáo vi phạm dữ liệu trong **72 giờ**; đánh giá tác động (TIA) khi chuyển dữ liệu qua biên giới (vd. gửi log chứa PII sang SaaS nước ngoài).

---

## 12. Checklist, Lab & Tổng kết

### Monitoring Checklist
- **Logging:** structured JSON, correlation ID · PII redacted, log levels đúng
- **Metrics:** latency P50/95/99 + TTFT · token in/out + cost · tool-call success
- **Tracing:** trace per request (span tree) · OTel `gen_ai.*` attributes
- **Alerting:** ≥ 3 alert actionable · symptom-based paging
- **Cost & Privacy:** daily budget alert · cache hit rate · retention + cross-border check

### LAB #13 (~2 giờ)
**Mục tiêu:** gắn observability đầy đủ vào agent (từ Day 12) — structured logging (correlation ID + PII redaction), AI metrics (token/cost/latency P95 + TTFT/tool-call success), distributed tracing (span tree kiểu OTel `gen_ai.*`) gửi tới backend (Langfuse hoặc backend zero-key offline), dashboard + ≥ 3 alert rule.

**Artifact cần nộp:**

| Logging & Tracing | Dashboard & Alert |
|---|---|
| Structured JSON logs + correlation ID | Dashboard: latency, cost, errors, tool-success |
| Input/output đã redact PII | ≥ 3 alert rule (symptom-based) |
| Trace (≥ 10): span tree đọc được | Screenshot dashboard có data |
| Cost & token per request | 1 incident note (metric → log → trace) |

> Không cần enterprise monitoring. Cần chứng minh bạn **biết agent đang chạy thế nào** mà không phải hỏi user.

**Observathon (capstone):** một agent e-commerce hộp đen, im lặng, đầy bug — tự gắn observability để bắt bug rồi sửa. Nộp 3 thứ (findings + bằng chứng · config đã sửa · wrapper retry/cache/route/guardrail); điểm = correctness + LLM-eval quality, latency/cost/error/drift ↓, thưởng theo chẩn đoán. Đội ~4h: public test (giờ 2, leaderboard) → private (3.5h, held-out + 1 bug ẩn).

### 7 Anti-patterns từ industry
1. **"We'll add monitoring later"** — later = never. Add ngay từ MVP *(phổ biến và tai hại nhất)*
2. **Log full prompts + responses** — vi phạm GDPR/PDPL, storage bill nổ. Sanitize + sample
3. **Alert trên mọi metric "quan trọng"** — 50 alert → alert fatigue → ignore
4. **Không có runbook** — alert fire 3h sáng, engineer trẻ lost, escalate lên senior
5. **Monitoring dev ≠ prod config** — prod có issue không reproduce được
6. **Chỉ đo performance, quên cost** — đến cuối tháng mới biết đốt tiền
7. **Trust vendor telemetry mặc định** — framework default có thể log sensitive data. Đọc docs trước khi deploy

> Monitoring không phải feature phụ — là phần **core** của production system, ngang với authentication.

---

## Key Takeaways

1. **4 pillars.** Metrics + logs + traces + eval (còn đúng không). Chỉ logs là không đủ; AI cần pillar thứ 4.
2. **AI-specific metrics.** Token & cost (output đắt 5–6× input), P95 + TTFT, tool-call success. **"HTTP 200" khác "trả lời đúng".**
3. **Logging + tracing.** JSON + correlation ID → `trace_id`; span tree tìm bottleneck; chuẩn OTel; redact PII.
4. **Alert + cost + online eval.** Page theo symptom, không theo cause. Đo cost như metric hạng nhất. Sample → judge → gauge → alert; debug incident: metric → log → trace.

> *Monitoring tốt nghĩa là bạn biết agent có vấn đề trước khi user phàn nàn.*

---

## Tiếp theo — Day 14: AI Evaluation & Benchmarking

*"Day 13 đo 'chất lượng có còn đúng không' trên production. Day 14: đo 'tốt đến đâu' một cách có hệ thống — sếp hỏi agent hơn ChatGPT bao nhiêu, bạn trả lời bằng benchmark."*

**Bài tập về nhà:** chuẩn bị 10 câu hỏi mẫu + expected answer cho agent của bạn · đọc trước tài liệu RAGAS (20 phút) · suy nghĩ: từ online eval hôm nay, quality metric nào quan trọng nhất cho use case của bạn?

**Tài liệu tham khảo:** OpenTelemetry GenAI Semantic Conventions · Langfuse (OSS/MIT, SDK Python v4, OTel-based) / LangSmith · Google SRE Book & SRE Workbook · Prometheus & Grafana · Microsoft Presidio · Vietnam PDPL (Luật 91/2025) + model pricing docs.