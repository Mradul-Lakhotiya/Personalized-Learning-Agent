import os
import sys
import asyncio
from dotenv import load_dotenv
import uuid

# Add app to path
sys.path.append(os.path.join(os.path.dirname(__file__), "app"))
load_dotenv(dotenv_path="../.env")

async def test_graph():
    print("\n--- Testing Phase 2 LangGraph ---\n")
    
    # Import the compiled graph
    try:
        from Agent.Graph import app_graph
        print("[PASS] Graph successfully compiled and imported!")
    except Exception as e:
        print(f"[FAIL] Graph compilation failed: {e}")
        return

    # To test execution without needing a real Supabase Auth user,
    # we will monkey-patch the Database.get_user_profile just for this test.
    from Agent.Tools.Database import Database
    
    # Save original method
    original_get_profile = Database.get_user_profile
    original_upsert_progress = Database.upsert_topic_progress
    original_get_progress = Database.get_topic_progress
    
    async def mock_get_profile(self, user_id: str):
        print(f"   [Mock DB] Fetching profile for {user_id}")
        return {"id": user_id, "name": "Test User", "learning_goals": ["Python"]}
        
    async def mock_get_progress(self, user_id: str, topic_id: str):
        return {"mastery_score": 0.0, "status": "not_started"}
        
    async def mock_upsert_progress(self, user_id: str, topic_id: str, data: dict):
        print(f"   [Mock DB] Upserting progress for {topic_id}: {data}")
        return None

    Database.get_user_profile = mock_get_profile
    Database.get_topic_progress = mock_get_progress
    Database.upsert_topic_progress = mock_upsert_progress

    # Execute the graph
    print("\n[START] Starting Graph Execution...")
    
    # LangGraph config for MemorySaver (thread_id is required)
    config = {"configurable": {"thread_id": "test_thread_1"}}
    
    initial_state = {
        "user_id": str(uuid.uuid4()),
        "loop_counters": {},
        "recent_history": []
    }
    
    try:
        # We run it up until the interrupt_before="answer_evaluator"
        async for output in app_graph.astream(initial_state, config=config):
            for node_name, state_update in output.items():
                print(f"[NODE] Node '{node_name}' executed.")
                if "error" in state_update and state_update["error"]:
                    print(f"   [WARN] Warning/Error: {state_update['error']}")
                if "current_topic" in state_update:
                    print(f"   [INFO] Topic Selected: {state_update['current_topic']}")
                if "current_question" in state_update:
                    q = state_update['current_question']
                    print(f"   [INFO] Generated Question [{q.get('type')}]: {q.get('text')}")
                    
        # Check current state
        state = app_graph.get_state(config)
        print(f"\n[PAUSE] Graph Paused at: {state.next}")
        if "answer_evaluator" in state.next:
            print("[PASS] Successfully paused before Answer Evaluator (waiting for user input)!")
            
    except Exception as e:
        print(f"[FAIL] Graph execution failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_graph())
