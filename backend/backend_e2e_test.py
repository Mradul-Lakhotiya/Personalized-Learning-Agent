import asyncio
import os
from uuid import uuid4
from dotenv import load_dotenv

load_dotenv()

from app.Agent.Graph import app_graph
from app.Agent.Tools.Database import Database
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

async def run_e2e_test():
    print("============================================================")
    print("  BACKEND END-TO-END INTEGRATION TEST")
    print("============================================================\n")

    # 1. Setup Mock User
    db = Database()
    test_user_id = "4b09d436-2c38-4388-a618-86295c31d61e"
    print(f"[Setup] Using real user ID: {test_user_id}")
    
    # Clear existing curricula and progress for this user so the test runs cleanly
    try:
        db.client.table("curricula").delete().eq("user_id", test_user_id).execute()
        db.client.table("user_progress").delete().eq("user_id", test_user_id).execute()
        print("[Setup] Cleared prior curricula and progress for user.")
    except Exception as e:
        print(f"[Setup] Warning clearing data: {e}")

    thread_id = str(uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "user_id": test_user_id,
        "session_id": thread_id,
        "conversation_history": [
            HumanMessage(content="I am a complete beginner and I want to learn about basic sorting algorithms.")
        ],
        "last_user_message": "I am a complete beginner and I want to learn about basic sorting algorithms.",
        "user_profile": {},
        "skill_map": {},
        "master_curriculum": [],
        "current_unit_index": 1,
        "current_topic": "",
        "current_subtopic": "",
        "current_question": None,
        "answered_questions": [],
        "current_batch_scores": [],
        "consecutive_streak": 0,
        "next_action": "deliver_content",
        "remediation_needed": False,
        "session_complete": False,
        "loop_counters": {},
        "error_context": None,
        "swarm_queries": [],
        "swarm_raw_results": [],
        "compiled_markdown_lesson": "",
        "total_sessions": 1,
        "flags": {}
    }

    # -------------------------------------------------------------------------
    # PHASE 1: Initialization -> Assessment
    # Expectation: ProfileBuilder -> CurriculumPlanner -> Swarm -> KnowledgeAssessor
    # -------------------------------------------------------------------------
    print("\n[PHASE 1] Initializing learning journey...")
    app_graph.checkpointer = MemorySaver()
    
    events = app_graph.astream(initial_state, config, stream_mode="values")
    
    async for event in events:
        # Just printing state transitions
        if "current_question" in event and event["current_question"]:
            pass # We'll inspect it after the pause

    print("\n[PHASE 1 COMPLETE] Graph paused at answer_evaluator.")
    
    state = app_graph.get_state(config).values
    curriculum = await db.get_user_curricula(test_user_id)
    print(f"\n[Validation] Curriculum generated: {len(curriculum)} units.")
    if curriculum:
        for i, unit in enumerate(curriculum[:3]):
            print(f"  {i+1}. {unit['topic']} (Status: {unit['status']})")
            
    question = state.get("current_question")
    if question:
        print("\n[Validation] Generated Question:")
        print(f"  Topic: {question.get('topic')}")
        print(f"  Question: {question.get('text')}")
        print(f"  Type: {question.get('type')}")
        print(f"  Correct Answer Key: {question.get('expected')}")
    else:
        print("\n[FAILED] No current question found!")
        return

    # -------------------------------------------------------------------------
    # PHASE 2: User answers the question perfectly
    # Expectation: AnswerEvaluator -> PathRerouter
    # -------------------------------------------------------------------------
    print("\n[PHASE 2] Simulating user response...")
    
    # We will simulate a perfect answer based on the LLM's correct answer
    perfect_answer = question.get("expected", "This is a simulated perfect answer.")
    print(f"  User answers: '{perfect_answer}'")
    
    # Update state with user message
    app_graph.update_state(config, {"user_answer": perfect_answer}, as_node="knowledge_assessor")
    
    # Resume graph execution
    events = app_graph.astream(None, config, stream_mode="values")
    async for event in events:
        pass

    print("\n[PHASE 2 COMPLETE] Graph paused at answer_evaluator (or ended).")
    
    final_state = app_graph.get_state(config).values
    answered = final_state.get("answered_questions", [])
    if answered:
        last_answer = answered[-1]
        print(f"\n[Validation] Answer Evaluation:")
        print(f"  Score: {last_answer.get('score')}")
        print(f"  Feedback: {last_answer.get('feedback')}")
    else:
        print("\n[FAILED] No answered questions logged!")
        
    print(f"\n[Validation] Current Batch Scores: {final_state.get('current_batch_scores')}")
    
    # Run memory consolidation directly to test it
    print("\n[PHASE 3] Testing Memory Consolidator...")
    from app.Agent.Nodes.MemoryConsolidator import consolidate_session
    await consolidate_session(final_state)

if __name__ == "__main__":
    asyncio.run(run_e2e_test())
