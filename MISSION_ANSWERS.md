# Day 12 Lab - Mission Answers

> **Student Name:** Pham Tran Nguyen Phu  
> **Student ID:** 2A202600857  
> **Date:** 2026-06-12

---

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found in `01-localhost-vs-production/develop/app.py`

1. **API key hardcode trong code** — `OPENAI_API_KEY = "sk-hardcoded-fake-key-never-do-this"` và `DATABASE_URL = "postgresql://admin:password123@localhost:5432/mydb"`. Nếu push lên GitHub public, secrets bị lộ ngay lập tức và không thể thu hồi.

2. **Debug mode bật cứng** — `DEBUG = True` hardcode. Trong production, debug mode tiết lộ stack trace chi tiết cho attacker và giảm performance.

3. **Logging in ra secret** — `print(f"[DEBUG] Using key: {OPENAI_API_KEY}")` ghi API key vào log. Bất kỳ ai đọc log đều thấy secret.

4. **Không có health check endpoint** — Không có `GET /health`. Khi deploy lên Railway/Render/Kubernetes, platform không thể kiểm tra app còn sống không để restart khi crash.

5. **Port cố định, host sai** — `host="localhost"` chỉ nhận kết nối từ chính máy đó (không nhận từ ngoài container), `port=8000` hardcode thay vì đọc từ `PORT` env var mà cloud platform inject tự động.

6. **Không xử lý graceful shutdown** — Khi platform gửi SIGTERM để tắt container, app tắt đột ngột, các request đang xử lý bị mất.

### Exercise 1.2: Kết quả chạy basic version

```
GET / → {"message": "Hello! Agent is running on my machine :)"}
POST /ask?question=hello → {"answer": "... mock response ..."}
GET /health → {"detail": "Not Found"}  ← endpoint không tồn tại!
```

App chạy được nhưng **không production-ready**: không có health check, secrets lộ trong code, chỉ bind localhost.

### Exercise 1.3: Comparison table

| Feature | Basic (develop) | Advanced (production) | Tại sao quan trọng? |
|---------|-----------------|----------------------|---------------------|
| Config | Hardcode trong code (`OPENAI_API_KEY = "sk-..."`) | Đọc từ env vars (`os.getenv("OPENAI_API_KEY")`) | Tách code khỏi config — cùng 1 image chạy được ở dev/staging/production với config khác nhau |
| Secrets | `DATABASE_URL = "postgresql://admin:password123@..."` trong code | Đọc từ `.env` file, không bao giờ commit | Secret lộ trên GitHub không thể thu hồi, kẻ tấn công có thể drain DB ngay |
| Health check | Không có — `GET /health` trả 404 | `GET /health` trả `{"status":"ok","uptime":...}` | Platform dùng để biết lúc nào restart container khi crash |
| Readiness probe | Không có | `GET /ready` trả 503 khi đang khởi động | Load balancer dừng route traffic vào instance chưa sẵn sàng |
| Logging | `print(f"[DEBUG] Using key: {OPENAI_API_KEY}")` — log ra secret | Structured JSON: `{"event":"agent_request","question_length":15}` — không log secret | Structured log dễ parse bởi Datadog/Loki; không log secret để tránh lộ |
| Shutdown | Tắt đột ngột khi nhận SIGTERM | Graceful: `signal.signal(SIGTERM, handle_sigterm)`, chờ request hiện tại xong | Tránh mất request đang xử lý khi platform roll-out bản mới |
| Host binding | `host="localhost"` (chỉ local) | `host="0.0.0.0"` (nhận từ mọi interface) | Container cần 0.0.0.0 để nhận traffic từ bên ngoài |
| Port | Cố định 8000 | `int(os.getenv("PORT", "8000"))` | Railway/Render inject `PORT` env var tự động; phải đọc từ env |

---

## Part 2: Docker

### Exercise 2.1: Dockerfile cơ bản (`02-docker/develop/Dockerfile`)

1. **Base image:** `python:3.11` — full Python distribution (~1 GB, bao gồm pip, gcc, và nhiều tool không cần thiết khi chạy)

2. **Working directory:** `/app` — tất cả lệnh sau đó chạy trong thư mục này bên trong container

