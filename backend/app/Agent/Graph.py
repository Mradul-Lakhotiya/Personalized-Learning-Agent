from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .LearnerState import LearnerState
from .CircuitBreaker import check_circuit_breaker
from .Nodes.ProfileBuilder import profile_builder_node
from .Nodes.CurriculumPlanner import curriculum_planner_node
from .Nodes.KnowledgeAssessor import knowledge_assessor_node
from .Nodes.AnswerEvaluator import answer_evaluator_node
from .Nodes.PathRerouter import path_rerouter_node
from .Nodes.ErrorHandler import error_handler_node
from .Nodes.ProgressReporter import progress_reporter_node
from .Swarm.SwarmGraph import swarm_graph

# ── Routing Functions ────────────────────────────────────────────────────────

def route_after_curriculum(state: LearnerState) -> str:
    """
    Conditional edge after CurriculumPlanner.
    If content_module is pre-filled (cache hit), skip the swarm and jump
    straight to assessment. Otherwise run the full content delivery swarm.
    """
    err = state.get("error", "")
    if err:
        return "error_handler"
    # Cache hit: content_module is flagged — skip swarm
    content = state.get("content_module", "")
    if content and not content.startswith("_cached_topic:"):
        # Actual lesson content already in state (somehow) — go assess
        return "knowledge_assessor"
    if content and content.startswith("_cached_topic:"):
        # Flagged as cached but content_module not yet fetched — still run swarm
        # (future: retrieve full chunks from Pinecone here)
        pass
    return "content_delivery"


def route_after_rerouter(state: LearnerState) -> str:
    """
    Conditional edge after PathRerouter.
    Checks circuit breakers FIRST, then reads the next_route flag.
    """
    # Circuit breaker: too many consecutive replans?
    if check_circuit_breaker(state, "curriculum_planner"):
        return "error_handler"

    # Session complete?
    if state.get("session_complete"):
        return "progress_reporter"

    route = state.get("next_route", "assessor")

    # Map route strings to node names
    route_map = {
        "assessor": "knowledge_assessor",
        "planner":  "curriculum_planner",
        "swarm":    "content_delivery",
    }
    return route_map.get(route, "knowledge_assessor")

def route_after_swarm(state: LearnerState) -> str:
    """After the content swarm delivers a lesson, always move to assessment."""
    err = state.get("error", "")
    if err:
        return "error_handler"
    return "knowledge_assessor"

def route_after_error(state: LearnerState) -> str:
    """
    ErrorHandler always routes to a node it did NOT just come from.
    Reads error_context.reason to decide where to send the user.
    """
    ctx = state.get("error_context") or {}
    reason = ctx.get("reason", "")

    if reason == "stuck_in_assessment_loop":
        return "content_delivery"   # Force-advance: re-deliver content on next topic
    elif reason == "replan_storm":
        return "progress_reporter"  # Graceful session end
    else:
        return "knowledge_assessor" # Default: retry assessment

# ── Graph Assembly ────────────────────────────────────────────────────────────

workflow = StateGraph(LearnerState)

# Register nodes
workflow.add_node("profile_builder",    profile_builder_node)
workflow.add_node("curriculum_planner", curriculum_planner_node)
workflow.add_node("content_delivery",   swarm_graph)
workflow.add_node("knowledge_assessor", knowledge_assessor_node)
workflow.add_node("answer_evaluator",   answer_evaluator_node)
workflow.add_node("path_rerouter",      path_rerouter_node)
workflow.add_node("error_handler",      error_handler_node)
workflow.add_node("progress_reporter",  progress_reporter_node)

# ── Static edges ──────────────────────────────────────────────────────────────
workflow.set_entry_point("profile_builder")
workflow.add_edge("profile_builder", "curriculum_planner")
# Graph pauses BEFORE answer_evaluator to wait for user input
workflow.add_edge("knowledge_assessor", "answer_evaluator")
workflow.add_edge("answer_evaluator",   "path_rerouter")
workflow.add_edge("progress_reporter",  END)

# ── Conditional edges ─────────────────────────────────────────────────────────
# After curriculum planner: use swarm OR skip to assessment if content is cached
workflow.add_conditional_edges(
    "curriculum_planner",
    route_after_curriculum,
    {
        "content_delivery":   "content_delivery",
        "knowledge_assessor": "knowledge_assessor",
        "error_handler":      "error_handler",
    }
)

workflow.add_conditional_edges(
    "path_rerouter",
    route_after_rerouter,
    {
        "knowledge_assessor": "knowledge_assessor",
        "curriculum_planner": "curriculum_planner",
        "content_delivery":   "content_delivery",
        "error_handler":      "error_handler",
        "progress_reporter":  "progress_reporter",
    }
)

workflow.add_conditional_edges(
    "content_delivery",
    route_after_swarm,
    {
        "knowledge_assessor": "knowledge_assessor",
        "error_handler":      "error_handler",
    }
)

workflow.add_conditional_edges(
    "error_handler",
    route_after_error,
    {
        "content_delivery":   "content_delivery",
        "knowledge_assessor": "knowledge_assessor",
        "progress_reporter":  "progress_reporter",
    }
)

# ── Compile ───────────────────────────────────────────────────────────────────
# MemorySaver for now — Redis deferred to Phase 5
memory = MemorySaver()
app_graph = workflow.compile(
    checkpointer=memory,
    interrupt_before=["answer_evaluator"]  # Pause here to wait for user answer
)
