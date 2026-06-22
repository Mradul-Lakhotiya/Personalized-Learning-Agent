from langgraph.graph import StateGraph, END
from ..LearnerState import LearnerState

from .Nodes.QueryGenerator import query_generator_node
from .Nodes.PracticalWorker import practical_worker_node
from .Nodes.AcademicWorker import academic_worker_node
from .Nodes.MultimediaWorker import multimedia_worker_node
from .Nodes.Synthesizer import synthesizer_node
from .Nodes.VectorIngestionGate import vector_ingestion_gate_node

# ── Swarm Sub-Graph Assembly ──────────────────────────────────────────────────
# Implements the parallel content fan-out/fan-in pattern from the architecture.
# The parent graph treats this entire compiled sub-graph as a single node.
swarm_workflow = StateGraph(LearnerState)

# Register all nodes
swarm_workflow.add_node("query_generator",       query_generator_node)
swarm_workflow.add_node("practical_worker",      practical_worker_node)
swarm_workflow.add_node("academic_worker",       academic_worker_node)
swarm_workflow.add_node("multimedia_worker",     multimedia_worker_node)
swarm_workflow.add_node("synthesizer",           synthesizer_node)
swarm_workflow.add_node("vector_ingestion_gate", vector_ingestion_gate_node)

swarm_workflow.set_entry_point("query_generator")

# ── Fan-Out: one query generator → three parallel workers ────────────────────
swarm_workflow.add_edge("query_generator", "practical_worker")
swarm_workflow.add_edge("query_generator", "academic_worker")
swarm_workflow.add_edge("query_generator", "multimedia_worker")

# ── Fan-In: all three workers complete → synthesizer ─────────────────────────
# NOTE: LangGraph does NOT automatically parallelise these three workers or
# wait for all of them before firing synthesizer. They run one after another
# in the order the edges are evaluated. The `add` reducer on swarm_raw_results
# accumulates results across the sequential runs; it does NOT create a join point.
swarm_workflow.add_edge("practical_worker",  "synthesizer")
swarm_workflow.add_edge("academic_worker",   "synthesizer")
swarm_workflow.add_edge("multimedia_worker", "synthesizer")

# ── After synthesis: persist to Pinecone, then exit ──────────────────────────
swarm_workflow.add_edge("synthesizer",           "vector_ingestion_gate")
swarm_workflow.add_edge("vector_ingestion_gate", END)

# Compile the sub-graph (no checkpointer — parent graph owns persistence)
swarm_graph = swarm_workflow.compile()