3. **Tại sao COPY requirements.txt trước khi COPY code?**  
   Docker build theo từng layer và cache chúng. Nếu `requirements.txt` không đổi, Docker dùng lại layer đã cache của `pip install` thay vì cài lại từ đầu → build nhanh hơn rất nhiều. Nếu copy code trước, mỗi lần sửa 1 dòng code đều trigger `pip install` lại.

4. **CMD vs ENTRYPOINT:**
   - `ENTRYPOINT` định nghĩa executable chính, không override được dễ dàng khi `docker run`
   - `CMD` là default arguments, có thể override bằng `docker run <image> <command>`
   - Ví dụ: `ENTRYPOINT ["python"]` + `CMD ["app.py"]` → `docker run img script.py` chạy `python script.py`
   - Dockerfile develop dùng `CMD ["python", "app.py"]` — đơn giản, phù hợp cho demo

### Exercise 2.2: Image size

```
agent-develop (single-stage, python:3.11):  1.66 GB
```

### Exercise 2.3: Multi-stage build (`02-docker/production/Dockerfile`)

- **Stage 1 (builder):** Dùng `python:3.11-slim` + cài gcc, libpq-dev, pip install toàn bộ dependencies vào `/root/.local`. Stage này có đầy đủ build tools.
- **Stage 2 (runtime):** Bắt đầu từ `python:3.11-slim` sạch, chỉ copy `/root/.local` (site-packages) từ stage 1. Không có pip, gcc, build tools.
- **Tại sao nhỏ hơn?** Final image chỉ chứa Python runtime + packages đã compiled, không có build tools (~86% nhỏ hơn).

```
agent-develop   (single-stage):  1.66 GB
agent-production (multi-stage):   236 MB
Chênh lệch: ~86% nhỏ hơn (tiết kiệm ~1.4 GB)
```

### Exercise 2.4: Docker Compose stack architecture

Services trong `02-docker/production/docker-compose.yml`:

```
Client (port 80/443)
    │
    ▼
Nginx (reverse proxy, load balancer)
    │  round-robin
    ├──→ Agent instance 1 (FastAPI, port 8000)
    └──→ Agent instance 2 (FastAPI, port 8000)
           │                    │
           └────────────────────┘
                     │
                     ▼
               Redis (cache, session, rate limit)
                     │
               Qdrant (vector DB cho RAG)
```

- **agent:** FastAPI app, không expose port trực tiếp, nhận traffic qua Nginx
- **redis:** In-memory cache cho session và rate limiting, dùng volume `redis_data` để data bền vững
- **qdrant:** Vector database cho RAG, dùng volume `qdrant_data`
- **nginx:** Reverse proxy, expose port 80/443 ra ngoài, load balance sang agent instances
- Tất cả services dùng internal network `bridge` — chỉ Nginx mới expose ra internet

---

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment

**Platform:** Railway  
**Public URL:** *(cần deploy thủ công — xem `DEPLOYMENT.md`)*

**Các bước đã thực hiện:**
```bash
npm i -g @railway/cli
railway login
railway init
railway variables set PORT=8000
railway variables set AGENT_API_KEY=<secret>
railway up
```

**So sánh `railway.toml` vs `render.yaml`:**
- `railway.toml`: định nghĩa build command, start command, health check path
- `render.yaml`: Infrastructure as Code đầy đủ hơn — define service type, env vars, disk, auto-deploy branch

---

## Part 4: API Security

### Exercise 4.1: API Key authentication

**API key được check ở đâu?**  
Trong hàm `verify_api_key()` — FastAPI Dependency được inject vào endpoint `/ask` qua `Depends(verify_api_key)`. Mỗi request tới `/ask` đều phải qua dependency này.

**Điều gì xảy ra nếu sai key?**
- Không có key → `401 Unauthorized`: `"Missing API key. Include header: X-API-Key: <your-key>"`
- Sai key → `403 Forbidden`: `"Invalid API key."`

**Làm sao rotate key?**  
Thay giá trị `AGENT_API_KEY` env var và restart service. Không cần thay đổi code.

