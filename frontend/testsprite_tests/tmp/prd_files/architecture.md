# PathMind AI — System Architecture (Authoritative Reference)

> **Status**: 2026-06-22  
> **Architecture**: Two-Backend Microservice  
> This document is the **single source of truth** for how the system works.

---

## 1. What This System Does

PathMind AI is a **personalised learning path generator**. A user tells it their learning goal (e.g. "Learn Machine Learning"), rates their existing knowledge across prerequisite topics, and receives a **visual directed acyclic graph (DAG)** of everything they need to study. Each node in the graph is a topic. Clicking a node shows a description and 3–5 curated resources (YouTube video, web article, arXiv paper).

The user marks nodes as completed → downstream nodes unlock → repeat until done.

```
User
 │
 ├─ Enters learning goal ("I want to learn Rust")
 │
 ├─ Rates prerequisite knowledge 0–5 per topic (self-assessment survey)
 │
 ├─ Receives a visual DAG (10–20 nodes, 2–4 sections)
 │   Nodes: locked | available | completed
 │   Edges: prerequisite arrows (animated when target is available)
 │
 ├─ Clicks any available node
 │   └─ Slide-in panel: 2–3 sentence description + 3–5 curated resources
 │
 └─ Marks node as completed → next nodes unlock
```

---

## 2. Technology Stack

| Layer | Technology | Role |
|---|---|---|
| **Frontend** | React 18 + Vite + React Flow (`@xyflow/react`) | UI, graph rendering, SSE stream reader |
| **Auth** | Supabase Auth (JWT) | Login, signup, token verification |
| **State & CRUD API** | Go (Gin/stdlib) — Port 4000 | Path history, node completion, SSE proxy to Python |
| **AI Engine API** | Python FastAPI + Uvicorn — Port 8000 | LangGraph orchestration, LLM calls, swarm |
| **LLM (generation)** | Google Gemini 2.5 Flash | Survey generation, curriculum planning, session summary |
| **LLM (synthesis)** | Groq (Llama 3 70B) | Resource synthesis in the content swarm |
| **Embeddings** | Google `gemini-embedding-001` (768-dim) | Embedding text for Pinecone storage and lookup |
| **Primary DB** | PostgreSQL via Supabase | All relational data (paths, nodes, surveys, sessions) |
| **Vector DB** | Pinecone | Three namespaces for caching (see §5) |
| **Graph Checkpoint** | LangGraph `MemorySaver` (in-process) | Holds LangGraph thread state in RAM during a session |
| **Web Search** | Tavily API | Fetches web tutorials and articles in the swarm |
| **Academic Search** | arXiv Python client | Fetches research paper abstracts in the swarm |
| **Video Search** | YouTube Data API v3 + `youtube-transcript-api` | Fetches video metadata + transcript in the swarm |
| **Observability** | LangSmith | LangGraph trace logging |

> **Note on Redis**: Redis was evaluated as a persistent checkpointer for LangGraph sessions but is **not used**. The current `MemorySaver` holds session state in RAM. This means restarting the Python backend loses all active in-flight sessions (users mid-survey). This is acceptable for the current development stage.

---

## 3. Repository Structure

