# MASPY Code Generator

Generate and run **[MASPy](https://github.com/laca-is/maspy)** multi-agent systems from natural-language requests.

Undergraduate research project (Iniciação Científica). You describe the agents you want (in Portuguese), a **RAG** pipeline retrieves real MASPy examples and an LLM writes the program, and you can run it right from the browser and watch each agent's output.

> **MASPy** is a Python framework for BDI (Beliefs, Desires, Intentions) multi-agent systems: agents, reactive plans, beliefs, goals, environments and agent communication.

**Live:** https://maspy.web.app

---

## Features

- **Chat that writes MASPy code**: grounded in the example corpus in `data/` (retrieved from Pinecone).
- **Follow-up edits**: "add a third agent" changes the current program (the site sends the current code with the request).
- **Run in the browser**: the **Executar** button runs the program in an isolated sandbox and shows the output with MASPy's own terminal colors.
- **Static view of the program**: agents, beliefs/goals/percepts and `self.send` calls per class.
- **Off-topic guard**: questions unrelated to multi-agent systems / MASPy are answered with a fixed message **without calling Gemini**.
- **Conversation saved in the browser**, plus a **New conversation** button.
- Copy / download the generated `maspy_system.py`.

---

## Architecture

```
Browser
  │   https://maspy.web.app            (Firebase Hosting: forwards every path to Cloud Run)
  ▼
Cloud Run · maspy-rag-api               (FastAPI, Python 3.11)
  ├── /                     static Next.js site (built inside the Docker image)
  ├── GET  /api/            health check
  ├── POST /api/chat        off-topic guard ─▶ Pinecone (top 3 examples) ─▶ Gemini
  └── POST /api/executar    ─────────────▶ Cloud Run · maspy-runner
                                            (Python 3.12 + maspy-ml, no API keys,
                                             permissionless service account,
                                             15 s per run, not public)
```

**How a question is answered** (`app/rag_service.py`):

1. `app/guardrails.py` rejects off-topic questions (keyword check, no API cost).
2. Keyword intent detection (`app/domain.py`) picks MASPy entities (Agent, Communication, Belief_Goal, Environment…).
3. The question is embedded with `gemini-embedding-001` (768 dims, `app/embeddings.py`) and searched in the Pinecone index `rag-docs`, filtered by those entities, keeping the 3 closest example files.
4. A single Gemini call (`GEMINI_MODEL`, default `gemini-3.5-flash-lite`) writes the full program using only API seen in the examples.
5. The site splits the answer: the explanation stays in the chat and the program goes to the code panel.

---

## Project structure

```
app/                  Cloud API (FastAPI): routes, guard, RAG chain, embeddings
runner/               Isolated code executor (separate Cloud Run service)
frontend/chat_rag/    Next.js site (chat + code panel + console)
data/                 MASPy example programs (the RAG knowledge base)
scripts/ingest.py     Uploads data/ to Pinecone
firebase/             Firebase Hosting config for the friendly URL
Dockerfile            Builds the site (Node) and the API (Python) into one image
```

---

## Running locally

### Prerequisites

- Python **3.11** (API) and Python **3.12** (executor; MASPy requires 3.12+)
- Node.js **20+**
- A [Gemini API key](https://aistudio.google.com/) and a [Pinecone](https://www.pinecone.io/) account

Create a `.env` file in the project root (it is git-ignored):

```env
GOOGLE_API_KEY=your_gemini_key
PINECONE_API_KEY=your_pinecone_key
RUNNER_URL=http://localhost:8081
# optional: GEMINI_MODEL=gemini-3.8-flash
```

### 1. Install

```bash
# API
python -m venv venv
venv/Scripts/python -m pip install -r requirements.txt          # Linux/macOS: venv/bin/python

# Executor (Python 3.12)
py -3.12 -m venv runner/.venv                                   # Linux/macOS: python3.12 -m venv runner/.venv
runner/.venv/Scripts/python -m pip install -r runner/requirements.txt

# Site
cd frontend/chat_rag && npm install
```

### 2. Load the examples into Pinecone (once)

Create an index named **`rag-docs`** with **768 dimensions** and the **cosine** metric, then:

```bash
venv/Scripts/python scripts/ingest.py
```

### 3. Start the services (one terminal each, from the project root)

```bash
runner/.venv/Scripts/python -m uvicorn main:app --app-dir runner --port 8081   # executor
venv/Scripts/python -m uvicorn app.main:app --port 8080                         # API
cd frontend/chat_rag && npm run dev                                             # site on :3000
```

Open **http://localhost:3000**. The dev site is configured in `frontend/chat_rag/.env.development.local`:

| `NEXT_PUBLIC_API_MOCK` | Chat | Executar | Gemini cost |
|---|---|---|---|
| `1` | canned answers (`lib/mock.ts`) | simulated | none |
| `chat` | canned answers | **real** (local executor) | none |
| `0` | **real** | **real** | 1 request per question |

To test the production setup (site served by the API on **http://localhost:8080**), build the site and copy it to `static/`:

```bash
cd frontend/chat_rag && npm run build && cd ../.. && rm -rf static && cp -r frontend/chat_rag/out static
```

---

## Deploying to Google Cloud

Project `maspy-rag-api-2026`, region `us-central1`. Run from the project root.

### Updating (everyday use)

```bash
# Site + API (the site is built inside the image)
gcloud run deploy maspy-rag-api --source . --region us-central1 --project maspy-rag-api-2026

# Executor (only when runner/ changes)
gcloud run deploy maspy-runner --source runner --region us-central1 --project maspy-rag-api-2026
```

`https://maspy.web.app` picks up new revisions automatically. What is uploaded is controlled by `.gcloudignore` (keys, `venv/`, `node_modules/` and `.next/` stay out).

### First-time setup

```bash
# 1. Service account with no permissions, for the executor
gcloud iam service-accounts create maspy-runner-sa --display-name "MASPY runner" --project maspy-rag-api-2026

# 2. Executor: private, one run at a time, at most 3 instances
gcloud run deploy maspy-runner --source runner --region us-central1 --project maspy-rag-api-2026 \
  --service-account maspy-runner-sa@maspy-rag-api-2026.iam.gserviceaccount.com \
  --no-allow-unauthenticated --concurrency 1 --max-instances 3 --memory 512Mi --timeout 30

# 3. Allow the API (default compute service account) to call the executor
gcloud run services add-iam-policy-binding maspy-runner --region us-central1 --project maspy-rag-api-2026 \
  --member serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com --role roles/run.invoker

# 4. Site + API, with keys and the executor URL
gcloud run deploy maspy-rag-api --source . --region us-central1 --project maspy-rag-api-2026 --allow-unauthenticated \
  --update-env-vars GOOGLE_API_KEY=...,PINECONE_API_KEY=...,RUNNER_URL=https://maspy-runner-....run.app
```

Use `--update-env-vars` (not `--set-env-vars`) on later deploys so existing variables are kept.

**Friendly URL**: Firebase Hosting site `maspy` with a single rewrite of `**` to the `maspy-rag-api` service (see `firebase/firebase.json`). It only needs to be set up once, e.g. with `cd firebase && npx firebase-tools deploy --only hosting`.

---

## API

| Method | Path | Body | Response |
|---|---|---|---|
| `GET` | `/api/` | – | `{"status": "online"}` |
| `POST` | `/api/chat` | `{"pergunta": "..."}` | `{"resposta": "markdown with a python block"}` |
| `POST` | `/api/executar` | `{"codigo": "..."}` | `{"status": "concluido" \| "erro" \| "tempo_esgotado", "saida", "erro", "duracao_s"}` |

Example:

```json
POST /api/chat
{ "pergunta": "Crie um vendedor e um comprador que negociam um preço. O comprador aceita qualquer valor abaixo de 50." }
```

---

## Costs and limits

- **Gemini**: 1 request per on-topic question; off-topic questions are blocked before Gemini. The free tier allows a limited number of requests per day per model; when it runs out the chat shows a quota message (HTTP 429).
- **Executor**: 15 s per run (agents that never call `stop_cycle()` are stopped), 512 MiB, one run per instance, at most 3 instances. The first run on a new instance is slower (~6–8 s) while pandas/numpy load.
- **Firebase Hosting**: requests through `maspy.web.app` time out after 60 s.
