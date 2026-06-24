import asyncio
import re

from app.config import get_settings


class RateLimitError(Exception):
    pass


class LlmFactory:
    """
    Factory for managing LLM API keys with round-robin rotation.
    Keys are loaded from config.get_settings() so they're read once on startup.
    """
    _gemini_key_idx = 0
    _groq_key_idx = 0

    @classmethod
    def get_next_gemini_key(cls) -> str:
        keys = get_settings().gemini_keys
        if not keys:
            raise ValueError(
                "No Gemini keys found. Set GEMINI_KEYS in app/config.py "
                "(comma-separated if multiple)."
            )
        key = keys[cls._gemini_key_idx % len(keys)]
        cls._gemini_key_idx += 1
        return key

    @classmethod
    def get_next_groq_key(cls) -> str:
        keys = get_settings().groq_keys
        if not keys:
            raise ValueError(
                "No Groq keys found. Set GROQ_KEYS in app/config.py "
                "(comma-separated if multiple)."
            )
        key = keys[cls._groq_key_idx % len(keys)]
        cls._groq_key_idx += 1
        return key


async def safe_ainvoke_gemini(chain_builder_func, prompt_vars: dict, max_attempts: int = 4):
    """
    Safely invoke Gemini with automatic key rotation and precise rate-limit backoffs.

    chain_builder_func must accept (api_key: str) and return a LangChain Runnable.
    """
    last_exception = None

    for attempt in range(max_attempts):
        key = LlmFactory.get_next_gemini_key()
        masked_key = f"...{key[-4:]}" if len(key) >= 4 else "..."

        if attempt > 0:
            print(
                f"[Gemini Retry] Attempt {attempt + 1}/{max_attempts} "
                f"— rotating to key ending in {masked_key}"
            )

        chain = chain_builder_func(key)

        try:
            return await chain.ainvoke(prompt_vars)
        except Exception as e:
            error_msg = str(e).lower()
            last_exception = e

            if "429" in error_msg or "quota" in error_msg or "exhausted" in error_msg:
                match = re.search(r"retry in ([\d\.]+)s", error_msg)
                sleep_time = float(match.group(1)) + 1.0 if match else 5.0
                print(
                    f"[Gemini Rate Limit] Key {masked_key} exhausted. "
                    f"Waiting {sleep_time:.2f}s before next key..."
                )
                await asyncio.sleep(sleep_time)
            elif "503" in error_msg or "unavailable" in error_msg:
                print(f"[Gemini Server Error] Service unavailable on {masked_key}. Waiting 3s...")
                await asyncio.sleep(3.0)
            else:
                raise e

    raise RateLimitError(
        f"All {max_attempts} Gemini attempts failed. Last error: {last_exception}"
    )


async def safe_ainvoke_groq(chain_builder_func, prompt_vars: dict, max_attempts: int = 4):
    """
    Safely invoke Groq with automatic key rotation and precise rate-limit backoffs.

    chain_builder_func must accept (api_key: str) and return a LangChain Runnable.
    """
    last_exception = None

    for attempt in range(max_attempts):
        key = LlmFactory.get_next_groq_key()
        masked_key = f"...{key[-4:]}" if len(key) >= 4 else "..."

        if attempt > 0:
            print(
                f"[Groq Retry] Attempt {attempt + 1}/{max_attempts} "
                f"— rotating to key ending in {masked_key}"
            )

        chain = chain_builder_func(key)

        try:
            return await chain.ainvoke(prompt_vars)
        except Exception as e:
            error_msg = str(e).lower()
            last_exception = e

            if "429" in error_msg or "rate limit" in error_msg:
                match = re.search(r"try again in ([\d\.]+)s", error_msg)
                sleep_time = float(match.group(1)) + 1.0 if match else 5.0
                print(
                    f"[Groq Rate Limit] Key {masked_key} exhausted. "
                    f"Waiting {sleep_time:.2f}s before next key..."
                )
                await asyncio.sleep(sleep_time)
            elif "503" in error_msg or "unavailable" in error_msg:
                print(f"[Groq Server Error] Service unavailable on {masked_key}. Waiting 3s...")
                await asyncio.sleep(3.0)
            else:
                raise e

    raise RateLimitError(
        f"All {max_attempts} Groq attempts failed. Last error: {last_exception}"
    )
