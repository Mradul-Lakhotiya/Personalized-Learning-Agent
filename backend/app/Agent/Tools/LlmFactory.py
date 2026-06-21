import os
import re
import asyncio

class RateLimitError(Exception): pass

def get_gemini_keys() -> list[str]:
    keys_raw = os.getenv("GEMINI_KEYS", "")
    return [k.strip() for k in keys_raw.split(",") if k.strip() and "REPLACE" not in k.strip()]

def get_groq_keys() -> list[str]:
    keys_raw = os.getenv("GROQ_KEYS", "")
    return [k.strip() for k in keys_raw.split(",") if k.strip() and "REPLACE" not in k.strip()]

class LlmFactory:
    """
    Factory for managing LLM API keys and circulating between them.
    """
    _gemini_key_idx = 0
    _groq_key_idx = 0

    @classmethod
    def get_next_gemini_key(cls) -> str:
        keys = get_gemini_keys()
        if not keys:
            raise ValueError("No Gemini keys found in environment variables (GEMINI_KEYS).")
        key = keys[cls._gemini_key_idx % len(keys)]
        cls._gemini_key_idx += 1
        return key
        
    @classmethod
    def get_next_groq_key(cls) -> str:
        keys = get_groq_keys()
        if not keys:
            raise ValueError("No Groq keys found in environment variables (GROQ_KEYS).")
        key = keys[cls._groq_key_idx % len(keys)]
        cls._groq_key_idx += 1
        return key

async def safe_ainvoke_gemini(chain_builder_func, prompt_vars: dict, max_attempts: int = 4):
    """
    Safely invoke Gemini with automatic key circulation and precise rate limit backoffs.
    chain_builder_func must be a callable that takes (api_key: str) and returns a Runnable chain.
    """
    last_exception = None
    
    for attempt in range(max_attempts):
        key = LlmFactory.get_next_gemini_key()
        masked_key = f"...{key[-4:]}" if len(key) >= 4 else "..."
        
        if attempt > 0:
            print(f"[Gemini Retry] Attempt {attempt+1}/{max_attempts} - Circulating to Gemini Key ending in {masked_key}")
            
        chain = chain_builder_func(key)
        
        try:
            return await chain.ainvoke(prompt_vars)
        except Exception as e:
            error_msg = str(e).lower()
            last_exception = e
            
            if "429" in error_msg or "quota" in error_msg or "exhausted" in error_msg:
                match = re.search(r"retry in ([\d\.]+)s", error_msg)
                if match:
                    delay = float(match.group(1))
                    sleep_time = delay + 1.0
                    print(f"[Gemini Rate Limit] Hit rate limit on key {masked_key}. Waiting {sleep_time:.2f}s before trying next key...")
                    await asyncio.sleep(sleep_time)
                else:
                    print(f"[Gemini Rate Limit] Hit rate limit on key {masked_key}. Waiting 5s before trying next key...")
                    await asyncio.sleep(5.0)
            elif "503" in error_msg or "unavailable" in error_msg:
                print(f"[Gemini Server Error] Service unavailable on key {masked_key}. Waiting 3s...")
                await asyncio.sleep(3.0)
            else:
                raise e
                
    raise RateLimitError(f"All {max_attempts} attempts failed. Last error: {last_exception}")

async def safe_ainvoke_groq(chain_builder_func, prompt_vars: dict, max_attempts: int = 4):
    """
    Safely invoke Groq with automatic key circulation and precise rate limit backoffs.
    chain_builder_func must be a callable that takes (api_key: str) and returns a Runnable chain.
    """
    last_exception = None
    
    for attempt in range(max_attempts):
        key = LlmFactory.get_next_groq_key()
        masked_key = f"...{key[-4:]}" if len(key) >= 4 else "..."
        
        if attempt > 0:
            print(f"[Groq Retry] Attempt {attempt+1}/{max_attempts} - Circulating to Groq Key ending in {masked_key}")
            
        chain = chain_builder_func(key)
        
        try:
            return await chain.ainvoke(prompt_vars)
        except Exception as e:
            error_msg = str(e).lower()
            last_exception = e
            
            if "429" in error_msg or "rate limit" in error_msg:
                match = re.search(r"try again in ([\d\.]+)s", error_msg)
                if match:
                    delay = float(match.group(1))
                    sleep_time = delay + 1.0
                    print(f"[Groq Rate Limit] Hit rate limit on key {masked_key}. Waiting {sleep_time:.2f}s before trying next key...")
                    await asyncio.sleep(sleep_time)
                else:
                    print(f"[Groq Rate Limit] Hit rate limit on key {masked_key}. Waiting 5s before trying next key...")
                    await asyncio.sleep(5.0)
            elif "503" in error_msg or "unavailable" in error_msg:
                print(f"[Groq Server Error] Service unavailable on key {masked_key}. Waiting 3s...")
                await asyncio.sleep(3.0)
            else:
                raise e
                
    raise RateLimitError(f"All {max_attempts} attempts failed. Last error: {last_exception}")
