import os
import random
import asyncio
from typing import Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# We'll retry on common free-tier exhaustion errors
class RateLimitError(Exception): pass

def get_gemini_keys() -> list[str]:
    keys_raw = os.getenv("GEMINI_KEYS", "")
    return [k.strip() for k in keys_raw.split(",") if k.strip() and "REPLACE" not in k.strip()]

class LlmFactory:
    """
    Factory for instantiating LLM clients with built-in key rotation.
    Ensures that we round-robin across available Gemini free-tier keys
    to avoid hitting the tight RPM limits.
    """
    @staticmethod
    def get_llm(model: str = "gemini-2.5-flash", temperature: float = 0.0) -> ChatGoogleGenerativeAI:
        keys = get_gemini_keys()
        if not keys:
            raise ValueError("No Gemini keys found in environment variables (GEMINI_KEYS).")
        
        # Randomly select a key for this instantiation
        selected_key = random.choice(keys)
        
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            google_api_key=selected_key
        )

# Resiliency Decorator for executing LLM calls
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=10),
    reraise=True
)
async def safe_ainvoke(llm: ChatGoogleGenerativeAI, prompt: str | list):
    """
    Safely invoke the LLM with automatic retries for rate limits (429)
    and temporary server errors (500/503).
    """
    try:
        return await llm.ainvoke(prompt)
    except Exception as e:
        error_msg = str(e).lower()
        if "429" in error_msg or "quota" in error_msg or "exhausted" in error_msg:
            # We can log here if needed
            raise RateLimitError(f"Rate limit hit: {e}")
        elif "503" in error_msg or "unavailable" in error_msg:
            raise Exception(f"Service unavailable: {e}")
        raise e