```
PersonalizeLearning/
│
├── frontend/                       React + Vite SPA
│   └── src/
│       ├── App.jsx                 Root layout (2-panel: sidebar + graph)
│       ├── App.css                 Node styles, panel CSS, animations
│       ├── index.css               Global design tokens (colors, glass, fonts)
│       ├── supabaseClient.js       Supabase JS client (anon key)
│       ├── context/
│       │   └── AuthContext.jsx     Global Supabase auth state (user, signOut)
│       ├── hooks/
│       │   └── useLearningPath.js  Full session lifecycle (API calls, SSE reading)
│       └── components/
│           ├── Auth.jsx            Login / signup form
│           ├── OnboardingFlow.jsx  Profile setup (background, learning style)
│           ├── NewPathModal.jsx    Enter learning goal modal
│           ├── SurveyCard.jsx      0–5 rating card per prerequisite topic
│           ├── GraphCanvas.jsx     React Flow canvas (auto-layout)
│           ├── CustomNode.jsx      Individual node box (n8n-style)
│           ├── NodeDetailPanel.jsx Slide-in right panel (resources + questions)
│           └── PathHistorySidebar.jsx  Left sidebar (history + new path button)
│
├── go-backend/                     Go State & CRUD API (Port 4000)
│   ├── main.go                     All route handlers + Supabase client
│   └── .env                        Go-specific env vars
│
├── backend/                        Python AI Engine (Port 8000)
│   ├── .env                        Python-specific env vars
│   └── app/
│       ├── main.py                 FastAPI app entry point + CORS
│       ├── routes.py               All /api/v1/agent/* route handlers
│       ├── models.py               Pydantic request models
│       ├── api/
│       │   └── auth.py             JWT verification via Supabase
│       └── Agent/
│           ├── Graph.py            LangGraph parent graph (compile + edges)
│           ├── GraphService.py     Session lifecycle (start, survey, curriculum, end)
│           ├── LearnerState.py     TypedDict for all LangGraph state fields
│           ├── Nodes/
│           │   ├── ProfileBuilder.py     Node 1: generates survey questions via Gemini
│           │   ├── CurriculumPlanner.py  Node 2: generates DAG via Gemini
│           │   ├── ErrorHandler.py       Node 3: clears errors, decides retry vs. stop
│           │   └── MemoryConsolidator.py Background: summarises session to Supabase + Pinecone
│           ├── Tools/
│           │   ├── Database.py       Supabase wrapper (all SQL ops, asyncio.to_thread)
│           │   ├── VectorStore.py    Pinecone wrapper (embed + upsert + search)
│           │   ├── Embeddings.py     Google embedding model factory (key rotation)
│           │   ├── LlmFactory.py     Gemini + Groq key rotation + rate-limit retry
│           │   └── RAGService.py     Cache lookup/write logic (3 namespaces)
│           └── Swarm/
│               ├── SwarmGraph.py     Content swarm LangGraph sub-graph
│               └── Nodes/
│                   ├── QueryGenerator.py     Decomposes topic into 3 search queries (Groq)
│                   ├── PracticalWorker.py    Fetches web results via Tavily
│                   ├── AcademicWorker.py     Fetches arXiv abstracts
│                   ├── MultimediaWorker.py   Fetches YouTube transcript
│                   ├── Synthesizer.py        Curates 3–5 resources from raw results (Groq)
│                   └── VectorIngestionGate.py  Saves results to Pinecone + Supabase
│
└── architecture.md                 This file
```

---

## 4. The Two Backends: Who Does What

The system intentionally splits responsibilities between two backend services:

| Responsibility | Go Backend (Port 4000) | Python Backend (Port 8000) |
|---|---|---|
| Auth token verification | ✅ Yes | ✅ Yes (independently) |
| Path history (list all paths) | ✅ Yes | ❌ No |
| Fetch full curriculum graph | ✅ Yes (from Supabase) | ❌ No |
| Mark node as completed | ✅ Yes | ❌ No |
| Unlock downstream nodes | ✅ Yes | ❌ No |
| Fetch cached node resources | ✅ Yes (from Supabase) | ❌ No |
| SSE proxy to Python | ✅ Yes | — |
| Run ProfileBuilder (LangGraph) | ❌ No | ✅ Yes |
| Run CurriculumPlanner (LangGraph) | ❌ No | ✅ Yes |
| Run Content Swarm | ❌ No | ✅ Yes |
| Write to Pinecone | ❌ No | ✅ Yes |
| Call Gemini / Groq | ❌ No | ✅ Yes |

**Rule**: Go owns all reads and writes of persistent relational state. Python owns all LLM calls and AI orchestration.

---

## 5. Supabase Schema

### Tables

