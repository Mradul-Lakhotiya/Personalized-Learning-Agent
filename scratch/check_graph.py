import asyncio
import sys
import os

# Add backend dir to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../backend'))

from app.Agent.Tools.Database import Database

async def main():
    db = Database()
    paths = await db.get_learning_paths("default_user")  # Wait, what's the user ID?
    # Let's just fetch all learning paths and get the most recent one
    response = db.client.table("learning_paths").select("*").order("created_at", desc=True).limit(1).execute()
    if not response.data:
        print("No paths found")
        return
    
    path = response.data[0]
    print(f"Path ID: {path['id']}")
    print(f"Phase: {path['phase']}")
    graph = path.get("curriculum_graph", {})
    nodes = graph.get("nodes", [])
    
    print("\nNodes:")
    for n in nodes:
        print(f"- ID: {n['id']}")
        print(f"  Title: {n['title']}")
        print(f"  Status: {n['status']}")
        print(f"  Prerequisites: {n['prerequisites']}")
    
    print("\nCompleted IDs in path row:")
    print(path.get("completed_node_ids", []))

if __name__ == "__main__":
    asyncio.run(main())
