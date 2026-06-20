from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .LearnerState import LearnerState
from .CircuitBreaker import check_circuit_breaker
from .Nodes.ProfileBuilder import profile_builder_node
from .Nodes.CurriculumPlanner import curriculum_planner_node
from .Nodes.KnowledgeAssessor import knowledge_assessor_node
from .Nodes.AnswerEvaluator import answer_evaluator_node
from .Nodes.PathRerouter import path_rerouter_node
from .Nodes.UtilityNodes import error_handler_node, progress_reporter_node
from .Swarm.SwarmGraph import swarm_graph

# (Dummy swarm node removed)

# --- Routing Functions ---
def route_after_evaluation(state: LearnerState) -> str:
    """Conditional edge logic after Path Rerouter"""
    err = state.get("error")
    if err:
        return "error"
        
    if not check_circuit_breaker(state, "answer_evaluator"):
        return "error"
        
    route = state.get("next_route", "assessor")
    return route

def route_after_swarm(state: LearnerState) -> str:
    return "assessor"

# --- Graph Assembly ---
workflow = StateGraph(LearnerState)

# Add Nodes
workflow.add_node("profile_builder", profile_builder_node)
workflow.add_node("curriculum_planner", curriculum_planner_node)
workflow.add_node("knowledge_assessor", knowledge_assessor_node)
workflow.add_node("answer_evaluator", answer_evaluator_node)
workflow.add_node("path_rerouter", path_rerouter_node)
workflow.add_node("content_delivery", swarm_graph)
workflow.add_node("error_handler", error_handler_node)
workflow.add_node("progress_reporter", progress_reporter_node)

# Add Edges
workflow.set_entry_point("profile_builder")

workflow.add_edge("profile_builder", "curriculum_planner")
workflow.add_edge("curriculum_planner", "knowledge_assessor")

# The graph will interrupt BEFORE answer_evaluator to wait for user input.
workflow.add_edge("knowledge_assessor", "answer_evaluator") 

workflow.add_edge("answer_evaluator", "path_rerouter")

workflow.add_conditional_edges(
    "path_rerouter",
    route_after_evaluation,
    {
        "assessor": "knowledge_assessor",
        "planner": "curriculum_planner",
        "swarm": "content_delivery",
        "error": "error_handler"
    }
)

workflow.add_conditional_edges(
    "content_delivery",
    route_after_swarm,
    {
        "assessor": "knowledge_assessor"
    }
)

# Terminal edges
workflow.add_edge("error_handler", "progress_reporter")
workflow.add_edge("progress_reporter", END)

# Compile
# For Phase 2 testing, we use MemorySaver instead of Redis
memory = MemorySaver()
app_graph = workflow.compile(
    checkpointer=memory,
    interrupt_before=["answer_evaluator"]
)