```sql
-- Managed by Supabase Auth (automatic)
auth.users (id UUID, email, created_at, ...)

-- Extended user profile (filled during onboarding)
user_profiles (
    id          UUID PRIMARY KEY REFERENCES auth.users(id),
    name        TEXT,
    background  TEXT,
    learning_goals  TEXT[],
    learning_style  TEXT,
    daily_time_budget_minutes INT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
)

-- One row per learning path (one path = one LangGraph thread)
learning_paths (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id       TEXT UNIQUE NOT NULL,       -- LangGraph thread_id (from frontend)
    user_id         UUID NOT NULL REFERENCES user_profiles(id),
    learning_goal   TEXT NOT NULL,
    skill_ratings   JSONB DEFAULT '{}',         -- { "Python": 3, "Statistics": 1 }
    curriculum_graph JSONB,                     -- Full { nodes: [...], edges: [...] }
    completed_node_ids  TEXT[] DEFAULT '{}',
    sections_generated  INT DEFAULT 0,
    phase           TEXT DEFAULT 'onboarding',  -- 'onboarding' | 'graph_ready'
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
)

-- One row per node per path (populated after CurriculumPlanner)
path_nodes (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    path_id           UUID NOT NULL REFERENCES learning_paths(id) ON DELETE CASCADE,
    user_id           UUID NOT NULL REFERENCES user_profiles(id),
    node_id           TEXT NOT NULL,            -- slug: "python-basics"
    title             TEXT NOT NULL,
    description       TEXT,
    section_number    INT,
    section_title     TEXT,
    difficulty        INT,                      -- 1–5
    estimated_minutes INT,
    is_major          BOOLEAN DEFAULT FALSE,
    prerequisites     TEXT[] DEFAULT '{}',      -- slugs of prerequisite nodes
    status            TEXT DEFAULT 'locked',    -- 'locked' | 'available' | 'completed'
    resources_cached  JSONB,                    -- populated by swarm: [{type, title, url, why_relevant}]
    questions_cached  JSONB,                    -- reserved for future use
    completed_at      TIMESTAMPTZ,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(path_id, node_id)
)

-- One row per survey answer per path
survey_responses (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    path_id     UUID NOT NULL REFERENCES learning_paths(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES user_profiles(id),
    topic       TEXT NOT NULL,
    question    TEXT NOT NULL,
    rating      INT NOT NULL CHECK (rating BETWEEN 0 AND 5),
    created_at  TIMESTAMPTZ DEFAULT NOW()
)

-- Global shared resource cache per node slug (cross-user)
node_resources (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_slug       TEXT UNIQUE NOT NULL,       -- "python-basics"
    title           TEXT NOT NULL,
    description     TEXT,
    resources       JSONB NOT NULL,             -- [{type, title, url, why_relevant}]
    questions       JSONB DEFAULT '[]',
    pinecone_ids    TEXT[] DEFAULT '{}',
    generated_at    TIMESTAMPTZ DEFAULT NOW()
)

-- Session log written by MemoryConsolidator on session end
sessions (
    id              UUID PRIMARY KEY,           -- = thread_id
    user_id         UUID REFERENCES user_profiles(id),
    summary         TEXT,                       -- Gemini-generated 2–3 sentence summary
    topics_covered  TEXT[],                     -- learning goals from this session
    ended_at        TIMESTAMPTZ
)
```

### Row-Level Security (RLS)

```sql
-- Users can only access their own paths and nodes
ALTER TABLE learning_paths ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own paths" ON learning_paths FOR ALL USING (auth.uid() = user_id);

ALTER TABLE path_nodes ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own nodes" ON path_nodes FOR ALL USING (auth.uid() = user_id);

ALTER TABLE survey_responses ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own surveys" ON survey_responses FOR ALL USING (auth.uid() = user_id);

-- node_resources is a shared cache: anyone can read, only service role can write
ALTER TABLE node_resources ENABLE ROW LEVEL SECURITY;
CREATE POLICY "public read resources" ON node_resources FOR SELECT USING (true);
```

---

## 6. Pinecone — The Three Namespaces

