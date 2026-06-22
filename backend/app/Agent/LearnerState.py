from typing import Annotated, Any, Literal, List
from typing_extensions import TypedDict
import operator


# ── Swarm types (unchanged) ─────────────────────────────────────────────────
class SwarmWorkerResult(TypedDict):
    source_type: str   # 'academic' | 'web' | 'video'
    raw_text: str
    source_url: str
    title: str
    metadata: dict


class SwarmQuery(TypedDict):
    engine: str        # 'academic' | 'web' | 'video'
    query: str


# ── New: Learning Graph types ────────────────────────────────────────────────
class LearningNode(TypedDict):
    """A single node in the visual learning path graph."""
    id: str                  # URL-safe slug: "python-basics"
    title: str               # "Python Basics"
    description: str         # 1–2 sentences shown in the side panel
    prerequisites: List[str] # list of node ids that must be completed first
    difficulty: int          # 1–5
    estimated_minutes: int
    section: str             # "Section 1: Foundations"
    section_number: int      # 1, 2, 3 …
    is_major: bool           # True → content swarm generates resources for this node
    status: str              # "locked" | "available" | "in_progress" | "completed"


class LearnerState(TypedDict):
    """
    The central state object passed between all LangGraph nodes.
    Redesigned for the Visual Learning Path Generator.
    """
    # ── Identity ─────────────────────────────────────────────────────────────
    user_id: str
    session_id: str

    # ── Profile ──────────────────────────────────────────────────────────────
    user_profile: dict          # goal, background, learning_style, time_budget
    skill_ratings: dict         # topic → 0-5 self-rated score from survey

    # ── Learning Goal ────────────────────────────────────────────────────────
    learning_goal: str          # The user's stated goal, e.g. "Learn Machine Learning"

    # ── Curriculum Graph ─────────────────────────────────────────────────────
    curriculum_graph: dict      # { "nodes": [...LearningNode], "edges": [...] }
    sections_generated: int     # how many sections have been lazily generated so far
    current_section: int        # which section the user is currently working on
    completed_node_ids: List[str]  # ids of nodes the user has explicitly completed
    active_node_id: str | None  # which node the user most recently clicked

    # ── Survey State (used during onboarding only) ───────────────────────────
    survey_questions: List[dict]   # [{ question, topic, current_index }]
    survey_answers: List[dict]     # [{ question, topic, rating }]
    survey_complete: bool

    # ── Dialogue (populated on /agent/start call) ────────────────────────────
    conversation_history: Annotated[list[dict], operator.add]
    last_user_message: str

    # ── Phase Routing ────────────────────────────────────────────────────────
    phase: str                  # "onboarding" | "graph_ready"
    session_complete: bool

    # ── Error ─────────────────────────────────────────────────────────────────
    error: str
    loop_counters: dict[str, int]
    error_context: dict | None

    # ── Content Swarm (on-demand, per node click) ────────────────────────────
    swarm_queries: List[SwarmQuery]
    swarm_raw_results: Annotated[List[SwarmWorkerResult], operator.add]
    content_module: str          # 2–3 sentence topic summary (from Synthesizer)
    node_resources_output: dict  # { summary, resources } from Synthesizer → VectorIngestionGate
    current_topic: str           # slug of the node being fetched (used by swarm)

    # ── Persistence ──────────────────────────────────────────────────────────
    db_path_id: str              # Supabase learning_paths.id (UUID) for this session

    # ── Meta ─────────────────────────────────────────────────────────────────
    total_sessions: int
    flags: dict[str, Any]
