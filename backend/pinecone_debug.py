import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.Agent.Tools.VectorStore import VectorStore

async def main():
    vs = VectorStore()
    matches = await vs.asearch("lesson about Introduction to Programming with Python", "content", 5)
    print("Found matches:", len(matches))
    for m in matches:
        print("Score:", m.get("score"))
        meta = m.get("metadata", {})
        print("Topic:", meta.get("topic"))
        print("Has chunk_text?", "chunk_text" in meta)

if __name__ == "__main__":
    asyncio.run(main())