**Index**: `personalized-learning-agent` (768-dim vectors, cosine similarity)  
**Embedding model**: `gemini-embedding-001` via Google AI

```
pinecone-index: "personalized-learning-agent"
│
├── namespace: "curriculum_cache"
│   What's stored: embedding of a learning goal → full curriculum_graph JSON in metadata
│   Write: CurriculumPlanner saves after generating a new graph
│   Read:  CurriculumPlanner queries before calling Gemini
│   Hit threshold: cosine similarity > 0.92
│   Benefit: Second user with same/similar goal gets graph instantly (no Gemini call)
│   Size limit: Graphs > 38KB are stored as summary-only (slugs + titles, no descriptions)
│
├── namespace: "node_content"
│   What's stored: embedding of (title + description + resource titles) → resource JSON in metadata
│   Write: VectorIngestionGate saves after a swarm completes
│   Read:  RAGService queries before running a swarm for a node
│   Hit threshold: cosine > 0.88 AND node_slug in metadata must match exactly
│   Benefit: "Python Classes" resources fetched once; every subsequent user gets them instantly
│
└── namespace: "user_memory_{user_id}"
    What's stored: embedding of a session summary → session metadata
    Write: MemoryConsolidator writes on POST /agent/end
    Read:  NOT YET IMPLEMENTED — planned for future personalisation at session start
    Metadata: { session_id, learning_goal, nodes_done, nodes_total, timestamp }
```

---

## 7. How RAG Works End-to-End

RAG (Retrieval-Augmented Generation) in this system means: **before spending time/money generating content with an LLM, check if we already have it cached**.

There are two RAG lookups:

### 7a. Curriculum Cache (at `/agent/generate-curriculum`)

```
User finishes survey
        │
        ▼
RAGService.get_curriculum_cache(learning_goal)
        │
        ├─ Embed learning_goal → search Pinecone "curriculum_cache"
        ├─ cosine > 0.92?
        │       YES → return cached curriculum_graph dict
        │              (skip Gemini call entirely, ~10 second saving)
        │       NO  → call Gemini CurriculumPlanner → generate DAG
        │              → asyncio.create_task(save to Pinecone "curriculum_cache")
        │
        └─ Return curriculum_graph to GraphService → save to Supabase → stream to frontend
```

### 7b. Node Content Cache (at `/agent/generate-node`)

```
User clicks a node
        │
        ▼
RAGService.get_node_resources(node_slug, node_title, node_description)
        │
        ├─ STEP 1: Supabase `node_resources` table — exact slug match (SQL, fastest)
        │       HIT → return resources immediately
        │
        ├─ STEP 2: Pinecone "node_content" — vector similarity on title+description
        │       cosine > 0.88 AND slug matches → return resources
        │
        └─ MISS on both → run Content Swarm (see §8)
                │
                └─ On completion → VectorIngestionGate calls RAGService.save_node_resources()
                        ├─ Embed content → upsert to Pinecone "node_content"
                        └─ Update Supabase path_nodes row: { resources_cached, questions_cached }
                           (keyed by thread_id → looks up path_id → updates node row)
```

---

## 8. Content Swarm — How It Works

The Content Swarm is a LangGraph **sub-graph** compiled separately from the parent graph. It is invoked via `swarm_graph.ainvoke()` — not as a node in the parent graph.

### Swarm Graph Flow

