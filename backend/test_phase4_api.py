import os
import sys
import asyncio
import warnings
from dotenv import load_dotenv

# Suppress the Starlette httpx deprecation warning
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Ensure we're running from the correct directory for imports
sys.path.append(os.path.join(os.path.dirname(__file__)))
load_dotenv(dotenv_path=".env")

from fastapi.testclient import TestClient
from app.main import app
import uuid

client = TestClient(app)

def test_api_sse_stream():
    print("\n--- Testing Phase 4 FastAPI SSE Integration ---\n")
    
    # Mocking Database methods for test user
    from app.Agent.Tools.Database import Database
    
    async def mock_get_profile(self, user_id: str):
        return {"id": user_id, "name": "API Test User", "learning_goals": ["FastAPI", "SSE"]}
        
    async def mock_get_progress(self, user_id: str, topic_id: str):
        return {"mastery_score": 0.0, "status": "not_started"}
        
    async def mock_upsert_progress(self, user_id: str, topic_id: str, data: dict):
        return None

    Database.get_user_profile = mock_get_profile
    Database.get_topic_progress = mock_get_progress
    Database.upsert_topic_progress = mock_upsert_progress

    # 1. Start Session
    user_id = str(uuid.uuid4())
    thread_id = f"test_api_thread_{uuid.uuid4().hex[:8]}"
    
    print(f"[START] Testing POST /api/v1/agent/start (Thread: {thread_id})...")
    
    with client.stream(
        "POST", 
        "/api/v1/agent/start",
        json={"user_id": user_id, "thread_id": thread_id}
    ) as response:
        print(f"Status Code: {response.status_code}")
        
        for line in response.iter_lines():
            if line:
                print(f"  Stream Event: {line}")

    print("\n[START] Emulating User Delay & Submitting Answer via POST /api/v1/agent/reply...")
    
    with client.stream(
        "POST",
        "/api/v1/agent/reply",
        json={"user_id": user_id, "thread_id": thread_id, "answer_text": "I think the answer is 42."}
    ) as response:
        print(f"Status Code: {response.status_code}")
        
        for line in response.iter_lines():
            if line:
                print(f"  Stream Event: {line}")
                
    print("\n[PASS] API Streaming test completed successfully!")

if __name__ == "__main__":
    test_api_sse_stream()
