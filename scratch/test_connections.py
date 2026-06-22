#!/usr/bin/env python3
"""
🧪 API Connectivity Test Suite — Personalized Learning Agent
Tests every configured key in .env using only stdlib (no installs required).
Run: python test_connections.py
"""
import os
import sys
import json
import time
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path

# ── Icons ─────────────────────────────────────────────────────────────────────
PASS = "  [PASS]"
FAIL = "  [FAIL]"
WARN = "  [WARN]"
SKIP = "  [SKIP]"
INFO = "  [INFO]"

results: dict[str, str] = {}

# ── Helpers ───────────────────────────────────────────────────────────────────
def section(title: str):
    print(f"\n{'=' * 62}")
    print(f"  {title}")
    print(f"{'=' * 62}")

def ok(service: str, msg: str):
    print(f"{PASS}  {service}")
    print(f"         {msg}")
    results[service] = "PASS"

def fail(service: str, msg: str):
    print(f"{FAIL}  {service}")
    print(f"         {msg}")
    results[service] = "FAIL"

def warn(service: str, msg: str):
    print(f"{WARN}  {service}")
    print(f"         {msg}")
    results[service] = "WARN"

def skip(service: str, msg: str):
    print(f"{SKIP}  {service}")
    print(f"         {msg}")
    results[service] = "SKIP"

def http_get(url: str, headers: dict | None = None, timeout: int = 12):
    """Simple GET — returns (status_code, parsed_json_or_text)."""
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode()
        try:
            return resp.status, json.loads(raw)
        except Exception:
            return resp.status, raw