```
                        ┌─────────────────────┐
                        │   query_generator   │  (Groq Llama 3.3 70B)
                        │                     │  Decomposes topic into
                        │  current_topic →    │  3 targeted queries:
                        │  3 x SwarmQuery     │  web / academic / video
                        └─────────────────────┘
                         /          |          \
              ┌──────────┐  ┌───────────┐  ┌──────────────┐
              │ practical │  │ academic  │  │  multimedia  │
              │  worker   │  │  worker   │  │   worker     │
              │  Tavily   │  │  arXiv    │  │ YouTube API  │
              │  web srch │  │  papers   │  │ + transcript │
              └──────────┘  └───────────┘  └──────────────┘
                  Results appended to swarm_raw_results via operator.add reducer
                         \          |          /
                        ┌─────────────────────┐
                        │     synthesizer     │  (Groq Llama 3 70B)
                        │                     │  Reads raw results,
                        │  raw_results →      │  picks 3–5 best URLs,
                        │  NodeResourceOutput │  writes 2–3 sentence summary
                        └─────────────────────┘
                                  │
                        ┌─────────────────────┐
                        │ vector_ingestion    │  (No LLM — programmatic only)
                        │      gate           │  Saves to Pinecone + Supabase
                        └─────────────────────┘
                                  │
                                 END
```

> **Important**: The three workers (practical, academic, multimedia) run **sequentially**, not truly in parallel. LangGraph does not automatically parallelise branches in this configuration. The `operator.add` reducer on `swarm_raw_results` accumulates results across the three sequential runs.

### Worker Details

| Worker | API Used | Output |
|---|---|---|
| `PracticalWorker` | Tavily Search API (`max_results=2`) | Web articles and tutorials |
| `AcademicWorker` | arXiv client (`max_results=2`, sorted by relevance) | Paper title + abstract |
| `MultimediaWorker` | YouTube Data API v3 (search) + `youtube-transcript-api` (transcript) | Video title + first 50 lines of transcript |

### Failure Handling in Workers

Each worker is wrapped in `try/except`. If a worker fails (rate limit, no results, transcript unavailable), it returns `{"swarm_raw_results": []}` and logs a warning. The swarm continues with fewer sources — graceful degradation.

The Synthesizer (`node_resources_output`) will then have fewer inputs but still produces a valid output.

---

## 9. LangGraph Parent Graph

### Graph Structure

```
START
  │
  ▼
profile_builder  (Gemini 2.5 Flash)
  │  Reads user profile from Supabase
  │  Generates 5–8 self-assessment survey questions
  │
  ├─ error → error_handler
  │
  ├─ survey_complete=False → END
  │     (graph pauses here. Frontend shows survey.
  │      Answers arrive via POST /agent/survey-answer
  │      which calls GraphService.update_state() — no graph resumption.
  │      When all answers are collected, frontend calls
  │      POST /agent/generate-curriculum to resume.)
  │
  └─ survey_complete=True → curriculum_planner
          │
          │  (Gemini 2.5 Flash)
          │  Checks Pinecone curriculum cache first
          │  If miss: generates full DAG JSON
          │  Auto-completes nodes for topics user rated ≥ 4
          │  Computes "available" nodes (all prerequisites completed)
          │  Saves curriculum_graph to Supabase (async)
          │
          ├─ error → error_handler
          │               │
          │               ├─ reason="replan_storm" → END (stop)
          │               └─ default → curriculum_planner (retry)
          │
          └─ success → END (phase="graph_ready")
```

### Checkpointer

```python
memory = MemorySaver()           # In-process RAM only
app_graph = workflow.compile(checkpointer=memory)
```

Each LangGraph thread is identified by `thread_id` (a UUID the frontend generates and sends with every request). The checkpointer stores the full `LearnerState` snapshot after each node runs, so the graph can be resumed mid-flow.

**Limitation**: Restarting the Python process wipes all in-memory checkpoints. Active sessions (e.g., users mid-survey) are lost.

---

## 10. LearnerState — Complete Field Reference

