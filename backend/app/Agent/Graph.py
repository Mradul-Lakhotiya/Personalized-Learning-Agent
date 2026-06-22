from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .LearnerState import LearnerState
from .Nodes.ProfileBuilder import profile_builder_node
from .Nodes.CurriculumPlanner import curriculum_planner_node
from .Nodes.ErrorHandler import error_handler_node
from .Swarm.SwarmGraph import swarm_graph


# ── Routing Functions ─────────────────────────────────────────────────────────

def route_after_profile(state: LearnerState) -> str:
    """
    After ProfileBuilder:
    - If there was an error, route to error_handler.
    - If survey is already complete (returning user), go straight to curriculum.
    - Otherwise the graph pauses here (returns END). The frontend sends survey
      answers one-by-one via POST /api/v1/agent/survey-answer, which calls
      GraphService.submit_survey_answer() to accumulate answers in state
      WITHOUT resuming the graph. When all answers are in, the frontend
      calls POST /api/v1/agent/generate-curriculum to resume the graph.
    """
    err = state.get("error", "")
    if err:
        return "error_handler"

    # Survey already complete (returning user or all answers collected)
    if state.get("survey_complete"):
        return "curriculum_planner"

    # Survey not yet complete — pause and wait for answers
    return END


def route_after_curriculum(state: LearnerState) -> str:
    """After CurriculumPlanner: surface the graph or handle error."""
    err = state.get("error", "")
    if err:
        return "error_handler"
    return END


def route_after_error(state: LearnerState) -> str:
    """ErrorHandler routes based on the error context."""
    ctx = state.get("error_context") or {}
    reason = ctx.get("reason", "")
    if reason == "replan_storm":
        return END
    return "curriculum_planner"


# ── Graph Assembly ─────────────────────────────────────────────────────────────

workflow = StateGraph(LearnerState)

workflow.add_node("profile_builder",    profile_builder_node)
workflow.add_node("curriculum_planner", curriculum_planner_node)
workflow.add_node("error_handler",      error_handler_node)
# The content swarm is invoked on-demand via POST /api/v1/agent/generate-node,
# NOT as part of the main graph flow.

workflow.set_entry_point("profile_builder")

workflow.add_conditional_edges(
    "profile_builder",
    route_after_profile,
    {
        "curriculum_planner": "curriculum_planner",
        "error_handler":      "error_handler",
        END:                  END,
    }
)

workflow.add_conditional_edges(
    "curriculum_planner",
    route_after_curriculum,
    {
        END:             END,
        "error_handler": "error_handler",
    }
)

workflow.add_conditional_edges(
    "error_handler",
    route_after_error,
    {
        "curriculum_planner": "curriculum_planner",
        END:                  END,
    }
)

# ── Compile ───────────────────────────────────────────────────────────────────
memory = MemorySaver()
app_graph = workflow.compile(checkpointer=memory)
