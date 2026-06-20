import os
import sys
import asyncio
from dotenv import load_dotenv

# Add app to path so we can import Agent.Tools
sys.path.append(os.path.join(os.path.dirname(__file__), "app"))

load_dotenv(dotenv_path="../.env")

async def test_tools():
    print("\n--- Testing Phase 1 Tools ---")
    
    # 1. Test LlmFactory
    print("\n[1/4] Testing LlmFactory...")
    from Agent.Tools.LlmFactory import LlmFactory, safe_ainvoke
    try:
        llm = LlmFactory.get_llm(model="gemini-2.5-flash")
        res = await safe_ainvoke(llm, "Reply with 'LLM OK'")
        print(f"[PASS] LlmFactory Success: {res.content.strip()}")
    except Exception as e:
        print(f"[FAIL] LlmFactory Failed: {e}")

    # 2. Test Embeddings
    print("\n[2/4] Testing EmbeddingFactory...")
    from Agent.Tools.Embeddings import EmbeddingFactory
    try:
        embeddings = EmbeddingFactory.get_embeddings()
        vec = await asyncio.to_thread(embeddings.embed_query, "Test embedding")
        print(f"[PASS] EmbeddingFactory Success: Vector length {len(vec)}")
    except Exception as e:
        print(f"[FAIL] EmbeddingFactory Failed: {e}")

    # 3. Test VectorStore
    print("\n[3/4] Testing VectorStore (Pinecone)...")
    from Agent.Tools.VectorStore import VectorStore
    try:
        vs = VectorStore()
        # Just ping index stats
        stats = await asyncio.to_thread(vs.index.describe_index_stats)
        print(f"[PASS] VectorStore Success: Dimension {stats.get('dimension', 'unknown')}")
    except Exception as e:
        print(f"[FAIL] VectorStore Failed: {e}")

    # 4. Test Database
    print("\n[4/4] Testing Database (Supabase)...")
    from Agent.Tools.Database import Database
    try:
        db = Database()
        # Ping topics table (even if empty, it should return an empty list if migration is applied,
        # or an error if the table doesn't exist yet)
        response = await asyncio.to_thread(
            db.client.table("topics").select("id").limit(1).execute
        )
        print(f"[PASS] Database Success: Can query topics table. Data: {response.data}")
    except Exception as e:
        print(f"[WARN] Database Warning: {e}")
        print("    (If the error is about 'relation topics does not exist', you need to run 'supabase db push')")

if __name__ == "__main__":
    asyncio.run(test_tools())