```python
class LearnerState(TypedDict):

    # ── Identity ──────────────────────────────────────────────────────────
    user_id: str            # Supabase auth UUID
    session_id: str         # = thread_id from frontend (LangGraph checkpoint key)

    # ── User Profile ──────────────────────────────────────────────────────
    user_profile: dict      # {id, name, background, learning_style, daily_time_budget_minutes}
    skill_ratings: dict     # {"Python": 3, "Statistics": 1, ...} built from survey answers
    learning_goal: str      # "Learn Machine Learning"

    # ── Curriculum Graph ──────────────────────────────────────────────────
    curriculum_graph: dict  # {goal, section_titles, nodes: [LearningNode], edges: [...]}
    sections_generated: int # number of sections in the graph
    current_section: int    # which section user is on (not actively used)
    completed_node_ids: List[str]  # slugs of nodes marked completed
    active_node_id: str | None     # slug of last clicked node (not actively used)

    # ── Survey State (onboarding only) ────────────────────────────────────
    survey_questions: List[dict]   # [{topic, question, index}]
    survey_answers: List[dict]     # [{topic, rating, question}]
    survey_complete: bool

    # ── Dialogue (populated on /agent/start) ──────────────────────────────
    conversation_history: Annotated[list[dict], operator.add]  # append-only
    last_user_message: str         # initial_prompt from /agent/start

    # ── Phase Routing ─────────────────────────────────────────────────────
    phase: str              # "onboarding" | "graph_ready"
    session_complete: bool  # set True by /agent/end
    error: str              # non-empty string causes routing to error_handler
    loop_counters: dict     # tracks retry counts to prevent infinite loops
    error_context: dict | None  # {"reason": "replan_storm"} etc.

    # ── Content Swarm (swarm sub-graph state) ────────────────────────────
    swarm_queries: List[SwarmQuery]          # [{engine, query}] from QueryGenerator
    swarm_raw_results: Annotated[List[SwarmWorkerResult], operator.add]  # accumulated by workers
    content_module: str          # 2–3 sentence summary from Synthesizer
    node_resources_output: dict  # {summary, resources, questions} from Synthesizer
    current_topic: str           # title of node being fetched by swarm

    # ── Persistence ───────────────────────────────────────────────────────
    db_path_id: str              # Supabase learning_paths.id UUID for this session

    # ── Meta ──────────────────────────────────────────────────────────────
    total_sessions: int
    flags: dict[str, Any]
```

---

## 11. LearningNode Schema (within `curriculum_graph.nodes`)

```python
{
    "id":                "python-basics",          # URL-safe slug (lowercase + hyphens)
    "title":             "Python Basics",          # Human-readable
    "description":       "1–2 sentence summary",
    "prerequisites":     ["intro-to-programming"], # list of node slugs
    "difficulty":        1,                        # 1–5
    "estimated_minutes": 30,
    "section":           "Section 1: Foundations", # full section title
    "section_number":    1,
    "is_major":          True,                     # True → content swarm runs on first click
    "status":            "available"               # "locked" | "available" | "completed"
}
```

Edge schema (stored in `curriculum_graph.edges`):
```python
{
    "id":       "e-intro-to-programming-python-basics",
    "source":   "intro-to-programming",
    "target":   "python-basics",
    "type":     "smoothstep",
    "animated": True    # True when target node status == "available"
}
```

---

## 12. API Reference

### Authentication

All Python backend endpoints require `Authorization: Bearer <supabase_access_token>`.  
The `get_current_user` FastAPI dependency verifies the JWT via `supabase.auth.get_user(token)`.  
The Go backend independently verifies tokens using the same Supabase service key.

---

### Go Backend — Port 4000