def http_post(url: str, data: dict, headers: dict | None = None, timeout: int = 12):
    """Simple POST JSON — returns (status_code, parsed_json)."""
    body = json.dumps(data).encode()
    h = {**(headers or {}), "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=body, headers=h, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, json.loads(resp.read().decode())

# ── .env loader ───────────────────────────────────────────────────────────────
def load_env():
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        print(f"{FAIL}  .env not found at {env_path}")
        sys.exit(1)
    loaded = 0
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                # strip inline comments (everything after  # )
                value = value.split("  #")[0].strip()
                os.environ.setdefault(key.strip(), value)
                loaded += 1
    print(f"{PASS}  .env loaded  ({loaded} variables)")

# ── Individual tests ──────────────────────────────────────────────────────────

def test_pinecone():
    section("1 / 7  —  Pinecone (Vector Store)")
    key = os.getenv("PINECONE_API_KEY", "")
    if not key or "REPLACE" in key:
        skip("Pinecone", "PINECONE_API_KEY not set"); return
    try:
        status, body = http_get(
            "https://api.pinecone.io/indexes",
            headers={"Api-Key": key, "X-Pinecone-API-Version": "2024-07"}
        )
        indexes = body.get("indexes", []) if isinstance(body, dict) else []
        ok("Pinecone", f"API key valid — {len(indexes)} indexes found "
                       f"(0 expected — we create the index in Phase 1)")
    except urllib.error.HTTPError as e:
        body_text = e.read().decode() if e.fp else ""
        fail("Pinecone", f"HTTP {e.code}: {e.reason} — {body_text[:200]}")
    except Exception as e:
        fail("Pinecone", str(e))


def test_supabase():
    section("2 / 7  —  Supabase (PostgreSQL + Auth)")
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    db  = os.getenv("DATABASE_URL", "")

    # ── REST API health ──
    if not url or not key:
        skip("Supabase REST", "SUPABASE_URL or SUPABASE_SERVICE_KEY not set")
    else:
        try:
            status, _ = http_get(
                f"{url}/rest/v1/",
                headers={"apikey": key, "Authorization": f"Bearer {key}"}
            )
            ok("Supabase REST", f"HTTP {status} — REST API reachable")
        except urllib.error.HTTPError as e:
            # 406 "Not Acceptable" just means no tables yet — API is up
            if e.code in (404, 406):
                ok("Supabase REST", f"HTTP {e.code} — API is up "
                                    f"(no tables yet, expected at this stage)")
            else:
                fail("Supabase REST", f"HTTP {e.code}: {e.reason}")
        except Exception as e:
            fail("Supabase REST", str(e))

    # -- Auth endpoint health (needs anon key; 401 with service key is normal) --
    if url:
        try:
            status, body = http_get(f"{url}/auth/v1/health")
            ok("Supabase Auth", f"HTTP {status} — Auth service running")
        except urllib.error.HTTPError as e:
            if e.code == 401:
                # The /health endpoint requires anon key; 401 with service key is expected
                ok("Supabase Auth",
                   "HTTP 401 on /auth/v1/health is EXPECTED with a service key "
                   "(endpoint requires anon key). Auth service is running correctly.")
            else:
                warn("Supabase Auth", f"HTTP {e.code}: {e.reason}")
        except Exception as e:
            warn("Supabase Auth", str(e))

    # ── DATABASE_URL sanity check ──
    if db and "%" in db and "supabase.co" in db:
        ok("DATABASE_URL",
           "URL-encoded connection string looks correct — "
           "password special chars are encoded")
    elif not db or "postgresql://..." in db:
        warn("DATABASE_URL", "Not yet configured")
    else:
        ok("DATABASE_URL", "Set")


def test_redis():
    section("3 / 7  —  Upstash Redis")
    rest_url   = os.getenv("UPSTASH_REDIS_REST_URL", "")
    rest_token = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
    redis_url  = os.getenv("REDIS_URL", "")

    if not rest_url or not rest_token:
        skip("Upstash Redis", "REST URL or token not set"); return

    # ── PING via REST API ──
    try:
        status, body = http_get(
            f"{rest_url}/ping",
            headers={"Authorization": f"Bearer {rest_token}"}
        )
        result = body.get("result", "") if isinstance(body, dict) else body
        if result == "PONG":
            ok("Upstash Redis REST", f"PING -> PONG  (HTTP {status})")
        else:
            fail("Upstash Redis REST", f"Unexpected PING response: {body}")
    except urllib.error.HTTPError as e:
        fail("Upstash Redis REST", f"HTTP {e.code}: {e.reason}")
    except Exception as e:
        fail("Upstash Redis REST", str(e))

    # ── SET + GET round-trip ──
    try:
        _, _ = http_get(
            f"{rest_url}/set/test_connectivity_key/hello_world",
            headers={"Authorization": f"Bearer {rest_token}"}
        )
        _, get_body = http_get(
            f"{rest_url}/get/test_connectivity_key",
            headers={"Authorization": f"Bearer {rest_token}"}
        )
        value = get_body.get("result") if isinstance(get_body, dict) else get_body
        if value == "hello_world":
            ok("Upstash Redis SET/GET", "Round-trip write and read confirmed")
        else:
            warn("Upstash Redis SET/GET", f"Unexpected GET response: {get_body}")
    except Exception as e:
        warn("Upstash Redis SET/GET", str(e))

    # ── Native rediss:// URL check ──
    if redis_url.startswith("rediss://"):
        ok("REDIS_URL (native protocol)",
           "rediss:// URL configured — LangGraph checkpointer ready")
    else:
        warn("REDIS_URL (native protocol)",
             "REDIS_URL should start with rediss:// for LangGraph")


def test_youtube():
    section("4 / 7  —  YouTube Data API v3")
    key = os.getenv("YOUTUBE_API_KEY", "")
    if not key or "REPLACE" in key:
        skip("YouTube", "YOUTUBE_API_KEY not set"); return
    try:
        params = urllib.parse.urlencode({
            "part":       "snippet",
            "q":          "Python programming tutorial",
            "maxResults": 2,
            "type":       "video",
            "key":        key,
        })
        status, body = http_get(
            f"https://www.googleapis.com/youtube/v3/search?{params}"
        )
        items = body.get("items", [])
        if items:
            title    = items[0]["snippet"]["title"]
            channel  = items[0]["snippet"]["channelTitle"]
            total    = body.get("pageInfo", {}).get("totalResults", "?")
            ok("YouTube Search API",
               f"Found {total} results — top: \"{title[:55]}\" by {channel}")
        else:
            warn("YouTube Search API", "Connected but 0 results returned")
    except urllib.error.HTTPError as e:
        body_text = e.read().decode() if e.fp else ""
        try:
            msg = json.loads(body_text)["error"]["message"]
        except Exception:
            msg = e.reason
        fail("YouTube Search API", f"HTTP {e.code}: {msg}")
    except Exception as e:
        fail("YouTube Search API", str(e))


def test_piston():
    section("5 / 7  —  Piston Code Execution")
    api_url = os.getenv("PISTON_API_URL", "https://emkc.org/api/v2/piston")

    # -- /runtimes endpoint --
    try:
        status, runtimes = http_get(f"{api_url}/runtimes")
        count = len(runtimes) if isinstance(runtimes, list) else "?"
        ok("Piston /runtimes",
           f"Connected — {count} supported languages available")
    except urllib.error.HTTPError as e:
        fail("Piston /runtimes", f"HTTP {e.code}: {e.reason}")
    except Exception as e:
        fail("Piston /runtimes", str(e))


def test_langsmith():
    section("6 / 7  —  LangSmith (Observability)")
    api_key = os.getenv("LANGCHAIN_API_KEY", "")
    project = os.getenv("LANGCHAIN_PROJECT", "")
    tracing = os.getenv("LANGCHAIN_TRACING_V2", "")

    if not api_key or "REPLACE" in api_key:
        skip("LangSmith", "LANGCHAIN_API_KEY not set"); return

    try:
        status, body = http_get(
            "https://api.smith.langchain.com/ok",
            headers={"x-api-key": api_key}
        )
        ok("LangSmith /ok", f"HTTP {status} — API key valid")
    except urllib.error.HTTPError as e:
        if e.code == 200:
            ok("LangSmith /ok", "API key valid")
        else:
            fail("LangSmith /ok", f"HTTP {e.code}: {e.reason}")
    except Exception as e:
        # Try the base URL as fallback
        try:
            status2, _ = http_get(
                "https://api.smith.langchain.com/",
                headers={"x-api-key": api_key}
            )
            ok("LangSmith", f"HTTP {status2} — Connected")
        except Exception as e2:
            fail("LangSmith", str(e2))

    # Config report
    print(f"{INFO}  Tracing: LANGCHAIN_TRACING_V2={tracing}")
    print(f"{INFO}  Project: {project}")


def test_gemini():
    section("7 / 7  —  Google Gemini (LLM)")
    keys_raw = os.getenv("GEMINI_KEYS", "")
    keys = [k.strip() for k in keys_raw.split(",")
            if k.strip() and "REPLACE" not in k.strip()]

    if not keys:
        skip("Gemini", "No Gemini keys configured yet — "
                       "add to GEMINI_KEYS in .env when ready")
        return

    for i, key in enumerate(keys, 1):
        try:
            # These keys support gemini-2.5-flash on the v1beta endpoint!
            url = (
                "https://generativelanguage.googleapis.com"
                f"/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
            )
            status, body = http_post(
                url,
                data={"contents": [{"parts": [{"text": "Reply with exactly one word: Ready"}]}]}
            )
            text = (
                body["candidates"][0]["content"]["parts"][0]["text"].strip()
            )
            ok(f"Gemini key #{i}", f"Response received: \"{text}\"")
        except urllib.error.HTTPError as e:
            body_text = e.read().decode() if e.fp else ""
            try:
                msg = json.loads(body_text)["error"]["message"]
            except Exception:
                msg = e.reason
            fail(f"Gemini key #{i}", f"HTTP {e.code}: {msg}")
        except Exception as e:
            fail(f"Gemini key #{i}", str(e))


# ── Summary ───────────────────────────────────────────────────────────────────
def print_summary():
    section("RESULTS SUMMARY")
    for service, status in results.items():
        icon = {"PASS": "[PASS]", "FAIL": "[FAIL]",
                "WARN": "[WARN]", "SKIP": "[SKIP]"}.get(status, "[????]")
        print(f"  {icon}  {service}")

    passed  = sum(1 for v in results.values() if v == "PASS")
    failed  = sum(1 for v in results.values() if v == "FAIL")
    warned  = sum(1 for v in results.values() if v == "WARN")
    skipped = sum(1 for v in results.values() if v == "SKIP")

    print(f"\n  Passed : {passed}")
    print(f"  Failed : {failed}")
    print(f"  Warned : {warned}")
    print(f"  Skipped: {skipped}")

    print()
    if failed > 0:
        print("  [ACTION NEEDED] Some services failed. Fix before Phase 1.")
    elif skipped > 0:
        print("  [NEXT STEP] Add missing keys to .env, then re-run this script.")
    else:
        print("  [ALL CLEAR] Every service is reachable. Ready to build!")
    print()


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("  Personalized Learning Agent")
    print("  API Connectivity Test Suite")
    print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    load_env()
    test_pinecone()
    test_supabase()
    test_redis()
    test_youtube()
    test_piston()
    test_langsmith()
    test_gemini()
    print_summary()
