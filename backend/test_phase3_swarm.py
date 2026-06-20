import os
import sys
import asyncio
from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(__file__), "app"))
load_dotenv(dotenv_path="../.env")

async def test_swarm():
    print("\n--- Testing Phase 3 Swarm Sub-Graph ---\n")
    
    try:
        from Agent.Swarm.SwarmGraph import swarm_graph
        print("[PASS] SwarmGraph successfully compiled!")
    except Exception as e:
        print(f"[FAIL] Graph compilation failed: {e}")
        return

    print("\n[START] Executing Parallel Swarm for topic: 'Base Java'...")
    
    initial_state = {
        "user_id": "test_user_swarm",
        "current_topic": "Base Java",
        "swarm_queries": [],
        "swarm_raw_results": []
    }
    
    try:
        # Run the sub-graph standalone
        async for output in swarm_graph.astream(initial_state):
            for node_name, state_update in output.items():
                print(f"\n[NODE] '{node_name}' finished.")
                
                if node_name == "query_generator" and "swarm_queries" in state_update:
                    print("   [INFO] Queries generated:")
                    for q in state_update["swarm_queries"]:
                        print(f"      - {q['engine'].upper()}: {q['query']}")
                        
                elif node_name in ["practical_worker", "academic_worker", "multimedia_worker"]:
                    if "swarm_raw_results" in state_update:
                        res = state_update["swarm_raw_results"]
                        if res:
                            print(f"   [SUCCESS] Gathered {len(res)} item(s).")
                        else:
                            print("   [WARN] No results found or worker failed gracefully.")
                            
                elif node_name == "synthesizer" and "content_module" in state_update:
                    print("\n[PASS] Synthesizer generated lesson:")
                    content = state_update["content_module"]
                    print("="*50)
                    print(content[:500] + "...\n(TRUNCATED FOR LOGS)")
                    print("="*50)

    except Exception as e:
        print(f"[FAIL] Swarm execution failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_swarm())