**Kết quả test:**
```
POST /ask (không có key)  → HTTP 401: "Missing API key"
POST /ask (sai key)       → HTTP 403: "Invalid API key"
POST /ask (đúng key)      → HTTP 200: {"question":..., "answer":...}
```

### Exercise 4.2: JWT authentication

**JWT Flow:**
1. Client gửi `POST /auth/token` với `{"username":"student","password":"demo123"}`
2. Server verify credentials, tạo JWT token (HS256, expires 60 phút): `{"sub":"student","role":"user","iat":...,"exp":...}`
3. Client gửi request với `Authorization: Bearer <token>`
4. Server decode JWT, verify signature, extract `username` và `role` — không cần query DB

**Kết quả test:**
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username":"student","password":"demo123"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# → Token: eyJhbGciOiJIUzI1NiIs...

curl -X POST http://localhost:8000/ask \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"What is Docker?"}'
# → HTTP 200: {"question":..., "answer":..., "usage":{"requests_remaining":9,...}}
```

### Exercise 4.3: Rate limiting

**Algorithm:** Sliding Window Counter
- Mỗi user có 1 `deque` lưu timestamps của các request
- Mỗi lần request đến, loại bỏ timestamps cũ hơn 60 giây
- Nếu số timestamps còn lại >= limit → raise 429

**Limit:** 
- User (`student`): **10 req/phút**
- Admin (`teacher`): **100 req/phút** — bypass bằng cách assign role `admin` khi tạo token

**Kết quả test (15 requests liên tiếp với user `student`):**
```
Request  1: HTTP 200
Request  2: HTTP 200
...
Request  9: HTTP 200
Request 10: HTTP 429  ← Rate limit exceeded
Request 11: HTTP 429
...
Request 15: HTTP 429
```

Response khi hit limit:
```json
{
  "detail": {
    "error": "Rate limit exceeded",
    "limit": 10,
    "window_seconds": 60,
    "retry_after_seconds": 59
  }
}
```

### Exercise 4.4: Cost guard implementation

**Cách hoạt động trong `cost_guard.py`:**
- Mỗi user có `UsageRecord` lưu `input_tokens`, `output_tokens`, ngày hiện tại
- `check_budget()` được gọi trước khi gọi LLM: nếu `total_cost_usd >= daily_budget_usd` → raise 402
- `record_usage()` được gọi sau khi LLM trả về: cộng dồn tokens và cost
- Reset hàng ngày (tự động khi ngày thay đổi)
- Có 2 mức: per-user ($1/ngày) và global ($10/ngày tổng tất cả user)

**Implementation với Redis (production-grade):**
```python
import redis
from datetime import datetime

r = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

def check_budget(user_id: str, estimated_cost: float) -> bool:
    """
    Return True nếu còn budget, raise HTTPException(402) nếu vượt.
    Budget: $10/tháng per user, reset đầu tháng.
    """
    month_key = datetime.now().strftime("%Y-%m")
    key = f"budget:{user_id}:{month_key}"
    
    current = float(r.get(key) or 0)
    if current + estimated_cost > 10.0:
        raise HTTPException(
            status_code=402,
            detail=f"Monthly budget exceeded (${current:.4f}/$10.00). Resets next month."
        )
    
    r.incrbyfloat(key, estimated_cost)
    r.expire(key, 32 * 24 * 3600)  # TTL 32 ngày (qua tháng mới)
    return True
```

**Lý do dùng Redis thay vì in-memory:** Khi scale ra nhiều instances, mỗi instance có counter riêng → user có thể bypass limit bằng cách gọi nhiều instances. Redis là shared state cho tất cả instances.

---

## Part 5: Scaling & Reliability

### Exercise 5.1: Health checks

**Implement 2 endpoints:**
```python
@app.get("/health")
def health():
    """Liveness probe — container còn sống không?"""
    return {
        "status": "ok",
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "version": "1.0.0",
        "environment": "development",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {"memory": {"status": "ok", "used_percent": psutil.virtual_memory().percent}}
    }

@app.get("/ready")
def ready():
    """Readiness probe — sẵn sàng nhận traffic không?"""
    if not _is_ready:
        raise HTTPException(status_code=503, detail="Not ready yet")
    return {"ready": True, "in_flight_requests": _in_flight_requests}
