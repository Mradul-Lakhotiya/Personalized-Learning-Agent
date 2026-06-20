import os
import random
from langchain_google_genai import GoogleGenerativeAIEmbeddings

def get_gemini_keys() -> list[str]:
    keys_raw = os.getenv("GEMINI_KEYS", "")
    return [k.strip() for k in keys_raw.split(",") if k.strip() and "REPLACE" not in k.strip()]

class EmbeddingFactory:
    """
    Factory for instantiating the embedding model with key rotation.
    We use text-embedding-004.
    """
    @staticmethod
    def get_embeddings() -> GoogleGenerativeAIEmbeddings:
        keys = get_gemini_keys()
        if not keys:
            raise ValueError("No Gemini keys found in environment variables.")
        
        selected_key = random.choice(keys)
        return GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=selected_key
        )
