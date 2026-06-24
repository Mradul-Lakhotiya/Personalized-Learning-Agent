# PathMind AI — Product Requirements Document (PRD)

**Product Name:** PathMind AI  
**Codename:** Personalized Learning Agent  
**Version:** 1.0  
**Document Date:** June 24, 2026  
**Status:** Active Development

---

## 1. Executive Summary

PathMind AI is an adaptive, AI-driven learning platform that dynamically generates personalized curriculum roadmaps for any subject a learner specifies. Unlike static course platforms, PathMind AI conducts a quick self-assessment survey, builds a skill-adaptive Directed Acyclic Graph (DAG) of topics, and—on demand—deploys a multi-agent "Swarm" to scour the web, YouTube, and academic databases to curate the most relevant resources for each topic node. Learners progress through an interactive visual graph, marking nodes complete to unlock dependent topics.

---

## 2. Problem Statement

### 2.1 The Core Problem
Existing learning platforms (MOOCs, YouTube playlists, textbooks) are static and one-size-fits-all. A learner who already knows Python fundamentals but wants to learn Machine Learning is forced to slog through beginner Python content they already know, or manually curate their own roadmap—a time-consuming and expertise-intensive task.

### 2.2 Pain Points
| Pain Point | Impact |
|---|---|
| No prior knowledge detection | Learners waste time on already-known content |
| Static, generic curriculums | Not adapted to individual goals or backgrounds |
| Resource quality varies | Hard to find the *best* resource for each specific topic |
| No visual learning roadmap | Hard to see progress and interdependencies |
| Scattered resources | Learners must jump between YouTube, docs, papers, blogs |

---

## 3. Product Vision

> **"Give every learner a personal AI tutor that builds their exact roadmap, knows what they already know, and finds the internet's best resources for each step."**

PathMind AI makes structured, personalized learning accessible to anyone — in any domain — without requiring manual curation.

---

## 4. Target Users

### 4.1 Primary Persona: "The Self-Directed Learner"
- **Who:** University students, career-switchers, working professionals upskilling
- **Goal:** Learn a new technical or academic subject efficiently
- **Pain:** Not knowing *what* to learn, *in what order*, or *where* to find quality resources
- **Behavior:** Motivated to learn but struggles with structuring self-study

### 4.2 Secondary Persona: "The Domain Expert Exploring Adjacent Fields"
- **Who:** A software engineer learning ML, a biologist learning bioinformatics
- **Goal:** Skip content they already know; fast-track to the new material
- **Key Need:** Prior knowledge acknowledgment — don't waste my time

### 4.3 Tertiary Persona: "The Educator/Content Creator"
- **Who:** Tutors, bootcamp instructors building curriculum
- **Goal:** Rapidly generate structured learning paths as a starting scaffold

---

## 5. Core User Flows

### 5.1 New Learning Path Creation (Happy Path)

```
[User lands → sees Auth screen]
        ↓
[Signs up / logs in via Supabase Auth]
        ↓
[Enters learning goal in chat bar]
    e.g. "I want to learn Machine Learning"
        ↓
[AI generates 5–8 prerequisite self-assessment questions]
    e.g. "Rate your Python knowledge: 0 (none) to 5 (expert)"
        ↓
[User answers each question with a 1–5 rating button]
        ↓
[All answers collected → "Building your curriculum..." loading state]
        ↓
[AI generates a personalized DAG curriculum (10–20 nodes, 2–4 sections)]
    • Topics where user rated ≥ 4 → auto-marked "Completed"
    • Other topics → "Locked" until prerequisites are done
        ↓
[Visual node graph appears in the main canvas]
```

### 5.2 Studying a Node (On-Demand Resource Generation)

```
[User clicks on an available node in the graph]
        ↓
[Node Detail Panel slides open (right side)]
    Shows: title, description, difficulty, estimated time, prerequisites
        ↓
[System checks cache (Supabase DB → Pinecone vector store)]
    Cache HIT → Resources load instantly
    Cache MISS → "Generate Resources" button shown (for major nodes)
        ↓
[User clicks "Generate Resources"]
        ↓
[AI Content Swarm runs in background:]
    1. Query Generator → 3 targeted search queries (web, academic, video)
    2. Web Worker → searches internet for tutorials/docs
    3. Academic Worker → finds research papers
    4. Multimedia Worker → finds YouTube videos + extracts transcripts
    5. Synthesizer → curates 3–5 best resources + writes topic summary
        ↓
[Resources appear: video links, article links, academic papers]
[Knowledge check questions rendered (one at a time, sliding UI)]
        ↓
[User studies, then clicks "Mark as Completed"]
        ↓
[Node marked completed → Dependent nodes unlock → Graph updates live]
```

### 5.3 Returning User (Session Resume)

