import asyncio
import re
from ...LearnerState import LearnerState
from ...Tools.VectorStore import VectorStore

# ── Text Chunker ──────────────────────────────────────────────────────────────
def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]:
    """
    Splits text into overlapping word-level chunks.
    chunk_size and overlap are in approximate words (not tokens),
    which is close enough for educational content without needing a tokenizer.
    """
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap   # slide forward with overlap
    return [c for c in chunks if len(c.strip()) > 20]  # drop near-empty chunks


def _slugify(text: str) -> str:
    """Convert topic name to a safe vector ID prefix."""
    return re.sub(r"[^a-z0-9_]", "_", text.lower().strip())[:48]


async def vector_ingestion_gate_node(state: LearnerState) -> dict:
    """
    Sub-Node 3.4 — VectorIngestionGate
    Runs after ContentSynthesizer. Takes the compiled markdown lesson and:
    1. Chunks it into overlapping word-level segments.
    2. Embeds each chunk using text-embedding-004 (via EmbeddingFactory).
    3. Upserts all chunks to Pinecone 'content' namespace with rich metadata.
    4. Resets swarm state fields so stale data doesn't bleed into the next topic.

    NO LLM call — fully programmatic.
    """
    topic = state.get("current_topic", "unknown")
    topic_id = state.get("current_topic_id", "")
    lesson = state.get("content_module", "")
    raw_results = state.get("swarm_raw_results", [])

    if not lesson:
        # Nothing to ingest — clear fields and continue
        print("[VectorIngestionGate] No lesson content to ingest. Skipping.")
        return {
            "swarm_queries": [],
            "swarm_raw_results": [],
        }

    # Collect all source URLs from the swarm workers
    source_urls = list({
        r.get("source_url", "") for r in raw_results if r.get("source_url")
    })

    try:
        vs = VectorStore()

        # 1. Chunk the lesson
        chunks = chunk_text(lesson, chunk_size=512, overlap=64)
        print(f"[VectorIngestionGate] Ingesting {len(chunks)} chunks for topic: '{topic}'")

        if not chunks:
            print("[VectorIngestionGate] No chunks generated from lesson. Skipping upsert.")
            return {"swarm_queries": [], "swarm_raw_results": []}

        topic_slug = _slugify(topic)

        # 2. Build metadata for each chunk
        metadatas = [
            {
                "topic": topic,
                "topic_id": topic_id,
                "chunk_index": i,
                "source_urls": source_urls[:5],   # cap to avoid metadata size limits
                "total_chunks": len(chunks),
            }
            for i in range(len(chunks))
        ]

        # 3. Embed + upsert to Pinecone 'content' namespace
        await vs.aupsert(
            texts=chunks,
            metadatas=metadatas,
            namespace="content"
        )

        print(f"[VectorIngestionGate] ✅ Successfully ingested {len(chunks)} chunks into Pinecone 'content' namespace.")

    except Exception as e:
        # Non-fatal — if Pinecone ingestion fails, the lesson was still delivered
        print(f"[VectorIngestionGate] ⚠️ Ingestion failed (non-fatal): {str(e)}")

    # 4. Always reset swarm state fields regardless of ingestion success
    return {
        "swarm_queries": [],
        "swarm_raw_results": [],
        # NOTE: We do NOT clear content_module here so the parent graph can still
        # read the lesson and append it to conversation_history if needed.
    }