Handles all relational state reads and writes. Proxies node content generation to Python.

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/users/:userId/conversations` | List all learning paths for the user (history sidebar) |
| `GET` | `/api/v1/users/:userId/conversations/:conversationId` | Get full curriculum graph for a path |
| `GET` | `/api/v1/users/:userId/conversations/:conversationId/nodes/:nodeId` | Get cached resources for a node from `path_nodes.resources_cached` |
| `GET` | `/api/v1/users/:userId/conversations/:conversationId/nodes/:nodeId/generate` | Gather node context from Supabase → call Python `/agent/generate-node` → proxy SSE stream |
| `POST` | `/api/v1/users/:userId/conversations/:conversationId/nodes/:nodeId/complete` | Mark node completed, recalculate unlocked nodes, return updated graph |

---

### Python Backend — Port 8000

Handles all LLM orchestration, LangGraph, and vector DB operations.

| Method | Path | Auth | Body | Returns |
|---|---|---|---|---|
| `POST` | `/api/v1/agent/start` | JWT | `{thread_id, initial_prompt}` | SSE stream: `connection_established` → `node_update` → `execution_complete {phase, survey_question}` |
| `POST` | `/api/v1/agent/survey-answer` | JWT | `{thread_id, topic, rating}` | JSON: `{next_question, progress}` or `{survey_complete: true}` |
| `POST` | `/api/v1/agent/generate-curriculum` | JWT | `{thread_id}` | SSE stream → `execution_complete {phase: "graph_ready", curriculum_graph}` |
| `POST` | `/api/v1/agent/generate-node` | JWT | `{node_id, thread_id, title, description, learning_goal}` | SSE stream: `status` → `ready {source}` or `error` |
| `POST` | `/api/v1/agent/end` | JWT | `{thread_id}` | JSON `{status: "success"}` — triggers background memory consolidation |
| `GET` | `/health` | None | — | `{status: "ok"}` |

---

## 13. Session Lifecycle — Complete End-to-End

```
1. AUTHENTICATION
   Frontend → Supabase Auth (email/password or OAuth)
   Receives: access_token (JWT)

2. ONBOARDING SURVEY
   Frontend → POST Python:8000/api/v1/agent/start
              Body: { thread_id: <uuid>, initial_prompt: "Learn Rust" }
   Python:  → Creates stub row in Supabase `learning_paths` (phase: "onboarding")
            → Runs LangGraph: profile_builder
              ProfileBuilder reads user profile from Supabase
              Calls Gemini to generate 5–8 survey questions
            → Graph pauses (returns END)
            → SSE stream returns: { phase: "onboarding", survey_question: {topic, question} }

3. SURVEY ANSWERS (one request per question)
   Frontend → POST Python:8000/api/v1/agent/survey-answer
              Body: { thread_id, topic: "Python", rating: 3 }
   Python:  → GraphService.update_state() appends answer to LangGraph state
            → Writes answer to Supabase `survey_responses`
            → Returns: { next_question } or { survey_complete: true }
   (Repeat for each question — no graph resumption between answers)

4. CURRICULUM GENERATION
   Frontend → POST Python:8000/api/v1/agent/generate-curriculum
              Body: { thread_id }
   Python:  → Resumes LangGraph graph
            → curriculum_planner runs:
                1. Check Pinecone "curriculum_cache" (cosine > 0.92 = HIT → skip LLM)
                2. If miss: call Gemini to generate full DAG JSON
                3. Auto-complete nodes user rated ≥ 4
                4. Compute "available" nodes (prerequisites met)
                5. Save to Pinecone "curriculum_cache" (async background task)
            → After stream ends: upsert `learning_paths` + bulk insert `path_nodes`
            → SSE returns: { phase: "graph_ready", curriculum_graph: {...} }
   Frontend stores curriculum_graph in React state and renders React Flow canvas.

5. LOADING HISTORY
   Frontend → GET Go:4000/api/v1/users/:userId/conversations
   Go:      → Queries Supabase `learning_paths` for all user paths
            → Returns list: [{ id, thread_id, learning_goal, phase, created_at }]

6. NODE CLICK — RESOURCE GENERATION
   Frontend → GET Go:4000/.../nodes/:nodeId/generate
   Go:      → Fetches node title + description + learning_goal from Supabase
            → Calls POST Python:8000/api/v1/agent/generate-node
              Body: { node_id, thread_id, title, description, learning_goal }
   Python:  → RAGService.get_node_resources():
                1. Check Supabase `node_resources` (exact slug — fastest)
                2. Check Pinecone "node_content" (cosine > 0.88 + slug match)
                3. MISS: run Content Swarm (QueryGenerator → 3 workers → Synthesizer)
            → After swarm: VectorIngestionGate saves to Pinecone + path_nodes row
            → SSE: { type: "ready", source: "swarm"|"pinecone_cache"|"db_cache" }
   Go:      → Proxies SSE stream to Frontend
   Frontend → Reads from Go:4000/.../nodes/:nodeId to display resources in panel

