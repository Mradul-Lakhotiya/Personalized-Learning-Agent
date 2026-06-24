"""
RAGService — Retrieval-Augmented Generation layer.

Centralises all cache lookups so routes and GraphService never touch
Pinecone or the DB directly for content retrieval.

Priority order for node resources:
  1. Supabase `node_resources` table   (fastest — SQL)
  2. Pinecone `node_content` namespace (vector similarity)
  3. Content Swarm                      (slowest — 3 parallel API calls + Gemini)

Priority order for curriculum graph:
  1. Pinecone `curriculum_cache` namespace (similarity on goal text)
  2. Gemini CurriculumPlanner             (fresh generation)
"""

import asyncio
import json
from typing import Optional

from .Database import Database
from .VectorStore import VectorStore


class RAGService:

    # ── Node Resources ────────────────────────────────────────────────────────

    @staticmethod
    async def get_node_resources(
        node_slug: str,
        node_title: str,
        node_description: str = "",
    ) -> Optional[dict]:
        """
        Returns cached resources for a node slug, or None if not found.
        Checks Supabase DB first, then Pinecone vector similarity.

        Return shape:
        {
            "description": str,
            "resources": [{ "type", "title", "url", "why_relevant" }],
            "source": "db_cache" | "pinecone_cache"
        }
        """ 
        # 1. Supabase DB lookup (exact slug match — fastest)
        try:
            db = Database()
            cached = await db.get_node_resources(node_slug)
            if cached and cached.get("resources"):
                print(f"[RAGService] DB cache HIT for slug: '{node_slug}'")
                return {
                    "description": cached.get("description", node_description),
                    "resources":   cached["resources"],
                    "source":      "db_cache",
                }
        except Exception as e:
            print(f"[RAGService] DB lookup failed (non-fatal): {e}")

        # 2. Pinecone vector similarity (fuzzy match for similar topics)
        try:
            vs = VectorStore()
            query = f"{node_title} {node_description}".strip()
            matches = await vs.asearch(query, namespace="node_content", top_k=1)
            
            if matches:
                print(f"[RAGService] Pinecone top match score: {matches[0].get('score', 0)}")

            if matches and matches[0].get("score", 0) > 0.70:
                meta = matches[0].get("metadata", {})
                resources_json = meta.get("resources_json", "[]")
                resources = json.loads(resources_json) if isinstance(resources_json, str) else resources_json
                if resources:
                        print(f"[RAGService] Pinecone cache HIT for slug: '{node_slug}' "
                              f"(score={matches[0]['score']:.3f})")
                        return {
                            "description": meta.get("description", node_description),
                            "resources":   resources,
                            "source":      "pinecone_cache",
                        }
        except Exception as e:
            print(f"[RAGService] Pinecone lookup failed (non-fatal): {e}")

        # Cache miss — caller must run the swarm
        print(f"[RAGService] Cache MISS for slug: '{node_slug}' — swarm needed")
        return None

    @staticmethod
    async def save_node_resources(
        node_slug: str,
        title: str,
        description: str,
        resources: list,
        questions: list = None,
        thread_id: str = None,
    ) -> list:
        """
        Persist node resources to:
          1. Pinecone `node_content` namespace (vector)
          2. Supabase `node_resources` table (relational cache)

        Returns list of Pinecone vector IDs written.
        """
        pinecone_ids = []
        questions = questions or []

        # 1. Embed and upsert to Pinecone
        try:
            vs = VectorStore()
            # Embed ONLY the title and description (the query) so that future queries 
            # for similar topics will match this vector. The resources and questions 
            # are safely stored in the metadata payload.
            text = f"{title} {description}".strip()
            
            metadata = {
                "node_slug":      node_slug,
                "title":          title,
                "description":    description,
                "resources_json": json.dumps(resources),
                "questions_json": json.dumps(questions),
            }
            await vs.aupsert(texts=[text], metadatas=[metadata], namespace="node_content")
            print(f"[RAGService] Upserted node_content vector for '{node_slug}'")
        except Exception as e:
            print(f"[RAGService] Pinecone upsert failed (non-fatal): {e}")

        # 2. Persist to Supabase (User-Specific Path Nodes instead of Global Cache)
        try:
            if thread_id:
                db = Database()
                await db.cache_node_content_by_thread(
                    thread_id=thread_id,
                    node_id=node_slug,
                    resources=resources,
                    questions=questions,
                )
                print(f"[RAGService] Saved generated content to path_nodes for '{node_slug}' (Thread: {thread_id})")
            else:
                print(f"[RAGService] Skipping DB save: no thread_id provided for '{node_slug}'")
        except Exception as e:
            print(f"[RAGService] DB path_nodes save failed (non-fatal): {e}")

        return pinecone_ids

    # ── Curriculum Cache ──────────────────────────────────────────────────────

    @staticmethod
    async def get_curriculum_cache(learning_goal: str) -> Optional[dict]:
        """
        Search Pinecone `curriculum_cache` for a previously generated graph
        that matches this learning goal closely (cosine > 0.92).

        Returns the curriculum_graph dict on hit, or None on miss.
        """
        try:
            vs = VectorStore()
            matches = await vs.asearch(learning_goal, namespace="curriculum_cache", top_k=1)

            if matches and matches[0].get("score", 0) > 0.70:
                meta = matches[0].get("metadata", {})
                graph_json = meta.get("curriculum_graph_json")
                if graph_json:
                    graph = json.loads(graph_json) if isinstance(graph_json, str) else graph_json
                    print(f"[RAGService] Curriculum cache HIT for goal: '{learning_goal}' "
                          f"(score={matches[0]['score']:.3f})")
                    return graph
        except Exception as e:
            print(f"[RAGService] Curriculum cache lookup failed (non-fatal): {e}")

        print(f"[RAGService] Curriculum cache MISS for goal: '{learning_goal}'")
        return None

    @staticmethod
    async def save_curriculum_cache(learning_goal: str, curriculum_graph: dict):
        """
        Save a freshly generated curriculum graph to Pinecone `curriculum_cache`
        so future users with the same goal get an instant response.
        """
        try:
            vs = VectorStore()
            graph_json = json.dumps(curriculum_graph)
            # Only cache if the serialised graph fits in Pinecone metadata (< 40KB)
            if len(graph_json) > 38000:
                # Store a summary-only version (goal + section titles + node titles)
                summary = {
                    "goal": curriculum_graph.get("goal"),
                    "section_titles": curriculum_graph.get("section_titles", []),
                    "nodes": [
                        {"id": n["id"], "title": n["title"],
                         "section_number": n["section_number"],
                         "prerequisites": n["prerequisites"],
                         "difficulty": n["difficulty"],
                         "estimated_minutes": n["estimated_minutes"],
                         "is_major": n["is_major"],
                         "status": "locked"}  # reset status for reuse
                        for n in curriculum_graph.get("nodes", [])
                    ],
                    "edges": curriculum_graph.get("edges", []),
                }
                graph_json = json.dumps(summary)

            await vs.aupsert(
                texts=[learning_goal],
                metadatas=[{
                    "learning_goal":         learning_goal,
                    "node_count":            len(curriculum_graph.get("nodes", [])),
                    "curriculum_graph_json": graph_json,
                }],
                namespace="curriculum_cache",
            )
            print(f"[RAGService] Cached curriculum graph for goal: '{learning_goal}'")
        except Exception as e:
            print(f"[RAGService] Curriculum cache save failed (non-fatal): {e}")
