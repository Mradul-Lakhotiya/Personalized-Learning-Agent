import os
import sys
import asyncio
from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))
load_dotenv(dotenv_path=".env")

from app.Agent.Nodes.ProfileBuilder import profile_builder_node
from app.Agent.Nodes.CurriculumPlanner import curriculum_planner_node
from app.Agent.LearnerState import LearnerState

async def run_debug():
    print("Testing ProfileBuilder...")
    state = LearnerState(user_id="00000000-0000-0000-0000-000000000123")
    res1 = await profile_builder_node(state)
    print("Profile Builder Result:", res1)
    
    state.update(res1)
    
    print("\nTesting CurriculumPlanner...")
    res2 = await curriculum_planner_node(state)
    print("Curriculum Planner Result:", res2)

if __name__ == "__main__":
    asyncio.run(run_debug())