7. NODE COMPLETION
   Frontend → POST Go:4000/.../nodes/:nodeId/complete
   Go:      → Updates `path_nodes` row: status = "completed", completed_at = now()
            → Recalculates which nodes are now "available" (prerequisites met)
            → Returns updated curriculum_graph
   Frontend re-renders graph with newly unlocked nodes.

8. SESSION END (Background Memory Consolidation)
   Frontend → POST Python:8000/api/v1/agent/end { thread_id }
   Python:  → Returns 200 immediately
            → Background task: GraphService.end_session()
                → await MemoryConsolidator.consolidate_session()
                  1. Call Gemini to write 2–3 sentence session summary
                  2. Write to Supabase `sessions` table
                  3. Upsert summary embedding to Pinecone "user_memory_{user_id}"
                → Update LangGraph state: { session_complete: True }
```

---

## 14. Key Decisions & Rationale

### Why Two Backends?
Python is the only language with a mature LangGraph SDK. Go provides significantly better throughput and simpler deployment for high-frequency CRUD operations (path history, node completion). Keeping them separate means the slow AI engine never blocks fast data reads.

### Why No Redis?
The `MemorySaver` is sufficient for the current development stage where a single Python process runs. Redis would add operational complexity (connection management, serialisation) without a proportional benefit until the system needs to run multiple Python workers or survive restarts without losing sessions.

### Why Groq for the Swarm (Not Gemini)?
The swarm runs three workers then a synthesizer, back-to-back. Gemini's free-tier rate limits would be hit immediately. Groq provides significantly higher free-tier token throughput for the Llama models, making the swarm reliable without introducing billing.

### Why Manual JSON Parsing (Not `with_structured_output`)?
Gemini's structured output API rejects complex nested Pydantic schemas with `INVALID_ARGUMENT: too many constraint states`. We prompt for raw JSON, strip markdown fences with regex, parse with `json.loads`, then validate with Pydantic — giving us both reliability and type safety.

### Why is `is_major` Only ~30% of Nodes?
Running the full swarm (Tavily + arXiv + YouTube + Groq synthesis) for every node on every click would be slow and expensive. Minor nodes serve their purpose with just the description from the curriculum graph. The user only wants deep resources for the important, complex topics.

---

## 15. Environment Variables Reference

### Python Backend (`backend/.env`)

| Variable | Used By | Purpose |
|---|---|---|
| `GEMINI_KEYS` | `LlmFactory`, `Embeddings` | Comma-separated Gemini API keys (rotated on rate limit) |
| `GROQ_KEYS` | `LlmFactory` | Comma-separated Groq API keys (rotated on rate limit) |
| `PINECONE_API_KEY` | `VectorStore` | Pinecone index access |
| `PINECONE_INDEX_NAME` | `VectorStore` | Index name (`personalized-learning-agent`) |
| `SUPABASE_URL` | `Database`, `auth.py` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | `Database`, `auth.py` | Service role key (bypasses RLS for server-side writes) |
| `TAVILY_API_KEY` | `PracticalWorker` | Web search API |
| `YOUTUBE_API_KEY` | `MultimediaWorker` | YouTube Data API v3 |
| `PISTON_API_URL` | _(unused, reserved)_ | Code execution sandbox |
| `LANGCHAIN_TRACING_V2` | LangSmith | Enable trace logging |
| `LANGCHAIN_API_KEY` | LangSmith | LangSmith auth |
| `LANGCHAIN_PROJECT` | LangSmith | Project name in LangSmith dashboard |
| `CORS_ORIGINS` | `main.py` | Allowed origins (comma-separated) |

### Go Backend (`go-backend/.env`)

| Variable | Purpose |
|---|---|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Service role key |
| `PYTHON_BACKEND_URL` | Python backend base URL for proxying (e.g. `http://localhost:8000`) |
| `PORT` | Go server port (default `4000`) |
