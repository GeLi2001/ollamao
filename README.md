# 🦙 ollamao

**A production-grade, OpenAI-compatible LLM serving stack powered by [Ollama](https://ollama.com/).**  
Supports multi-model routing, streaming, auth, logging, and Docker-based deployments — all from a single config file.

> 🧠 Bring your own models. Run them anywhere. Stay in control.

---

## ✨ Features

- ✅ OpenAI-compatible API (`/v1/chat/completions`)
- ✅ Multiple models via `models.yaml`
- ✅ Docker-per-model architecture
- ✅ Streaming support (SSE)
- ✅ API key authentication (MVP)
- ✅ Structured logging
- ✅ Cloud/server ready (CPU or GPU)

---

## 🚀 Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/GeLi2001/ollamao
cd ollamao
```

### 2. Define your models

Edit `config/models.yaml`:

```yaml
models:
  llama3:
    port: 11434
    model: llama3
    quant: Q4_K_M

  mistral:
    port: 11435
    model: mistral
```

### 3. Start the Ollama backends

```bash
docker compose up -d
```

Each model runs in its own container, e.g.:
- http://localhost:11434 → llama3
- http://localhost:11435 → mistral

### 4. Start the API proxy

```bash
uvicorn ollamao.main:app --reload
```

## 🧪 API Usage

POST to `/v1/chat/completions` just like OpenAI:

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer my-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3",
    "messages": [{"role": "user", "content": "hello"}],
    "stream": true
  }'
```

## 🔐 API Keys

Define keys in `config/keys.yaml`:

```yaml
keys:
  my-key:
    name: "Internal Dev"
    quota: unlimited
```

*Quota enforcement coming soon.*

## 🛠️ Architecture

```
         +-----------+        +---------------------+
 Client →| FastAPI   |───────→| http://localhost:11434 (llama3)
         |  Proxy    |───────→| http://localhost:11435 (mistral)
         +-----------+        +---------------------+
                |
                └── Logs, auth, routing, SSE
```

## 📦 Deployment Targets

| Env | Supported | Notes |
|-----|-----------|-------|
| 🖥️ Local dev | ✅ | Use `uvicorn` + `docker compose` |
| ☁️ EC2 | ✅ | CPU or GPU (NVIDIA driver + Ollama) |
| 🐳 Docker | ✅ | Included |
| 🔁 RunPod / Lambda Labs | ✅ | Supports `--gpus all` |
| ☸️ Kubernetes | 🛠️ Planned | (contributions welcome) |

## 📊 Logs

All requests are logged as structured JSON:

```json
{
  "timestamp": "...",
  "model": "llama3",
  "tokens_prompt": 123,
  "tokens_response": 456,
  "latency_ms": 2150
}
```

*Future: per-user usage tracking, rate limits, Prometheus `/metrics`*

## 🧩 Roadmap

- [ ] `/v1/embeddings` support
- [ ] Admin dashboard
- [ ] Hot-reloading `models.yaml`
- [ ] Per-user usage + quotas
- [ ] Cloud bootstrap (RunPod, GPU)
- [ ] Kubernetes templates

## 📜 License

MIT — free to fork, host, modify, or commercialize.

If you're building something on top of **ollamao**, we'd love to see it.

## 🧠 About the Name

**Ollama** = "he who plays the (Mesoamerican) ballgame"  
**ollamao** = Ollama + LMAO 😎

*A playful, powerful dev-first gateway to open models.*

## 💌 Stay in the loop

⭐ Star the repo. Contribute. Or just run your own damn models.

---

## 🚀 Installation & Setup

### Option 1: Development Setup (with uv - recommended)

```bash
# Clone and setup
git clone https://github.com/GeLi2001/ollamao
cd ollamao

# Install dependencies with uv (super fast!)
uv sync --extra dev

# Copy environment config
cp env.example .env

# Start Ollama backends
docker-compose up -d

# Setup models (this will take a while)
./scripts/setup-models.sh

# Start the API server
uv run uvicorn ollamao.main:app --reload
```

### Option 2: Docker Only

```bash
# Start everything
docker-compose up -d

# Setup models
./scripts/setup-models.sh

# Test the API
curl http://localhost:8000/health
```

### Option 3: Production

```bash
# Use production profile
docker-compose --profile production up -d
```

---