```
[User logs in → sees sidebar with past learning paths]
        ↓
[Clicks a past path → curriculum graph loads from DB]
        ↓
[Resumes from where they left off — all progress preserved]
```

---

## 6. Feature Requirements

### 6.1 Authentication
| ID | Requirement | Priority |
|---|---|---|
| AUTH-1 | Email/password sign-up and login via Supabase Auth | P0 |
| AUTH-2 | Session persistence across browser refreshes | P0 |
| AUTH-3 | Protected routes — all API calls require JWT | P0 |
| AUTH-4 | Sign-out functionality | P0 |

### 6.2 Onboarding & Survey
| ID | Requirement | Priority |
|---|---|---|
| SURV-1 | User submits a free-text learning goal | P0 |
| SURV-2 | AI generates 5–8 prerequisite topic questions for that specific goal | P0 |
| SURV-3 | One question displayed at a time with 0–5 rating buttons | P0 |
| SURV-4 | Progress indicator shown during survey | P1 |
| SURV-5 | Survey answers persisted to Supabase immediately per answer | P0 |
| SURV-6 | Auto-complete nodes where user rated ≥ 4 (already knows) | P0 |

### 6.3 Curriculum Graph Generation
| ID | Requirement | Priority |
|---|---|---|
| CURR-1 | AI generates a DAG of 10–20 nodes organized into 2–4 sections | P0 |
| CURR-2 | Each node has: ID, title, description, prerequisites, difficulty (1–5), estimated time, section | P0 |
| CURR-3 | ~30% of nodes flagged `is_major=true` (warrant curated resource generation) | P1 |
| CURR-4 | Nodes with all prerequisites completed are unlocked ("available") | P0 |
| CURR-5 | Curriculum graph cached in Pinecone for reuse (same goal = instant response) | P1 |
| CURR-6 | Graph persisted to Supabase `learning_paths` table on generation | P0 |
| CURR-7 | All nodes bulk-inserted into `path_nodes` table | P0 |

### 6.4 Visual Graph Canvas
| ID | Requirement | Priority |
|---|---|---|
| GRAPH-1 | Interactive node graph rendered using ReactFlow (@xyflow/react) | P0 |
| GRAPH-2 | Nodes styled by status: locked (gray), available (highlighted), completed (green) | P0 |
| GRAPH-3 | Directed edges with animation on available nodes | P1 |
| GRAPH-4 | Node click opens the Node Detail Panel | P0 |
| GRAPH-5 | Graph updates live when a node is marked complete | P0 |
| GRAPH-6 | Nodes organized in left-to-right / top-to-bottom layout by section | P1 |

### 6.5 Node Detail Panel
| ID | Requirement | Priority |
|---|---|---|
| NODE-1 | Slide-in panel from the right showing node metadata | P0 |
| NODE-2 | Shows: title, status badge, description, difficulty label, estimated time | P0 |
| NODE-3 | Shows curated resources (video, article, academic) with clickable links | P0 |
| NODE-4 | Shows knowledge-check questions (one at a time, sliding animation) | P1 |
| NODE-5 | "Generate Resources" button for major nodes without cached resources | P0 |
| NODE-6 | Loading state while swarm is running ("Gathering resources...") | P0 |
| NODE-7 | "Mark as Completed" button for available/in-progress nodes | P0 |
| NODE-8 | Shows prerequisites list as chips | P1 |
| NODE-9 | Locked nodes show "Complete prerequisites to unlock" message | P0 |

### 6.6 Content Swarm (On-Demand Resource Generation)
| ID | Requirement | Priority |
|---|---|---|
| SWARM-1 | Query Generator creates 3 search queries (web, academic, video) per topic | P0 |
| SWARM-2 | Practical/Web Worker fetches web content (tutorials, docs) | P0 |
| SWARM-3 | Academic Worker searches research/academic sources | P0 |
| SWARM-4 | Multimedia Worker searches YouTube and extracts video transcripts | P0 |
| SWARM-5 | Synthesizer curates 3–5 best resources + writes topic summary | P0 |
| SWARM-6 | VectorIngestionGate persists output to Pinecone + Supabase | P0 |
| SWARM-7 | Cache-first: check Supabase DB then Pinecone before running swarm | P0 |
| SWARM-8 | SSE streaming so frontend can show live progress | P1 |

### 6.7 Path History & Sidebar
| ID | Requirement | Priority |
|---|---|---|
| HIST-1 | Left sidebar lists all past learning paths for the user | P0 |
| HIST-2 | Each path shows: learning goal, progress (X/Y nodes completed) | P0 |
| HIST-3 | Clicking a past path loads the curriculum graph | P0 |
| HIST-4 | "New Path" button to start a fresh learning goal | P0 |
| HIST-5 | Paths sorted by creation date (newest first) | P1 |

