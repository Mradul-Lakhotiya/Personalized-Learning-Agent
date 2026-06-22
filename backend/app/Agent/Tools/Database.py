import os
import asyncio
from datetime import datetime, timezone
from supabase import create_client, Client


class Database:
    """
    Wrapper for all Supabase operations.
    Uses asyncio.to_thread() since supabase-py is synchronous.

    Live tables (as of latest migration):
        user_profiles     — core auth + onboarding data
        sessions          — session history (written by MemoryConsolidator)
        learning_paths    — one row per learning path / LangGraph thread
        path_nodes        — one row per node per path
        survey_responses  — self-assessment answers
        node_resources    — shared swarm-generated resource cache per topic slug
    """

    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL or SUPABASE_SERVICE_KEY is not set.")
        self.client: Client = create_client(url, key)

    # ── User Profile ──────────────────────────────────────────────────────────

    async def get_user_profile(self, user_id: str) -> dict:
        r = await asyncio.to_thread(
            self.client.table("user_profiles").select("*").eq("id", user_id).execute
        )
        return r.data[0] if r.data else {}

    # ── Learning Paths ────────────────────────────────────────────────────────

    async def get_learning_path(self, thread_id: str) -> dict:
        r = await asyncio.to_thread(
            self.client.table("learning_paths").select("*").eq("thread_id", thread_id).execute
        )
        return r.data[0] if r.data else {}

    async def save_learning_path(
        self,
        thread_id: str,
        user_id: str,
        learning_goal: str,
        skill_ratings: dict = None,
        curriculum_graph: dict = None,
        phase: str = "onboarding",
    ) -> str:
        """Upsert a learning path. Returns the path UUID."""
        payload = {
            "thread_id": thread_id,
            "user_id": user_id,
            "learning_goal": learning_goal,
            "skill_ratings": skill_ratings or {},
            "phase": phase,
        }
        if curriculum_graph:
            nodes = curriculum_graph.get("nodes", [])
            payload["curriculum_graph"] = curriculum_graph
            payload["sections_generated"] = len(curriculum_graph.get("section_titles", []))
            payload["completed_node_ids"] = [
                n["id"] for n in nodes if n.get("status") == "completed"
            ]
        r = await asyncio.to_thread(
            self.client.table("learning_paths")
                .upsert(payload, on_conflict="thread_id")
                .execute
        )
        return r.data[0]["id"] if r.data else ""

    # ── Path Nodes ────────────────────────────────────────────────────────────

    async def save_path_nodes(self, path_id: str, user_id: str, nodes: list):
        """Bulk upsert all nodes for a path."""
        if not nodes:
            return
        payloads = [
            {
                "path_id":            path_id,
                "user_id":            user_id,
                "node_id":            n["id"],
                "title":              n["title"],
                "description":        n.get("description", ""),
                "section_number":     n.get("section_number", 1),
                "section_title":      n.get("section", ""),
                "difficulty":         n.get("difficulty", 1),
                "estimated_minutes":  n.get("estimated_minutes", 30),
                "is_major":           n.get("is_major", False),
                "prerequisites":      n.get("prerequisites", []),
                "status":             n.get("status", "locked"),
            }
            for n in nodes
        ]
        await asyncio.to_thread(
            self.client.table("path_nodes")
                .upsert(payloads, on_conflict="path_id,node_id")
                .execute
        )

    async def cache_node_content_by_thread(self, thread_id: str, node_id: str, resources: list, questions: list):
        """Store fetched resources and questions directly on a path_node row using thread_id."""
        # 1. Lookup the path UUID
        r = await asyncio.to_thread(
            self.client.table("learning_paths").select("id").eq("thread_id", thread_id).execute
        )
        if not r.data:
            return
        
        path_id = r.data[0]["id"]

        # 2. Update path_nodes
        await asyncio.to_thread(
            self.client.table("path_nodes")
                .update({"resources_cached": resources, "questions_cached": questions})
                .eq("path_id", path_id)
                .eq("node_id", node_id)
                .execute
        )

    # ── Survey Responses ──────────────────────────────────────────────────────

    async def save_survey_response(
        self, path_id: str, user_id: str, topic: str, question: str, rating: int
    ):
        await asyncio.to_thread(
            self.client.table("survey_responses").insert({
                "path_id":  path_id,
                "user_id":  user_id,
                "topic":    topic,
                "question": question,
                "rating":   rating,
            }).execute
        )

    # ── Node Resources (shared cache) ─────────────────────────────────────────

    async def get_node_resources(self, node_slug: str) -> dict | None:
        r = await asyncio.to_thread(
            self.client.table("node_resources")
                .select("*")
                .eq("node_slug", node_slug)
                .execute
        )
        return r.data[0] if r.data else None

    async def save_node_resources(
        self,
        node_slug: str,
        title: str,
        description: str,
        resources: list,
        questions: list = None,
        pinecone_ids: list = None,
    ):
        await asyncio.to_thread(
            self.client.table("node_resources")
                .upsert({
                    "node_slug":    node_slug,
                    "title":        title,
                    "description":  description,
                    "resources":    resources,
                    "questions":    questions or [],
                    "pinecone_ids": pinecone_ids or [],
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                }, on_conflict="node_slug")
                .execute
        )

    # ── Sessions (MemoryConsolidator) ─────────────────────────────────────────

    async def save_session(self, session_id: str, user_id: str, summary: str, topics: list):
        await asyncio.to_thread(
            self.client.table("sessions").upsert({
                "id":             session_id,
                "user_id":        user_id,
                "summary":        summary,
                "topics_covered": topics,
                "ended_at":       datetime.now(timezone.utc).isoformat(),
            }).execute
        )
