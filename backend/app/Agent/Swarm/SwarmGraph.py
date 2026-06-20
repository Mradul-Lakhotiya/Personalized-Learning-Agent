from langgraph.graph import StateGraph, END
from ..LearnerState import LearnerState

from .Nodes.QueryGenerator import query_generator_node
from .Nodes.PracticalWorker import practical_worker_node
from .Nodes.AcademicWorker import academic_worker_node
from .Nodes.MultimediaWorker import multimedia_worker_node
from .Nodes.Synthesizer import synthesizer_node

# --- Swarm Graph Assembly ---
# We use the same LearnerState so it integrates seamlessly with the parent graph
swarm_workflow = StateGraph(LearnerState)

# Add Nodes
swarm_workflow.add_node("query_generator", query_generator_node)
swarm_workflow.add_node("practical_worker", practical_worker_node)
swarm_workflow.add_node("academic_worker", academic_worker_node)
swarm_workflow.add_node("multimedia_worker", multimedia_worker_node)
swarm_workflow.add_node("synthesizer", synthesizer_node)

# Add Edges
swarm_workflow.set_entry_point("query_generator")

# Fan-out: One node branches to three parallel workers
swarm_workflow.add_edge("query_generator", "practical_worker")
swarm_workflow.add_edge("query_generator", "academic_worker")
swarm_workflow.add_edge("query_generator", "multimedia_worker")

# Fan-in: All three workers must complete before synthesizer runs
swarm_workflow.add_edge("practical_worker", "synthesizer")
swarm_workflow.add_edge("academic_worker", "synthesizer")
swarm_workflow.add_edge("multimedia_worker", "synthesizer")

# End
swarm_workflow.add_edge("synthesizer", END)

# Compile the sub-graph
# We do not use an interrupter here; it runs autonomously
swarm_graph = swarm_workflow.compile()