### 6.8 Memory Consolidation
| ID | Requirement | Priority |
|---|---|---|
| MEM-1 | On session end, AI generates a 2–3 sentence session summary | P1 |
| MEM-2 | Session summary saved to Supabase `sessions` table | P1 |
| MEM-3 | Session summary embedded and stored in Pinecone per-user namespace | P1 |
| MEM-4 | Memory consolidation runs as a non-blocking background task | P1 |

---

## 7. Non-Functional Requirements

### 7.1 Performance
| Requirement | Target |
|---|---|
| Survey question generation latency | < 5 seconds |
| Curriculum graph generation (cache miss) | < 30 seconds |
| Curriculum graph generation (cache hit) | < 2 seconds |
| Node resource generation (swarm) | < 60 seconds |
| Node resource load (cache hit) | < 500ms |
| Frontend page load | < 2 seconds |

### 7.2 Reliability
- All AI calls use automatic key rotation with up to 4 retry attempts
- Rate-limit errors trigger precise backoffs (parsed from API error messages)
- Non-critical operations (memory consolidation, vector cache writes) are non-fatal — failures are logged and execution continues

### 7.3 Security
- All Python AI backend endpoints require Supabase JWT authentication
- Supabase Row Level Security (RLS) ensures users can only access their own data
- The Go backend uses the service role key for DB operations, bypassing RLS only for trusted server-side operations
- CORS is configured for allowed origins only

### 7.4 Scalability
- Multiple LLM API keys can be configured (comma-separated) and are round-robin rotated
- Curriculum graphs cached in Pinecone — popular goals (e.g., "Learn Python") serve instantly for all users
- Node resources cached globally in `node_resources` table — one swarm run per unique topic slug

---

## 8. Success Metrics

| Metric | Definition | Target |
|---|---|---|
| Survey Completion Rate | % of users who complete all survey questions | > 80% |
| Graph Generation Success Rate | % of goal submissions that produce a valid graph | > 95% |
| Node Engagement Rate | % of available nodes that get clicked | > 60% |
| Resource Generation Rate | % of major nodes where user triggers resource generation | > 40% |
| Path Completion Rate | % of paths where user completes ≥ 50% of nodes | > 25% |
| Cache Hit Rate (curriculum) | % of curriculum requests served from cache | > 30% (improves over time) |
| Cache Hit Rate (node resources) | % of node resource requests served from cache | > 50% (after ramp-up) |

---

## 9. Constraints & Assumptions

### 9.1 Technical Constraints
- LLM API rate limits (Gemini 2.5 Flash, Groq llama-3.3-70b) require key rotation
- Pinecone metadata limit of ~40KB per vector (large graphs are truncated to summaries)
- YouTube transcript API is unofficial and may break on API changes
- LangGraph checkpointing uses in-memory `MemorySaver` — state is lost on server restart (mitigated by Supabase DB restore)

### 9.2 Business Constraints
- Platform is deployed on Render's free tier → cold start latency possible
- No payment layer in v1 — open access

### 9.3 Assumptions
- Users have a clear enough goal to express in a sentence
- Users are honest in their self-assessment ratings
- Gemini 2.5 Flash produces valid JSON output reliably enough with regex fallback parsing

---

## 10. Out of Scope (v1)

- Real-time collaborative learning paths (multi-user)
- Native mobile app (iOS/Android)
- Instructor/teacher dashboard
- Certificate or badge system
- In-platform video player (links out to YouTube)
- Adaptive re-routing based on quiz performance (quiz answers are not yet analyzed)
- Social features (sharing paths, commenting)
- Custom user profiles beyond auth email
- Payments / subscription tiers

---

## 11. Dependencies

| Dependency | Type | Risk |
|---|---|---|
| Supabase (Auth + DB) | Managed service | Low — mature platform |
| Pinecone (Vector DB) | Managed service | Low |
| Groq API (llama-3.3-70b) | LLM inference | Medium — rate limits |
| Google Gemini 2.5 Flash | LLM inference | Medium — rate limits |
| YouTube Data API v3 | External API | Medium — quota limits |
| youtube-transcript-api | Open source lib | High — unofficial, fragile |
| Render (deployment) | Cloud hosting | Low |
| Vercel (frontend) | Cloud hosting | Low |

---

## 12. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Gemini returns non-JSON output | Medium | High | Regex JSON extraction fallback + retry |
| YouTube transcript API breaks | High | Medium | Graceful degradation — swarm continues without video |
| LLM API rate exhaustion | Medium | High | Multi-key rotation (4 keys, automatic retry) |
| Pinecone latency spikes | Low | Medium | Supabase DB cache checked first |
| Graph generation produces invalid DAG (circular deps) | Low | Medium | Pydantic validation + slug sanitization |

