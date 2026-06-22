import re
from typing import List
from pydantic import BaseModel, Field
from ..LearnerState import LearnerState, LearningNode
from ..Tools.LlmFactory import safe_ainvoke_gemini
from ..Tools.RAGService import RAGService
from langchain_core.prompts import PromptTemplate


# ── Pydantic models for the graph output ─────────────────────────────────────

class GraphNode(BaseModel):
    id: str = Field(description="URL-safe slug, e.g. 'python-basics'. Lowercase, hyphens only.")
    title: str = Field(description="Human-readable topic name, e.g. 'Python Basics'")
    description: str = Field(description="1–2 sentence explanation of what this topic covers.")
    prerequisites: List[str] = Field(
        default=[],
        description="List of node IDs (slugs) that must be completed before this node."
    )
    difficulty: int = Field(description="Difficulty from 1 (beginner) to 5 (advanced).")
    estimated_minutes: int = Field(description="Estimated study time in minutes.")
    section_number: int = Field(description="Which section this node belongs to (1, 2, 3...).")
    is_major: bool = Field(
        description="True for foundational or complex topics that warrant curated resources."
    )


class LearningGraphOutput(BaseModel):
    goal: str = Field(description="The user's learning goal.")
    section_titles: List[str] = Field(
        description="Title for each section, e.g. ['Section 1: Foundations', 'Section 2: Core Concepts']"
    )
    nodes: List[GraphNode] = Field(
        description="All learning nodes organized into sections.",
        min_length=5,
        max_length=80,
    )


def _slugify(text: str) -> str:
    """Convert a title to a URL-safe slug."""
    return re.sub(r"[^a-z0-9-]", "", text.lower().replace(" ", "-"))


