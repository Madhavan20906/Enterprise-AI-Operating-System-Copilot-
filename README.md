# 🧠 Enterprise AI Operating System

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blueviolet?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi)
![Next.js](https://img.shields.io/badge/Next.js-16-black?style=for-the-badge&logo=next.js)
![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-4B32C3?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-blue?style=for-the-badge)

**A production-grade, multi-agent AI platform built for the enterprise.**
Intelligent document understanding, real-time streaming chat, hybrid RAG, and autonomous agent orchestration — all in one system.

[Features](#-features) • [Architecture](#-architecture) • [Quick Start](#-quick-start) • [Tech Stack](#-tech-stack) • [Project Structure](#-project-structure) • [API Docs](#-api-docs) • [Roadmap](#️-roadmap) • [Contributing](#-contributing)

</div>

---

## 📌 Overview

Enterprise AI Operating System is a self-hostable platform that lets organizations turn their internal documents, projects, and teams into a queryable, agent-driven knowledge layer. Instead of a single chatbot bolted onto a vector store, it runs a **graph of specialized agents** — planning, retrieving, reasoning, reporting, coding, summarizing meetings, and automating workflows — coordinated by LangGraph and backed by a hybrid retrieval pipeline and a knowledge graph of how people, documents, and projects relate to one another.

It's built to be run locally with Docker Compose for development, and to scale onto Kubernetes for production.

---

## ✨ Features

### 🤖 Multi-Agent Orchestration
- **LangGraph-powered** stateful agent graph with dynamic routing
- Specialized agents: **Planner, Retrieval, Reasoning, Report, Code, Meeting, Workflow, Analytics**
- Agents collaborate autonomously to resolve complex enterprise queries

### 📚 Hybrid RAG Pipeline
- **Dual-path retrieval**: dense vector search (Qdrant) + keyword BM25 search
- **Reciprocal Rank Fusion (RRF)** for result merging
- **Cross-encoder re-ranking** for precision-optimized answers
- Layout-aware parsing, OCR fallback, parent-child chunking

### 🔐 Enterprise Auth & RBAC
- JWT-based authentication with role-based access control
- Roles: `employee`, `team_lead`, `manager`, `hr`, `administrator`
- Secure document access scoped to ownership and organizational hierarchy

### 📡 Real-Time Streaming
- **Server-Sent Events (SSE)** for live token streaming from the LLM
- Typing cursor indicator, agent step visibility, and full conversation history

### 🕸️ Knowledge Graph
- Neo4j integration linking Documents, Employees, Projects, and Teams
- Auto-extracted entities and relationships from ingested documents
- Interactive SVG graph visualization in the dashboard

### 📊 Observability Dashboard
- Real-time container health (Postgres, Qdrant, Redis)
- Token usage tracking, estimated cost analytics, chat thread metrics
- Security audit logs for all user actions (admin-only)

### 📁 Document Management
- Drag-and-drop ingestion supporting PDF, DOCX, PPTX, XLSX, CSV, TXT, MD, and images
- Async background processing via **Celery** task queue
- Auto document classification and deduplication via SHA-256 content hash
- 50 MB file size support

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Next.js Frontend                      │
│         /login  /register  /dashboard  /chat             │
└──────────────────────┬────────────────────────────────────┘
                        │ HTTP / SSE
┌──────────────────────▼────────────────────────────────────┐
│                   FastAPI Backend                         │
│    Auth │ Users │ Documents │ Chat │ Analytics            │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              LangGraph Agent Graph                   │  │
│  │  Planner → Retrieval → Reasoning → Report            │  │
│  │           ↘ Code ↗ Meeting ↗ Workflow                │  │
│  └─────────────────────────────────────────────────────┘  │
└──────┬───────────┬────────────┬────────────┬───────────────┘
       │            │            │            │
  PostgreSQL     Qdrant        Redis         Neo4j
  (Users/Docs)  (Vectors)   (Cache/Queue)  (Knowledge Graph)
```

**Request flow:** the frontend calls the FastAPI backend over HTTP for standard operations and opens an SSE connection for chat. Incoming chat queries enter the LangGraph agent graph, where the Planner agent decides which downstream agents to invoke (Retrieval, Reasoning, Report, Code, Meeting, or Workflow), each of which may read from Postgres, Qdrant, Redis, or Neo4j before the final answer streams back token-by-token.

---

## 🚀 Quick Start

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (running)
- Python 3.10+
- Node.js 18+

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/enterprise-ai-os.git
cd enterprise-ai-os
```

### 2. Configure environment
```bash
cp backend/.env.example backend/.env
# Edit backend/.env and add your GROQ_API_KEY
```

Key variables to set in `backend/.env`:

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | API key for Groq (LLaMA 3.3 70B inference) |
| `DATABASE_URL` | PostgreSQL connection string |
| `QDRANT_URL` | Qdrant vector database endpoint |
| `REDIS_URL` | Redis connection string (cache + Celery broker) |
| `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` | Neo4j knowledge graph credentials |
| `JWT_SECRET_KEY` | Secret used to sign JWT tokens |

### 3. Start infrastructure (Docker)
```bash
docker-compose up -d
```
This brings up PostgreSQL, Qdrant, Redis, and Neo4j.

### 4. Start the backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
venv\Scripts\uvicorn.exe app.main:app --reload --host 0.0.0.0 --port 8000
```
> ⏳ Wait ~30–60 seconds for HuggingFace embedding models to load.
> You'll see `Application startup complete.` when ready.

### 5. Start the frontend (new terminal)
```bash
cd frontend
npm install
npm run dev
```

### 6. Open the app
| Service | URL |
|---|---|
| **App** | http://localhost:3000 |
| **API Docs** | http://localhost:8000/api/v1/docs |
| **API Health** | http://localhost:8000/health |

**Default admin credentials:**
```
Email:    admin@enterprise.com
Password: AdminPassword123!
```
> ⚠️ Change these immediately in any non-local environment.

---

## 🛠️ Tech Stack

### Backend
| Technology | Purpose |
|---|---|
| **FastAPI** | High-performance async REST API |
| **LangGraph** | Stateful multi-agent orchestration |
| **LangChain** | LLM chains, RAG, embeddings |
| **Groq (LLaMA 3.3 70B)** | Ultra-fast LLM inference |
| **HuggingFace** | Local embedding models |
| **Qdrant** | Vector database for semantic search |
| **PostgreSQL** | Primary relational database |
| **Redis** | Caching and Celery task broker |
| **Celery** | Async background task processing |
| **Neo4j** | Knowledge graph database |
| **SQLAlchemy + Alembic** | ORM and database migrations |
| **PassLib + JWT** | Authentication & security |

### Frontend
| Technology | Purpose |
|---|---|
| **Next.js 16** | React framework (App Router) |
| **TypeScript** | Type-safe development |
| **Tailwind CSS** | Utility-first styling |
| **SSE (EventSource)** | Real-time token streaming |

### Infrastructure
| Technology | Purpose |
|---|---|
| **Docker Compose** | Local service orchestration |
| **Kubernetes (k8s/)** | Production deployment manifests |

---

## 📁 Project Structure

```
enterprise-ai-os/
├── backend/
│   ├── app/
│   │   ├── agents/          # LangGraph agent implementations
│   │   │   ├── graph.py     # Main agent orchestration graph
│   │   │   ├── planner.py   # Task planning agent
│   │   │   ├── retrieval.py # Hybrid RAG retrieval agent
│   │   │   ├── reasoning.py # Chain-of-thought reasoning agent
│   │   │   ├── report.py    # Report generation agent
│   │   │   ├── code.py      # Code generation agent
│   │   │   ├── meeting.py   # Meeting summarization agent
│   │   │   └── workflow.py  # Workflow automation agent
│   │   ├── api/routes/      # FastAPI route handlers
│   │   ├── domain/          # SQLAlchemy entities & enums
│   │   ├── infrastructure/  # DB, Qdrant, Neo4j clients
│   │   ├── core/             # Security, config, dependencies
│   │   └── main.py           # App entrypoint
│   ├── alembic/              # Database migrations
│   ├── tests/                # Backend test suite
│   └── requirements.txt
├── frontend/
│   └── src/app/
│       ├── login/            # Auth pages
│       ├── register/
│       ├── dashboard/        # Knowledge base, analytics, graph, audit
│       └── chat/             # Real-time streaming AI chat
├── k8s/                       # Kubernetes manifests
├── docker-compose.yml          # Local infrastructure
└── README.md
```

---

## 📖 API Docs

Once the backend is running, visit:
**http://localhost:8000/api/v1/docs** — Interactive Swagger UI

Key endpoints:
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/login` | Get JWT token |
| `POST` | `/api/v1/users/` | Register new user |
| `GET` | `/api/v1/users/me` | Get current user |
| `POST` | `/api/v1/documents/upload` | Upload & ingest document |
| `GET` | `/api/v1/documents/` | List all documents |
| `POST` | `/api/v1/chat/stream` | SSE streaming chat |
| `GET` | `/api/v1/analytics/overview` | Platform metrics |
| `GET` | `/api/v1/analytics/graph` | Knowledge graph data |
| `GET` | `/api/v1/analytics/audit-logs` | Security audit logs |

---

## 🧪 Testing

```bash
cd backend
pytest tests/ -v
```

CI-friendly test suite covers auth, document ingestion, retrieval, and agent routing logic.

---

## 🗺️ Roadmap

- [ ] Fix frontend–backend CORS on local dev
- [ ] Celery worker startup in Docker Compose
- [ ] OAuth2 / SSO integration (Google, Microsoft)
- [ ] Multi-tenant organization management
- [ ] Webhook support for external connectors (Slack, Notion, Confluence)
- [ ] Kubernetes Helm chart for cloud deployment
- [ ] LLM evaluation & feedback loop dashboard

---

## 🤝 Contributing

Contributions are welcome!

1. Open an issue first to discuss what you'd like to change.
2. Fork the repo and create a feature branch (`git checkout -b feature/my-feature`).
3. Make your changes with clear, focused commits.
4. Ensure `pytest` passes and the frontend builds cleanly (`npm run build`).
5. Open a pull request describing the change and why it's needed.

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---
