import os
import asyncio
from pinecone import Pinecone
from .Embeddings import EmbeddingFactory

class VectorStore:
    """
    Wrapper for Pinecone vector operations.
    Handles the async offloading since Pinecone's standard client is synchronous.
    """
    def __init__(self):
        self.api_key = os.getenv("PINECONE_API_KEY")
        self.index_name = os.getenv("PINECONE_INDEX_NAME", "learning-agent")
        
        if not self.api_key:
            raise ValueError("PINECONE_API_KEY is not set.")
            
        self.pc = Pinecone(api_key=self.api_key)
        self.index = self.pc.Index(self.index_name)
        self.embeddings = EmbeddingFactory.get_embeddings()

    async def asearch(self, query: str, namespace: str, top_k: int = 5) -> list[dict]:
        """Async wrapper for vector search."""
        # 1. Embed query
        query_vector = await asyncio.to_thread(
            self.embeddings.embed_query, query
        )
        
        # Google's embeddings support Matryoshka representation learning.
        # We truncate to 768 dimensions to match the Pinecone index.
        query_vector = query_vector[:768]
        
        # 2. Search Pinecone
        response = await asyncio.to_thread(
            self.index.query,
            namespace=namespace,
            vector=query_vector,
            top_k=top_k,
            include_metadata=True
        )
        return response.get("matches", [])

    async def aupsert(self, texts: list[str], metadatas: list[dict], namespace: str):
        """Async wrapper for vector upsert."""
        # 1. Embed documents
        vectors = await asyncio.to_thread(
            self.embeddings.embed_documents, texts
        )
        
        # Google's embeddings support Matryoshka representation learning.
        # We truncate all vectors to 768 dimensions to match the Pinecone index.
        vectors = [vec[:768] for vec in vectors]
        
        # 2. Prepare for Pinecone
        # Using a hash of the text or a random UUID as the ID
        import uuid
        records = []
        for vec, meta in zip(vectors, metadatas):
            record_id = str(uuid.uuid4())
            records.append({"id": record_id, "values": vec, "metadata": meta})
            
        # 3. Upsert
        await asyncio.to_thread(
            self.index.upsert,
            vectors=records,
            namespace=namespace
        )