async def curriculum_planner_node(state: LearnerState) -> dict:
    """
    Node 2: Curriculum Planner (rewritten for visual graph generation)
    
    Takes the user's learning goal + self-assessment skill ratings and
    generates a full directed acyclic graph (DAG) of learning nodes,
    organized into sections. Nodes already known (rating >= 4) are
    auto-marked as 'completed'.
    
    Strategy:
    - Section 1 is always generated upfront.
    - If the topic is large (> 10 nodes needed), further sections are
      generated lazily when the user finishes the previous section.
    - Only ~30% of nodes are flagged `is_major=True` (core foundational
      and complex nodes that get curated resource links via the swarm).
    """
    profile = state.get("user_profile", {})
    skill_ratings = state.get("skill_ratings", {})
    learning_goal = state.get("learning_goal", "")

    if not learning_goal:
        goals = profile.get("learning_goals", [])
        learning_goal = goals[0] if goals else "General Programming"

    if not learning_goal:
        return {"error": "CurriculumPlanner requires a learning_goal in state"}

    # Build a human-readable summary of skill ratings for the prompt
    skill_summary = ""
    if skill_ratings:
        skill_lines = [
            f"  - {topic}: {rating}/5 ({'already knows' if rating >= 4 else 'needs to learn' if rating <= 1 else 'partial knowledge'})"
            for topic, rating in skill_ratings.items()
        ]
        skill_summary = "\n".join(skill_lines)
    else:
        skill_summary = "  - No self-assessment data available. Assume complete beginner."

    prompt = PromptTemplate.from_template(
        "You are an expert AI curriculum designer. Design a comprehensive, visual learning path.\n\n"
        "LEARNING GOAL: {goal}\n\n"
        "USER'S SELF-ASSESSED SKILL RATINGS (0=none, 5=expert):\n{skills}\n\n"
        "TASK: Generate a full learning path as a directed acyclic graph (DAG).\n\n"
        "RULES:\n"
        "1. Create 10-20 nodes total, organized into 2-4 logical sections.\n"
        "2. Each section should have 4-8 nodes covering a coherent theme.\n"
        "3. A node's prerequisites must be IDs of other nodes in your output.\n"
        "4. Nodes for topics where the user rated themselves 4 or 5 SHOULD still appear, "
        "   but mark them with difficulty 1 - the frontend will auto-complete them.\n"
        "5. Mark about 30% of nodes as is_major true - the most foundational or complex topics.\n"
        "6. IDs must be URL-safe slugs (lowercase, hyphens only, no spaces).\n"
        "7. Section titles should be descriptive, e.g. Section 1 Foundations.\n"
        "8. Estimated minutes per node: easy 15, medium 30, hard 60.\n\n"
        "OUTPUT FORMAT: Respond with ONLY a valid JSON object. No markdown, no explanation, no code fences.\n"
        "The JSON must have exactly this structure:\n"
        "{{\n"
        '  "goal": "<learning goal>",\n'
        '  "section_titles": ["Section 1: Name", "Section 2: Name"],\n'
        '  "nodes": [\n'
        "    {{\n"
        '      "id": "slug-here",\n'
        '      "title": "Topic Name",\n'
        '      "description": "1-2 sentence explanation.",\n'
        '      "prerequisites": [],\n'
        '      "difficulty": 1,\n'
        '      "estimated_minutes": 30,\n'
        '      "section_number": 1,\n'
        '      "is_major": true\n'
        "    }}\n"
        "  ]\n"
        "}}\n\n"
        "Generate a complete, coherent learning graph as JSON now:"
    )

    # ── 1. Check Pinecone curriculum cache first ─────────────────────────────
    # If a very similar goal was already planned, reuse that graph instantly.
    cached_graph = await RAGService.get_curriculum_cache(learning_goal)
    if cached_graph:
        nodes = cached_graph.get("nodes", [])
        # Re-apply skill ratings to auto-complete known nodes
        completed_set = set(state.get("completed_node_ids", []))
        for node in nodes:
            for skill_topic, rating in skill_ratings.items():
                if rating >= 4 and (
                    skill_topic.lower() in node["title"].lower()
                    or node["title"].lower() in skill_topic.lower()
                ):
                    node["status"] = "completed"
                    completed_set.add(node["id"])
        # Unlock available nodes
        for node in nodes:
            if node["status"] == "locked":
                prereqs = set(node.get("prerequisites", []))
                if not prereqs or prereqs.issubset(completed_set):
                    node["status"] = "available"
        cached_graph["nodes"] = nodes
        # Update edge animation
        for edge in cached_graph.get("edges", []):
            target = next((n for n in nodes if n["id"] == edge["target"]), None)
            edge["animated"] = target["status"] == "available" if target else False
        print(f"[CurriculumPlanner] Used curriculum cache for goal: '{learning_goal}'")
        return {
            "curriculum_graph": cached_graph,
            "completed_node_ids": list(completed_set),
            "sections_generated": len(cached_graph.get("section_titles", [])),
            "current_section": 1,
            "phase": "graph_ready",
            "session_complete": False,
            "error": "",
        }


    def build_chain(api_key: str):
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", temperature=0.3, google_api_key=api_key
        )
        # NOTE: Do NOT use with_structured_output — Gemini rejects complex nested
        # schemas (INVALID_ARGUMENT: too many constraint states). Parse JSON manually.
        return prompt | llm


    try:
        import json as _json
        import re as _re

        raw_response = await safe_ainvoke_gemini(
            build_chain,
            {"goal": learning_goal, "skills": skill_summary}
        )
        raw_text = raw_response.content if hasattr(raw_response, "content") else str(raw_response)

        # Strip markdown code fences if present
        clean = _re.sub(r"```(?:json)?\s*", "", raw_text).strip().rstrip("`").strip()

        # Try direct parse first
        data = None
        try:
            data = _json.loads(clean)
        except _json.JSONDecodeError:
            pass

        # Fall back: find the outermost { ... } block
        if data is None:
            match = _re.search(r'\{[\s\S]*\}', clean)
            if match:
                try:
                    data = _json.loads(match.group())
                except _json.JSONDecodeError:
                    pass

        if data is None:
            raise ValueError(
                f"CurriculumPlanner: Gemini returned non-JSON response.\n"
                f"First 300 chars: {raw_text[:300]}"
            )

        # Validate and coerce via Pydantic (schema only used for validation, not Gemini)
        result = LearningGraphOutput.model_validate(data)

        # ── Build section title lookup ────────────────────────────────────────
        section_map = {
            i + 1: title
            for i, title in enumerate(result.section_titles)
        }

        # ── Determine auto-completed nodes (user rated >= 4) ─────────────────
        auto_completed_ids = set()

        # ── Convert Pydantic nodes → state-ready dicts ────────────────────────
        nodes: List[LearningNode] = []
        for gn in result.nodes:
            # Ensure slug is clean
            node_id = _slugify(gn.id) or _slugify(gn.title)
            section_title = section_map.get(gn.section_number, f"Section {gn.section_number}")

            # Auto-complete if the user knows this topic (skill rating >= 4)
            matched_rating = None
            for skill_topic, rating in skill_ratings.items():
                if skill_topic.lower() in gn.title.lower() or gn.title.lower() in skill_topic.lower():
                    matched_rating = rating
                    break

            if matched_rating is not None and matched_rating >= 4:
                status = "completed"
                auto_completed_ids.add(node_id)
            else:
                status = "locked"  # Will be unlocked after computing available nodes

            nodes.append({
                "id": node_id,
                "title": gn.title,
                "description": gn.description,
                "prerequisites": [_slugify(p) for p in gn.prerequisites],
                "difficulty": gn.difficulty,
                "estimated_minutes": gn.estimated_minutes,
                "section": section_title,
                "section_number": gn.section_number,
                "is_major": gn.is_major,
                "status": status,
            })

        # ── Compute available nodes (all prerequisites completed) ─────────────
        completed_set = auto_completed_ids | set(state.get("completed_node_ids", []))
        valid_node_ids = {n["id"] for n in nodes}
        for node in nodes:
            if node["status"] == "locked":
                valid_prereqs = {p for p in node["prerequisites"] if p in valid_node_ids}
                if not valid_prereqs or valid_prereqs.issubset(completed_set):
                    node["status"] = "available"

        # ── Build edges list for React Flow ──────────────────────────────────
        edges = []
        for node in nodes:
            for prereq_id in node["prerequisites"]:
                edges.append({
                    "id": f"e-{prereq_id}-{node['id']}",
                    "source": prereq_id,
                    "target": node["id"],
                    "type": "smoothstep",
                    "animated": node["status"] == "available",
                })

        curriculum_graph = {
            "goal": result.goal,
            "section_titles": result.section_titles,
            "nodes": nodes,
            "edges": edges,
        }

        print(f"[CurriculumPlanner] Generated graph: {len(nodes)} nodes, {len(edges)} edges")
        print(f"[CurriculumPlanner] Auto-completed nodes: {auto_completed_ids}")

        # ── Save to Pinecone curriculum cache (async, non-blocking) ──────────
        import asyncio
        asyncio.create_task(RAGService.save_curriculum_cache(learning_goal, curriculum_graph))

        return {
            "curriculum_graph": curriculum_graph,
            "completed_node_ids": list(completed_set),
            "sections_generated": len(result.section_titles),
            "current_section": 1,
            "phase": "graph_ready",
            "session_complete": False,
            "error": "",
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": f"CurriculumPlanner failed: {str(e)}"}
