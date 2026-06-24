# PathMind AI — Technical Documentation

**Version:** 1.0  
**Last Updated:** June 24, 2026

---

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [Technology Stack](#2-technology-stack)
3. [Service Breakdown](#3-service-breakdown)
4. [Database Schema](#4-database-schema)
5. [API Reference](#5-api-reference)
6. [AI Agent Pipeline](#6-ai-agent-pipeline)
7. [Content Swarm Architecture](#7-content-swarm-architecture)
8. [RAG & Caching Strategy](#8-rag--caching-strategy)
9. [Frontend Architecture](#9-frontend-architecture)
10. [Data Flow Diagrams](#10-data-flow-diagrams)
11. [Environment Variables Reference](#11-environment-variables-reference)
12. [Deployment Guide](#12-deployment-guide)
13. [Local Development Setup](#13-local-development-setup)

---

## 1. System Architecture Overview

PathMind AI uses a **distributed microservice architecture** with three distinct backend services and a managed database/vector-store layer.

```
┌─────────────────────────────────────────────────────────────────┐
│                        BROWSER / CLIENT                          │
│   React + Vite + ReactFlow (port 5173 dev / Vercel prod)        │
└─────────────────┬────────────────────┬──────────────────────────┘
                  │ REST + SSE          │ REST + SSE
                  ▼                    ▼
┌─────────────────┐      ┌─────────────────────────────┐
│  Go State/CRUD  │      │   Python AI Backend          │
│  Backend        │      │   (FastAPI + LangGraph)      │
│  Port: 4000     │─────▶│   Port: 8000                 │
│  (Gorilla Mux)  │proxy │   (Uvicorn ASGI)             │
└────────┬────────┘ SSE  └──────────┬──────────────────┘
         │                          │
         │ REST (service key)        │ supabase-py + asyncio
         ▼                          ▼
┌────────────────────────────────────────────────────────────────┐
│                    MANAGED SERVICES LAYER                       │
│                                                                 │
│  ┌──────────────────────┐    ┌─────────────────────────────┐  │
│  │   Supabase           │    │   Pinecone (Vector DB)       │  │
│  │   PostgreSQL + Auth  │    │   Namespaces:                │  │
│  │   Row Level Security │    │   • node_content             │  │
│  │                      │    │   • curriculum_cache         │  │
│  │   Tables:            │    │   • user_memory_{uid}        │  │
│  │   • user_profiles    │    └─────────────────────────────┘  │
│  │   • learning_paths   │                                      │
│  │   • path_nodes       │    ┌─────────────────────────────┐  │
│  │   • survey_responses │    │   LLM APIs                   │  │
│  │   • node_resources   │    │   • Google Gemini 2.5 Flash  │  │
│  │   • sessions         │    │     (ProfileBuilder,         │  │
│  └──────────────────────┘    │      CurriculumPlanner,      │  │
│                               │      MemoryConsolidator)     │  │
│                               │   • Groq llama-3.3-70b      │  │
│                               │     (QueryGenerator,         │  │
│                               │      Synthesizer)            │  │
│                               └─────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

### Responsibility Matrix

| Service | Owns | Does NOT Own |
|---|---|---|
| **Python Backend** | AI session lifecycle, LangGraph state, LLM calls, Swarm | CRUD operations, path history list |
| **Go Backend** | Path CRUD, node completion logic, DAG unlocking, SSE proxy | LLM calls, AI state |
| **Frontend** | UI, state display, SSE stream reading | Business logic, LLM calls |
| **Supabase** | Auth, relational persistence, RLS | AI logic |
| **Pinecone** | Semantic caching, user memory | Relational data |

---

## 2. Technology Stack

### Frontend
| Technology | Version | Purpose |
|---|---|---|
| React | 19.2.6 | UI framework |
| Vite | 8.0 | Build tool / dev server |
| @xyflow/react (ReactFlow) | 12.11 | Interactive graph canvas |
| TailwindCSS | 3.4 | Utility-first CSS (custom design tokens) |
| @supabase/supabase-js | 2.108 | Auth + direct DB client |
| framer-motion | 12.40 | Animations |
| lucide-react | 1.21 | Icons |
| react-markdown | 10.1 | Markdown rendering |
| recharts | 3.8 | Charts (planned) |

### Python AI Backend
| Technology | Version | Purpose |
|---|---|---|
| FastAPI | Latest | ASGI web framework |
| LangGraph | Latest | AI agent state machine |
| LangChain | Latest | LLM chains and prompts |
| langchain-google-genai | Latest | Gemini 2.5 Flash integration |
| langchain-groq | Latest | Groq/llama-3.3-70b integration |
| supabase-py | Latest | Supabase DB client |
| pinecone-client | Latest | Pinecone vector operations |
| google-api-python-client | Latest | YouTube Data API v3 |
| youtube-transcript-api | Latest | YouTube transcript extraction |
| pydantic | v2 | Schema validation |
| uvicorn | Latest | ASGI server |

### Go Backend
| Technology | Version | Purpose |
|---|---|---|
| Go | 1.21+ | Language |
| gorilla/mux | Latest | HTTP router |
| joho/godotenv | Latest | .env loading |
| nedpals/supabase-go | Latest | Supabase client |

### Managed Services
| Service | Usage |
|---|---|
| Supabase | PostgreSQL DB + Auth + Row Level Security |
| Pinecone | Vector similarity search (semantic caching) |
| Render | Cloud hosting (Go + Python backends) |
| Vercel | Frontend hosting |

---

## 3. Service Breakdown

### 3.1 Python AI Backend (`/backend`)

**Entry Point:** `backend/app/main.py`  
**Port:** 8000  
**Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port 8000`

**CORS Configuration:** Reads from `CORS_ORIGINS` env var (comma-separated). Defaults: `http://localhost:3000,http://localhost:5173`

**Router prefix:** `/api/v1`

**Key modules:**

```
backend/app/
├── main.py               # FastAPI app setup, CORS, router include
├── config.py             # Centralized env vars
├── routes.py             # All HTTP endpoints
├── models.py             # Pydantic request models
├── api/
│   └── auth.py           # JWT verification via Supabase singleton
└── Agent/
    ├── Graph.py           # LangGraph workflow assembly
    ├── GraphService.py    # Session lifecycle orchestrator
    ├── LearnerState.py    # TypedDict state schema
    ├── Nodes/             # Main graph agent nodes
    │   ├── ProfileBuilder.py      # Survey generation (Gemini)
    │   ├── CurriculumPlanner.py   # DAG generation (Gemini)
    │   ├── MemoryConsolidator.py  # Session summary (Gemini)
    │   └── ErrorHandler.py        # Error recovery routing
    ├── Swarm/             # Content Swarm sub-graph
    │   ├── SwarmGraph.py          # Swarm LangGraph assembly
    │   └── Nodes/
    │       ├── QueryGenerator.py      # 3 search queries (Groq)
    │       ├── PracticalWorker.py     # Web search
    │       ├── AcademicWorker.py      # Academic search
    │       ├── MultimediaWorker.py    # YouTube search + transcript
    │       ├── Synthesizer.py         # Resource curation (Groq)
    │       └── VectorIngestionGate.py # Persist to Pinecone + DB
    └── Tools/
        ├── Database.py    # Supabase wrapper (all DB ops)
        ├── RAGService.py  # Cache lookup orchestration
        ├── VectorStore.py # Pinecone wrapper
        ├── Embeddings.py  # Embedding model (for Pinecone)
        └── LlmFactory.py  # Key rotation + retry logic
```

### 3.2 Go State/CRUD Backend (`/go-backend`)

**Entry Point:** `go-backend/main.go`  
**Port:** 4000 (default)  
**Start Command:** `./main` (after `go build -o main`)

The Go backend has been refactored from a single monolithic file into a clean package structure. Uses `nedpals/supabase-go` for write operations and custom helpers for reads.

**Package Structure:**
```
go-backend/
├── main.go               # Slim HTTP router (~50 lines)
├── db/
│   └── supabase.go       # DB query and patch helpers
├── handlers/
│   ├── conversations.go  # getConversations, getCurriculum
│   └── nodes.go          # getNodeDetails, generateNodeProxy, completeNode
└── middleware/
    ├── auth.go           # JWT verification logic
    └── cors.go           # CORS configuration
```

**Routes:**
```
GET  /api/v1/users/{userId}/conversations                         → getConversations
GET  /api/v1/users/{userId}/conversations/{conversationId}        → getCurriculum
GET  /api/v1/users/{userId}/conversations/{conversationId}/nodes/{nodeId}          → getNodeDetails
GET  /api/v1/users/{userId}/conversations/{conversationId}/nodes/{nodeId}/generate → generateNodeProxy (SSE)
POST /api/v1/users/{userId}/conversations/{conversationId}/nodes/{nodeId}/complete  → completeNode
```

### 3.3 Frontend (`/frontend`)

**Entry Point:** `frontend/src/main.jsx`  
**Port:** 5173 (Vite dev server)  
**Build:** `npm run build` → `/frontend/dist`

**File structure:**
```
frontend/src/
├── main.jsx              # React DOM root, AuthContext provider
├── App.jsx               # Main app layout, routing logic
├── App.css               # Global styles
├── index.css             # Tailwind base styles
├── config/
│   └── supabase.js       # Supabase client singleton
├── constants/
│   ├── nodeStatus.js     # Status enums
│   └── phases.js         # Phase enums
├── services/
│   ├── aiApi.js          # Python backend fetch wrappers
│   └── pathApi.js        # Go backend fetch wrappers
├── utils/
│   └── graphLayout.js    # Layout algorithms
├── context/
│   └── AuthContext.jsx   # Auth state context provider
├── hooks/
│   └── useLearningPath.js # All AI session state + API calls
└── components/
    ├── layout/           # Structural layout components (Sidebar)
    ├── auth/             # Auth UI (Auth.jsx)
    ├── graph/            # ReactFlow graph (GraphCanvas, CustomNode)
    ├── node/             # Slide-in panel (NodeDetailPanel, QuestionCard)
    ├── path/             # Path management (NewPathModal)
    └── survey/           # Onboarding (SurveyCard)
```

---

## 4. Database Schema

### 4.1 `user_profiles`
```sql
id                  UUID PRIMARY KEY  -- matches Supabase auth.users.id
name                TEXT
background          TEXT
learning_style      TEXT              -- 'visual' | 'auditory' | etc.
daily_time_budget_minutes INT DEFAULT 30
learning_goals      TEXT[]
```

### 4.2 `learning_paths`
```sql
id                  UUID PRIMARY KEY DEFAULT gen_random_uuid()
thread_id           TEXT UNIQUE NOT NULL   -- LangGraph thread ID (generated by frontend)
user_id             UUID NOT NULL REFERENCES user_profiles(id)
learning_goal       TEXT NOT NULL
skill_ratings       JSONB DEFAULT '{}'     -- { "Python": 3, "Statistics": 1 }
curriculum_graph    JSONB                  -- Full graph: { goal, section_titles, nodes, edges }
completed_node_ids  TEXT[] DEFAULT '{}'
sections_generated  INT DEFAULT 0
current_section     INT DEFAULT 1
phase               TEXT DEFAULT 'onboarding'  -- 'onboarding' | 'graph_ready'
created_at          TIMESTAMPTZ DEFAULT NOW()
updated_at          TIMESTAMPTZ DEFAULT NOW()   -- auto-updated via trigger
```
**Indexes:** `(user_id, created_at DESC)` for fast history lookup  
**RLS:** Users can only manage their own rows

### 4.3 `path_nodes`
```sql
id                  UUID PRIMARY KEY DEFAULT gen_random_uuid()
path_id             UUID NOT NULL REFERENCES learning_paths(id) ON DELETE CASCADE
user_id             UUID NOT NULL REFERENCES user_profiles(id)
node_id             TEXT NOT NULL               -- URL-safe slug: "python-basics"
title               TEXT NOT NULL
description         TEXT
section_number      INT DEFAULT 1
section_title       TEXT
difficulty          INT DEFAULT 1 CHECK (1..5)
estimated_minutes   INT DEFAULT 30
is_major            BOOLEAN DEFAULT FALSE
prerequisites       TEXT[] DEFAULT '{}'         -- Array of node_id slugs
status              TEXT DEFAULT 'locked'       -- locked | available | in_progress | completed
resources_cached    JSONB                       -- null until swarm generates
questions_cached    JSONB                       -- null until swarm generates
completed_at        TIMESTAMPTZ
created_at          TIMESTAMPTZ DEFAULT NOW()
UNIQUE(path_id, node_id)
```
**Indexes:** `(path_id, status)` for status queries  
**RLS:** Users can only manage their own rows

### 4.4 `survey_responses`
```sql
id          UUID PRIMARY KEY DEFAULT gen_random_uuid()
path_id     UUID REFERENCES learning_paths(id) ON DELETE CASCADE
user_id     UUID NOT NULL REFERENCES user_profiles(id)
topic       TEXT NOT NULL
question    TEXT NOT NULL
rating      INT NOT NULL CHECK (0..5)
created_at  TIMESTAMPTZ DEFAULT NOW()
```
**Indexes:** `(user_id, topic)` for skill aggregation

### 4.5 `node_resources` (Shared Global Cache)
```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
node_slug       TEXT UNIQUE NOT NULL               -- e.g. "python-basics"
title           TEXT NOT NULL
description     TEXT                               -- 2–3 sentence summary
resources       JSONB NOT NULL DEFAULT '[]'        -- [{ type, title, url, why_relevant }]
questions       JSONB NOT NULL DEFAULT '[]'        -- [{ text, options, correct }]
pinecone_ids    TEXT[] DEFAULT '{}'
generated_at    TIMESTAMPTZ DEFAULT NOW()
```
**RLS:** Public read, service-role writes only

### 4.6 `sessions`
```sql
id              UUID PRIMARY KEY  -- = LangGraph thread_id
user_id         UUID NOT NULL REFERENCES user_profiles(id)
summary         TEXT              -- AI-generated session summary
topics_covered  TEXT[]
ended_at        TIMESTAMPTZ
```

---

## 5. API Reference

### 5.1 Python AI Backend — `/api/v1`

All endpoints require: `Authorization: Bearer <supabase_jwt>`

#### `POST /api/v1/agent/start`
Start a new learning session or resume an existing one.

**Request body:**
```json
{
  "thread_id": "thread-1719200000000-abc12",
  "initial_prompt": "I want to learn Machine Learning"
}
```
**Response:** `text/event-stream` SSE  
**Events:**
```
data: {"type": "connection_established", "message": "Streaming started"}
data: {"type": "node_update", "node": "profile_builder"}
data: {"type": "execution_complete", "payload": {
    "phase": "onboarding",
    "survey_question": {"topic": "Python", "question": "Rate your Python knowledge..."},
    "survey_progress": {"answered": 0, "total": 6}
}}
```

#### `POST /api/v1/agent/survey-answer`
Submit one self-assessment answer.

**Request body:**
```json
{
  "thread_id": "thread-1719200000000-abc12",
  "topic": "Python",
  "rating": 3
}
```
**Response:** `application/json`
```json
// Not complete:
{"survey_complete": false, "next_question": {"topic": "Statistics", "question": "..."}, "progress": {"answered": 1, "total": 6}}

// Complete:
{"survey_complete": true, "skill_ratings": {"Python": 3, "Statistics": 1, ...}}
```

#### `POST /api/v1/agent/generate-curriculum`
Trigger curriculum generation after survey is complete.

**Request body:**
```json
{"thread_id": "thread-1719200000000-abc12"}
```
**Response:** `text/event-stream` SSE  
**Final event:**
```json
{"type": "execution_complete", "payload": {
  "phase": "graph_ready",
  "curriculum_graph": {
    "goal": "Learn Machine Learning",
    "section_titles": ["Section 1: Foundations", "Section 2: Core ML"],
    "nodes": [
      {
        "id": "python-basics",
        "title": "Python Basics",
        "description": "...",
        "prerequisites": [],
        "difficulty": 1,
        "estimated_minutes": 30,
        "section": "Section 1: Foundations",
        "section_number": 1,
        "is_major": true,
        "status": "available"
      }
    ],
    "edges": [
      {"id": "e-python-basics-numpy", "source": "python-basics", "target": "numpy", "type": "smoothstep", "animated": true}
    ]
  }
}}
```

#### `POST /api/v1/agent/generate-node`
Trigger content swarm for a specific node. (Called by Go backend's proxy.)

**Request body:**
```json
{
  "node_id": "python-basics",
  "thread_id": "thread-1719200000000-abc12",
  "title": "Python Basics",
  "description": "Core Python syntax and data structures",
  "learning_goal": "Learn Machine Learning"
}
```
**Response:** `text/event-stream` SSE  
**Events:**
```
data: {"type": "status", "message": "Gathering resources"}
data: {"type": "ready", "source": "swarm"}  // or "pinecone_cache"
```

#### `POST /api/v1/agent/end`
End a session (triggers background memory consolidation).

**Response:** `{"status": "success", "message": "Session ended. Memory consolidation queued."}`

---

### 5.2 Go State Backend — `/api/v1`

No authentication required (trusts frontend auth; uses service key to DB).

#### `GET /api/v1/users/{userId}/conversations`
List all learning paths for a user, sorted newest first. Enriches with `node_count` and `completed_count`.

**Response:**
```json
{"paths": [{"id": "uuid", "thread_id": "...", "learning_goal": "...", "phase": "graph_ready", "node_count": 15, "completed_count": 3, ...}]}
```

#### `GET /api/v1/users/{userId}/conversations/{conversationId}`
Get full curriculum graph for a conversation (thread_id).

**Response:**
```json
{
  "phase": "graph_ready",
  "curriculum_graph": {...},
  "completed_node_ids": ["python-basics"],
  "learning_goal": "Learn Machine Learning"
}
```

#### `GET /api/v1/users/{userId}/conversations/{conversationId}/nodes/{nodeId}`
Get full details for a single node (including cached resources).

**Response:** Full `path_nodes` row as JSON.

#### `GET /api/v1/users/{userId}/conversations/{conversationId}/nodes/{nodeId}/generate`
**SSE Proxy.** Fetches node metadata from Supabase, then calls Python backend's `/api/v1/agent/generate-node`, proxies the SSE stream back to the client.

#### `POST /api/v1/users/{userId}/conversations/{conversationId}/nodes/{nodeId}/complete`
Mark a node as completed. Performs the DAG unlock calculation:
1. Marks `nodeId` as `completed` in `path_nodes` and `curriculum_graph`
2. Computes which previously-locked nodes now have all prerequisites completed
3. Updates those nodes to `available` in both `path_nodes` and `curriculum_graph`
4. Updates `completed_node_ids` in `learning_paths`
5. Returns updated `curriculum_graph` to the client

**Response:**
```json
{
  "success": true,
  "completed_node_id": "python-basics",
  "curriculum_graph": {...}  // Updated graph with new statuses
}
```

---

## 6. AI Agent Pipeline

### 6.1 Main LangGraph (`app_graph`)

```
[START]
   │
   ▼
profile_builder  ──────────────────────── route_after_profile ──┐
(Gemini 2.5 Flash)                                              │
   │                                                             │
   ├── survey_complete=False → [END] (waits for survey answers) │
   ├── error → error_handler                                     │
   └── survey_complete=True → curriculum_planner ◄──────────────┘
                                      │
                              route_after_curriculum
                                      │
                              ├── END (success)
                              └── error_handler
                                        │
                                 route_after_error
                                        │
                                 ├── curriculum_planner (retry)
                                 └── END (replan_storm)
```

### 6.2 LearnerState Schema

The `LearnerState` TypedDict is the central state object passed between all graph nodes:

| Field | Type | Description |
|---|---|---|
| `user_id` | str | Supabase auth UUID |
| `session_id` | str | LangGraph thread ID |
| `user_profile` | dict | Goal, background, learning style from DB |
| `skill_ratings` | dict | `{topic: 0-5}` from survey |
| `learning_goal` | str | Free-text goal from user |
| `curriculum_graph` | dict | `{goal, section_titles, nodes, edges}` |
| `completed_node_ids` | List[str] | Node slugs marked complete |
| `survey_questions` | List[dict] | Generated questions |
| `survey_answers` | List[dict] | Accumulated answers |
| `survey_complete` | bool | All questions answered |
| `phase` | str | `onboarding` or `graph_ready` |
| `db_path_id` | str | Supabase `learning_paths.id` UUID |
| `swarm_*` | various | Content swarm state (cleared between runs) |

### 6.3 ProfileBuilder Node

**Model:** Gemini 2.5 Flash  
**Input:** `learning_goal`  
**Output:** `survey_questions` (5–8 prerequisite topics)

Prompts Gemini to identify prerequisite topics for the learning goal and generate a self-assessment question per topic. Outputs strict JSON; uses regex fallback parsing if Gemini wraps in markdown fences.

### 6.4 CurriculumPlanner Node

**Model:** Gemini 2.5 Flash  
**Input:** `learning_goal`, `skill_ratings`  
**Output:** `curriculum_graph` (DAG of learning nodes)

1. Checks Pinecone `curriculum_cache` namespace for a semantically similar goal (threshold: cosine > 0.92). On cache hit, reuses the graph.
2. On cache miss, prompts Gemini to generate a full DAG with 10–20 nodes across 2–4 sections.
3. Auto-marks nodes as `completed` where `skill_ratings[topic] >= 4`.
4. Computes `available` nodes (all prerequisites are in `completed` set).
5. Builds ReactFlow `edges` array.
6. Asynchronously saves new graph to Pinecone cache (`asyncio.create_task`).

### 6.5 ErrorHandler Node

Routes errors:
- `replan_storm` (too many retries) → END
- Other errors → retry `curriculum_planner`

### 6.6 MemoryConsolidator

Called as a FastAPI background task on `POST /agent/end`:
1. Generates a 2–3 sentence session summary (Gemini)
2. Saves to Supabase `sessions` table
3. Embeds summary and upserts to Pinecone `user_memory_{user_id}` namespace

### 6.7 LLM Key Rotation (`LlmFactory`)

```python
# Round-robin rotation across comma-separated keys
GEMINI_KEYS="key1,key2,key3"
GROQ_KEYS="key1,key2"
```

- `safe_ainvoke_gemini(chain_builder_func, prompt_vars, max_attempts=4)` — tries up to 4 keys
- `safe_ainvoke_groq(chain_builder_func, prompt_vars, max_attempts=4)` — same for Groq
- Parses exact wait time from 429 error message ("retry in Xs") for precise backoff
- On 503/unavailable: 3s fixed backoff

---

## 7. Content Swarm Architecture

The Content Swarm is a **separate LangGraph sub-graph** (`swarm_graph`) invoked on-demand when a user clicks "Generate Resources" for a node.

### 7.1 Swarm Graph Flow

```
[swarm_graph.ainvoke({current_topic: "Python Basics", ...})]

query_generator
   │  (Groq: generates 3 search queries)
   ▼
   ├── practical_worker  (web search for tutorials)
   ├── academic_worker   (academic paper search)
   └── multimedia_worker (YouTube search + transcript)
           │
           ▼ (all results accumulated in swarm_raw_results via `add` reducer)
        synthesizer
        │  (Groq: picks best 3–5 resources, writes summary)
        ▼
   vector_ingestion_gate
   │  (no LLM: persists to Pinecone + Supabase)
   ▼
  [END]
```

> **Note:** LangGraph does NOT automatically parallelize the three workers. They run sequentially; the `Annotated[List, operator.add]` reducer on `swarm_raw_results` accumulates all results as they stream in.

### 7.2 Swarm Nodes Detail

#### QueryGenerator
- **Model:** Groq llama-3.3-70b
- **Input:** `current_topic`
- **Output:** `swarm_queries` — 3 `SwarmQuery` objects `{engine: "web"|"academic"|"video", query: str}`

#### PracticalWorker
- Picks the `web` engine query
- Searches web for tutorials, documentation, guides
- Returns `SwarmWorkerResult {source_type, raw_text, source_url, title, metadata}`

#### AcademicWorker
- Picks the `academic` engine query
- Searches academic databases / research resources
- Returns `SwarmWorkerResult`

#### MultimediaWorker
- Picks the `video` engine query
- Calls **YouTube Data API v3** to search for relevant videos
- Extracts transcript using `youtube-transcript-api` (English preferred, fallback to translated)
- Caps transcript to first 50 lines
- Returns `SwarmWorkerResult` with transcript excerpt

#### Synthesizer
- **Model:** Groq llama-3.3-70b
- **Input:** `current_topic`, `swarm_raw_results` (up to 8 sources, 600 chars each)
- **Output:** `node_resources_output` = `{summary: str, resources: [{type, title, url, why_relevant}]}`
- Strict: only uses URLs that actually appeared in the gathered content

#### VectorIngestionGate
- **No LLM call** — purely programmatic persistence
- Calls `RAGService.save_node_resources()` which:
  1. Embeds combined text (title + description + resource titles + questions) → upserts to Pinecone `node_content` namespace
  2. Updates `path_nodes.resources_cached` and `path_nodes.questions_cached` for this user's thread

---

## 8. RAG & Caching Strategy

### 8.1 Node Resource Cache (3-layer)

```
Request: GET node resources for "python-basics"
         │
         ▼
Layer 1: Supabase DB `node_resources` table (exact slug match)
         │ HIT → return instantly (< 50ms)
         │ MISS ↓
         ▼
Layer 2: Pinecone `node_content` namespace
         similarity search on "{title} {description}"
         threshold: cosine score > 0.88
         │ HIT → return (< 200ms)
         │ MISS ↓
         ▼
Layer 3: Content Swarm (30–60 seconds)
         run all workers → synthesize → persist to Layers 1 & 2
```

### 8.2 Curriculum Cache

```
Request: Generate curriculum for "Learn Machine Learning"
         │
         ▼
Pinecone `curriculum_cache` namespace
semantic similarity on learning goal text
threshold: cosine score > 0.92
         │ HIT → return instantly, re-apply skill ratings
         │ MISS ↓
         ▼
Gemini CurriculumPlanner → generates fresh DAG
After generation: async save to Pinecone `curriculum_cache`
```

**Pinecone metadata limit:** Graphs > 38KB are stored as summary-only (goal + section_titles + node slugs without descriptions).

### 8.3 User Memory (Semantic)

Each user has a dedicated Pinecone namespace: `user_memory_{user_id}`  
Stores session summaries as vector embeddings for future retrieval-augmented personalization.

---

## 9. Frontend Architecture

### 9.1 Auth Flow

```
main.jsx
  └── <AuthContext.Provider>   (user, session, signOut)
        └── <App>
              ├── if !user → <Auth />  (Supabase email/password)
              └── if user → Main layout
```

`AuthContext.jsx` wraps `supabase.auth.onAuthStateChange()`. The `session.access_token` (Supabase JWT) is passed to all API calls as `Authorization: Bearer`.

### 9.2 State Architecture

**Primary state:** `useLearningPath` hook manages all AI session state:

| State | Description |
|---|---|
| `phase` | `idle` → `starting` → `survey` → `generating` → `graph_ready` → `error` |
| `surveyQuestion` | Current question object `{topic, question}` |
| `surveyProgress` | `{answered, total}` |
| `curriculumGraph` | Full graph `{nodes, edges, goal, section_titles}` |
| `threadId` | Current LangGraph thread ID |

**Path history:** Stored in `App.jsx` local state (`paths`, `activePath`). Fetched from Go backend.

**Selected node:** `App.jsx` local state (`selectedNode`). Passed to `NodeDetailPanel`.

### 9.3 SSE Stream Reading

`useLearningPath.js` implements a generic `readSSEStream(response, onPayload)` that:
1. Uses `response.body.getReader()` and `TextDecoder`
2. Buffers chunks, splits on `\n\n`
3. Strips `data: ` prefix, JSON-parses each message
4. Dispatches to `onPayload(data)` callback

### 9.4 Graph Canvas (`GraphCanvas.jsx`)

Uses `@xyflow/react` with:
- **Custom node component** (`CustomNode.jsx`) styled by `status` prop
- Auto-layout via dagre or manual positioning by `section_number`
- `onNodeClick` callback → sets `selectedNode` in App

### 9.5 Node Detail Panel (`NodeDetailPanel.jsx`)

On `node` prop change:
1. Immediately checks Go backend for cached resources (`GET .../nodes/{nodeId}`)
2. If `resources_cached` exists → renders resources
3. If `is_major=true` and no cache → shows "Generate Resources" button
4. On generate: streams from Go's SSE proxy → listens for `ready` event → re-fetches resources

---

## 10. Data Flow Diagrams

### 10.1 New Learning Path — Full Flow

```
User types goal → [Enter]
│
│ 1. Frontend generates thread_id = `thread-{Date.now()}-{random}`
│
│ 2. POST /api/v1/agent/start (Python, SSE)
│    → ProfileBuilder runs (Gemini)
│    → survey_questions generated
│    → SSE: execution_complete {phase: "onboarding", survey_question}
│
│ 3. Frontend renders survey questions (one at a time)
│
│ 4. User clicks rating → POST /api/v1/agent/survey-answer (Python)
│    → State updated in LangGraph checkpoint
│    → Response: next_question OR survey_complete
│    (Repeat for all questions)
│
│ 5. Last answer: survey_complete=true
│    Frontend sets phase="generating"
│
│ 6. POST /api/v1/agent/generate-curriculum (Python, SSE)
│    → CurriculumPlanner runs (Gemini)
│    → Checks Pinecone curriculum_cache
│    → Generates DAG if cache miss
│    → SSE: execution_complete {phase: "graph_ready", curriculum_graph}
│    → After SSE: saves learning_path + all path_nodes to Supabase
│
│ 7. Frontend renders ReactFlow graph
│    Graph updates in path history sidebar
```

### 10.2 Node Completion — Full Flow

```
User clicks "Mark as Completed" on NodeDetailPanel
│
│ 1. POST .../nodes/{nodeId}/complete (Go backend)
│    a. Fetches learning_path (with curriculum_graph + completed_node_ids) from Supabase
│    b. Updates path_nodes row: status="completed", completed_at=now
│    c. Adds nodeId to completed_node_ids
│    d. Re-computes which locked nodes → available (prerequisite check)
│    e. Updates curriculum_graph.nodes statuses
│    f. PATCH learning_paths: new completed_node_ids + curriculum_graph
│    g. Returns {success, curriculum_graph}
│
│ 2. Frontend calls onMarkComplete(newGraph)
│    useLearningPath.updateGraph(newGraph)
│    ReactFlow canvas re-renders with updated statuses
```

---

## 11. Environment Variables Reference

### Python Backend (`backend/.env`)

| Variable | Required | Description |
|---|---|---|
| `SUPABASE_URL` | ✅ | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | ✅ | Supabase service role key (bypasses RLS) |
| `GEMINI_KEYS` | ✅ | Comma-separated Google AI API keys |
| `GROQ_KEYS` | ✅ | Comma-separated Groq API keys |
| `PINECONE_API_KEY` | ✅ | Pinecone API key |
| `PINECONE_HOST` | ✅ | Pinecone index host URL |
| `PINECONE_INDEX` | ✅ | Pinecone index name |
| `YOUTUBE_API_KEY` | ✅ | YouTube Data API v3 key |
| `CORS_ORIGINS` | ❌ | Allowed origins (default: localhost:3000,5173) |

### Go Backend (`go-backend/.env`)

| Variable | Required | Description |
|---|---|---|
| `SUPABASE_URL` | ✅ | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | ✅ | Supabase service role key |
| `PYTHON_BACKEND_URL` | ✅ | Python backend URL (default: http://localhost:8000) |
| `PORT` | ❌ | Port to listen on (default: 4000) |

### Frontend (`frontend/.env`)

| Variable | Required | Description |
|---|---|---|
| `VITE_SUPABASE_URL` | ✅ | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | ✅ | Supabase anon/public key |
| `VITE_API_BASE_URL` | ✅ | Go backend URL (default: http://localhost:4000) |
| `VITE_AI_API_BASE_URL` | ✅ | Python backend URL (default: http://localhost:8000) |

---

## 12. Deployment Guide

### 12.1 Database Setup (Supabase)

Run migrations in order in Supabase SQL Editor:

1. `supabase/migrations/20260621000000_initial_schema.sql` — base tables
2. `supabase/migrations/20260621100000_complete_schema.sql` — complete schema
3. `supabase/migrations/20260621170000_learning_paths_schema.sql` — learning paths + nodes + survey + cache
4. `supabase/migrations/20260621170100_drop_legacy_tables.sql` — clean up old tables
5. `supabase/migrations/20260622000000_add_questions_to_node_resources.sql` — questions column
6. `supabase/migrations/20260622000001_node_content_hierarchy.sql` — content hierarchy

### 12.2 Pinecone Setup

Create a Pinecone index with:
- **Dimensions:** 1536 (for `text-embedding-ada-002`) or matching your embedding model
- **Metric:** cosine

The following namespaces are created automatically on first write:
- `node_content` — node resources cache
- `curriculum_cache` — curriculum graph cache
- `user_memory_{uid}` — per-user session memory

### 12.3 Deploy to Render (Backends)

The `render.yaml` at the repo root defines both backend services:

```yaml
services:
  - type: web
    name: go-backend
    env: go
    rootDir: go-backend
    buildCommand: go build -o main
    startCommand: ./main
    plan: free

  - type: web
    name: python-backend
    env: python
    rootDir: backend
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    plan: free
```

Steps:
1. Connect GitHub repo to Render
2. Select "Blueprint" to read `render.yaml`
3. Set environment variables for each service via Render dashboard

### 12.4 Deploy Frontend to Vercel

1. Connect GitHub repo to Vercel
2. Set **Root Directory:** `frontend`
3. Set environment variables:
   - `VITE_SUPABASE_URL`
   - `VITE_SUPABASE_ANON_KEY`
   - `VITE_API_BASE_URL` → Render Go backend URL
   - `VITE_AI_API_BASE_URL` → Render Python backend URL

---

## 13. Local Development Setup

### Prerequisites
- Node.js v18+
- Go v1.21+
- Python v3.11+

### Step 1: Database
Run Supabase migrations (see §12.1) against your Supabase project.

### Step 2: Python Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

Create `backend/.env` with required variables (see §11).

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Swagger UI: http://localhost:8000/docs

### Step 3: Go Backend
```bash
cd go-backend
go mod tidy
```

Create `go-backend/.env` with required variables.

```bash
go run main.go
```

### Step 4: Frontend
```bash
cd frontend
npm install
```

Create `frontend/.env` with required variables.

```bash
npm run dev
```

App: http://localhost:5173

### Step 5: Verify
1. Open http://localhost:5173
2. Sign up with email/password
3. Type a learning goal in the chat bar
4. Complete the survey
5. Verify the graph renders
6. Click a node → check resources load

---

## Appendix A: JSON Parsing Strategy

Both ProfileBuilder and CurriculumPlanner use a robust 3-step JSON extraction strategy because Gemini may wrap output in markdown code fences:

```python
# Step 1: Strip markdown fences
clean = re.sub(r"```(?:json)?\s*", "", raw_text).strip().rstrip("`").strip()

# Step 2: Direct parse
try:
    data = json.loads(clean)
except json.JSONDecodeError:
    pass

# Step 3: Regex extraction of outermost JSON object
if data is None:
    match = re.search(r'\{[\s\S]*\}', clean)
    if match:
        try:
            data = json.loads(match.group())
        ...

# Step 4: Pydantic validation (type coercion, NOT sent to Gemini as schema)
result = LearningGraphOutput.model_validate(data)
```

> **Why not `with_structured_output`?** Gemini rejects complex nested Pydantic schemas with `INVALID_ARGUMENT: too many constraint states`. Manual JSON parsing with Pydantic validation-only is the current workaround.

---

## Appendix B: Node Status State Machine

```
         [created]
              │
              ▼
           "locked"
              │
    (all prerequisites completed)
              │
              ▼
          "available"
              │
        (user clicks)
              │
              ▼
         "in_progress"  (planned, not yet enforced)
              │
        (user marks complete)
              │
              ▼
          "completed"
```

Status transitions are computed **in the Go backend** on `POST .../complete`, not by the AI layer. This ensures consistency and fast response times without LLM involvement.

---

## Appendix C: Thread ID Format

Thread IDs are generated client-side by the frontend:

```js
const newThreadId = `thread-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
// Example: "thread-1719200000000-abc12"
```

This ID is the primary key linking:
- LangGraph in-memory checkpoint (`configurable.thread_id`)
- Supabase `learning_paths.thread_id` (UNIQUE)
- All API calls between frontend, Go, and Python backends