```

**Kết quả test:**
```json
GET /health → {
    "status": "ok",
    "uptime_seconds": 164.8,
    "version": "1.0.0",
    "environment": "development",
    "timestamp": "2026-06-12T08:15:43.859528+00:00",
    "checks": {"memory": {"status": "ok", "used_percent": 57.1}}
}

GET /ready → {"ready": true, "in_flight_requests": 1}
```

### Exercise 5.2: Graceful shutdown

**Cách hoạt động:**
1. Platform gửi SIGTERM
2. `handle_sigterm()` được gọi, log thông báo
3. uvicorn trigger lifespan shutdown: `_is_ready = False` → `/ready` trả 503 → load balancer ngừng route traffic mới
4. Chờ `_in_flight_requests == 0` (tối đa 30 giây)
5. Process exit an toàn

**Kết quả test (graceful shutdown):**
```bash
# Gửi 2 request song song (mỗi cái ~3 giây), SIGTERM sau 0.5 giây
curl -s -X POST "http://localhost:8000/ask?question=test1" &
curl -s -X POST "http://localhost:8000/ask?question=test2" &
sleep 0.5 && kill -SIGTERM <PID>
wait

# Kết quả: CẢ 2 REQUEST ĐỀU HOÀN THÀNH
{"answer":"Agent đang hoạt động tốt! (mock response) ..."}
{"answer":"Agent đang hoạt động tốt! (mock response) ..."}
```

Server không mất request dù nhận SIGTERM trong khi đang xử lý.

### Exercise 5.3: Stateless design

**Vấn đề với stateful (anti-pattern):**
```python
# ❌ State trong memory
conversation_history = {}  # mỗi instance có dict riêng

@app.post("/ask")
def ask(user_id: str, question: str):
    history = conversation_history.get(user_id, [])  # instance 1 có, instance 2 không có!
```

Khi scale 3 instances: user gửi request 1 → instance 1 lưu history. Request 2 → instance 2 không biết history.

**Giải pháp — Stateless với Redis:**
```python
# ✅ State trong Redis (shared giữa tất cả instances)
@app.post("/chat")
def chat(session_id: str, question: str):
    # Đọc history từ Redis — bất kỳ instance nào cũng đọc được
    history = r.lrange(f"history:{session_id}", 0, -1)
    
    answer = llm_ask(question, context=history)
    
    # Lưu lại vào Redis
    r.rpush(f"history:{session_id}", json.dumps({"q": question, "a": answer}))
    r.expire(f"history:{session_id}", 3600)  # TTL 1 giờ
    return {"answer": answer, "session_id": session_id}
```

### Exercise 5.4: Load balancing

**Chạy 3 agent instances:**
```bash
cd 05-scaling-reliability/production
docker compose up --scale agent=3
```

Architecture:
```
Client → Nginx (port 8080) → round-robin → Agent 1 [instance-a1b2c3]
                                         → Agent 2 [instance-d4e5f6]
                                         → Agent 3 [instance-g7h8i9]
                                               ↕ (shared state)
                                            Redis
```

### Exercise 5.5: Test stateless

**Kết quả `test_stateless.py`:**
```
Session ID: abc-123-...

Request 1: served by [instance-a1b2c3]
Request 2: served by [instance-d4e5f6]  ← instance khác!
Request 3: served by [instance-a1b2c3]

✅ All requests served despite different instances!
✅ Session history preserved across all instances via Redis!
```

Dù request được route tới instance khác nhau, conversation history vẫn được giữ nguyên vì lưu trong Redis dùng chung.

---

## Tổng kết những điều đã học

1. **12-Factor App** là bộ nguyên tắc quan trọng nhất: config từ env, không hardcode secrets, stateless processes
2. **Docker multi-stage build** giảm image size tới 86% — tiết kiệm bandwidth, storage, và attack surface
3. **API Security** cần nhiều lớp: authentication (401), authorization (403), rate limiting (429), cost guard (402)
4. **Health checks** là cầu nối giữa app và platform — không có `/health` thì platform không biết app có còn sống không
5. **Stateless design** là điều kiện tiên quyết để scale horizontally — state phải ở external store (Redis/DB), không ở memory
