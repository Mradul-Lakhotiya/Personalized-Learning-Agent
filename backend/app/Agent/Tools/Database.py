import os
import asyncio
from supabase import create_client, Client

class Database:
    """
    Wrapper for Supabase database operations.
    Uses asyncio.to_thread to prevent blocking the event loop since
    the standard supabase-py client is synchronous.
    """
    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL or SUPABASE_SERVICE_KEY is not set.")
        self.client: Client = create_client(url, key)

    async def get_user_profile(self, user_id: str) -> dict:
        """Fetch user profile."""
        response = await asyncio.to_thread(
            self.client.table("user_profiles").select("*").eq("id", user_id).execute
        )
        data = response.data
        return data[0] if data else {}

    async def update_user_profile(self, user_id: str, updates: dict):
        """Update user profile."""
        await asyncio.to_thread(
            self.client.table("user_profiles").update(updates).eq("id", user_id).execute
        )

    async def get_topic_progress(self, user_id: str, topic_id: str) -> dict:
        """Fetch user progress for a specific topic."""
        response = await asyncio.to_thread(
            self.client.table("user_progress").select("*").eq("user_id", user_id).eq("topic_id", topic_id).execute
        )
        data = response.data
        return data[0] if data else None

    async def upsert_topic_progress(self, user_id: str, topic_id: str, data: dict):
        """Upsert user progress for a specific topic."""
        payload = {"user_id": user_id, "topic_id": topic_id, **data}
        await asyncio.to_thread(
            self.client.table("user_progress").upsert(payload, on_conflict="user_id,topic_id").execute
        )

    async def get_topic(self, topic_id: str) -> dict:
        """Fetch topic details."""
        response = await asyncio.to_thread(
            self.client.table("topics").select("*").eq("id", topic_id).execute
        )
        data = response.data
        return data[0] if data else {}

    async def get_or_create_topic(self, name: str, description: str = "") -> str:
        """Gets a topic by name, or creates it if it doesn't exist. Returns the UUID."""
        response = await asyncio.to_thread(
            self.client.table("topics").select("id").eq("name", name).execute
        )
        if response.data:
            return response.data[0]["id"]
            
        # Create it
        payload = {"name": name, "description": description}
        insert_resp = await asyncio.to_thread(
            self.client.table("topics").insert(payload).execute
        )
        return insert_resp.data[0]["id"]
