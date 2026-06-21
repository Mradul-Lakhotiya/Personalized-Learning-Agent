"""
backend_integration_test.py
============================
Comprehensive end-to-end integration test for the Personalized Learning Agent backend.

Tests:
  1.  Environment & imports
  2.  Supabase connection
  3.  Supabase schema (all tables exist)
  4.  User profile read/write
  5.  Topic creation (get_or_create_topic)
  6.  Staging question write (QualityGate)
  7.  Staging question Pinecone upsert (questions_staging namespace)
  8.  Pinecone content namespace upsert (VectorIngestionGate simulation)
  9.  Pinecone content namespace search
  10. Pinecone questions namespace search (verified pool)
  11. Groq LLM connectivity (llama-3.3-70b-versatile)
  12. Gemini LLM connectivity (gemini-2.5-flash)
  13. KnowledgeAssessor node (end-to-end question generation + staging write)
  14. AnswerEvaluator node (MCQ exact match path)
  15. AnswerEvaluator node (open-ended Groq grading path)
  16. QualityGate promotion flow (simulate correct answer on staged question)
  17. VectorIngestionGate node (chunk + embed + upsert)
  18. CurriculumPlanner node (Gemini topic selection)
  19. PathRerouter node (EMA mastery update)
  20. Full graph: profile_builder → curriculum_planner → knowledge_assessor interrupt

Usage:
    cd backend
    python -m venv venv  # if not already done
    .\\venv\\Scripts\\activate
    pip install -r requirements.txt
    python backend_integration_test.py

Set TEST_USER_ID to a real user UUID from your Supabase auth.users table.
"""

import asyncio
import os
import sys
import traceback
from dotenv import load_dotenv

# ── Load env ──────────────────────────────────────────────────────────────────
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

# ── Test configuration ────────────────────────────────────────────────────────
# Replace this with a real user UUID from your Supabase auth.users table
TEST_USER_ID  = os.getenv("TEST_USER_ID", "00000000-0000-0000-0000-000000000001")
TEST_TOPIC    = "Python List Comprehensions"
TEST_THREAD   = "test-thread-integration-001"

# ── Colour helpers ────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

passed = []
failed = []

def ok(name: str, detail: str = ""):
    passed.append(name)
    suffix = f"  {YELLOW}→ {detail}{RESET}" if detail else ""
    print(f"  {GREEN}✓{RESET} {name}{suffix}")

def fail(name: str, err):
    failed.append(name)
    print(f"  {RED}✗{RESET} {name}")
    print(f"    {RED}{err}{RESET}")

def section(title: str):
    print(f"\n{BOLD}{CYAN}{'─'*60}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'─'*60}{RESET}")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST SUITE
# ═══════════════════════════════════════════════════════════════════════════════

async def test_01_environment():
    section("01 — Environment & Imports")
    required_vars = [
        "SUPABASE_URL", "SUPABASE_SERVICE_KEY",
        "PINECONE_API_KEY", "PINECONE_INDEX_NAME",
        "GEMINI_KEYS", "GROQ_KEYS",
    ]
    for var in required_vars:
        val = os.getenv(var, "")
        if val:
            ok(f"ENV: {var}", f"...{val[-6:]}")
        else:
            fail(f"ENV: {var}", "Not set!")

    # Test imports
    try:
        import langchain_groq
        ok("Import: langchain_groq")
    except ImportError as e:
        fail("Import: langchain_groq", e)

    try:
        import langchain_google_genai
        ok("Import: langchain_google_genai")
    except ImportError as e:
        fail("Import: langchain_google_genai", e)

    try:
        import pinecone
        ok("Import: pinecone")
    except ImportError as e:
        fail("Import: pinecone", e)


async def test_02_supabase_connection():
    section("02 — Supabase Connection")
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))
        from app.Agent.Tools.Database import Database
        db = Database()
        ok("Supabase client created")

        # Ping with a lightweight query
        resp = await asyncio.to_thread(
            db.client.table("topics").select("id").limit(1).execute
        )
        ok("Supabase query succeeded", f"{len(resp.data)} rows returned")
        return db
    except Exception as e:
        fail("Supabase connection", e)
        return None


async def test_03_schema_tables(db):
    section("03 — Schema Tables Exist")
    if not db:
        fail("Schema check", "No DB connection")
        return

    required_tables = [
        "user_profiles", "topics", "user_progress",
        "sessions", "staging_questions", "answered_questions",
        "skill_map", "curricula", "user_subscriptions",
    ]
    for table in required_tables:
        try:
            resp = await asyncio.to_thread(
                db.client.table(table).select("*").limit(0).execute
            )
            ok(f"Table: {table}")
        except Exception as e:
            fail(f"Table: {table}", e)


async def test_04_user_profile(db):
    section("04 — User Profile Operations")
    if not db:
        fail("User profile", "No DB connection")
        return

    try:
        profile = await db.get_user_profile(TEST_USER_ID)
        if profile:
            ok("get_user_profile", f"name={profile.get('name', 'N/A')}")
        else:
            print(f"  {YELLOW}⚠ No profile found for TEST_USER_ID={TEST_USER_ID}. "
                  f"Some downstream tests may fail.{RESET}")
    except Exception as e:
        fail("get_user_profile", e)


async def test_05_topic_creation(db):
    section("05 — Topic Creation")
    if not db:
        fail("Topic creation", "No DB connection")
        return None

    try:
        topic_id = await db.get_or_create_topic(TEST_TOPIC, "Test topic created by integration test")
        ok("get_or_create_topic", f"id={topic_id[:8]}...")
        return topic_id
    except Exception as e:
        fail("get_or_create_topic", e)
        return None


async def test_06_staging_question_write():
    section("06 — Staging Question Write (QualityGate)")
    try:
        from app.Agent.Tools.QualityGate import write_question_to_staging
        row = await write_question_to_staging(
            topic=TEST_TOPIC,
            subtopic="basic syntax",
            question_type="open_ended",
            question_text="What is a list comprehension in Python and when should you use it?",
            expected_answer="A concise way to create lists using a single line with optional filtering.",
            options=[],
        )
        staging_id = row.get("staging_id", "")
        ok("write_question_to_staging", f"staging_id={staging_id[:8]}...")
        return staging_id
    except Exception as e:
        fail("write_question_to_staging", e)
        traceback.print_exc()
        return None


async def test_07_pinecone_staging_upsert():
    section("07 — Pinecone questions_staging Namespace")
    try:
        from app.Agent.Tools.VectorStore import VectorStore
        vs = VectorStore()
        await vs.aupsert(
            texts=["What is a list comprehension? A concise way to create lists."],
            metadatas=[{"topic": TEST_TOPIC, "type": "open_ended", "status": "staging", "staging_id": "test-staging-001"}],
            namespace="questions_staging"
        )
        ok("Pinecone upsert → questions_staging")
    except Exception as e:
        fail("Pinecone upsert → questions_staging", e)


async def test_08_pinecone_content_upsert():
    section("08 — Pinecone content Namespace Upsert")
    try:
        from app.Agent.Tools.VectorStore import VectorStore
        vs = VectorStore()
        await vs.aupsert(
            texts=[
                "List comprehensions provide a concise way to create lists in Python.",
                "Syntax: [expression for item in iterable if condition]",
                "Example: squares = [x**2 for x in range(10)]",
            ],
            metadatas=[
                {"topic": TEST_TOPIC, "chunk_index": 0, "source_urls": ["https://docs.python.org"]},
                {"topic": TEST_TOPIC, "chunk_index": 1, "source_urls": ["https://docs.python.org"]},
                {"topic": TEST_TOPIC, "chunk_index": 2, "source_urls": ["https://docs.python.org"]},
            ],
            namespace="content"
        )
        ok("Pinecone upsert → content (3 chunks)")
    except Exception as e:
        fail("Pinecone upsert → content", e)


async def test_09_pinecone_content_search():
    section("09 — Pinecone content Namespace Search")
    try:
        from app.Agent.Tools.VectorStore import VectorStore
        vs = VectorStore()
        results = await vs.asearch(
            query=f"lesson about {TEST_TOPIC}",
            namespace="content",
            top_k=3
        )
        if results:
            ok("Pinecone search → content", f"{len(results)} matches, top score={results[0].get('score', 0):.3f}")
        else:
            print(f"  {YELLOW}⚠ No results (index may need a moment to index){RESET}")
    except Exception as e:
        fail("Pinecone search → content", e)


async def test_10_pinecone_questions_search():
    section("10 — Pinecone questions Namespace Search (Verified Pool)")
    try:
        from app.Agent.Tools.VectorStore import VectorStore
        vs = VectorStore()
        results = await vs.asearch(
            query=f"Assessment question about {TEST_TOPIC}",
            namespace="questions",
            top_k=3
        )
        ok("Pinecone search → questions", f"{len(results)} verified questions found")
    except Exception as e:
        fail("Pinecone search → questions", e)


async def test_11_groq_connectivity():
    section("11 — Groq LLM Connectivity")
    try:
        from app.Agent.Tools.LlmFactory import safe_ainvoke_groq
        from langchain_core.messages import HumanMessage

        def build_chain(api_key: str):
            from langchain_groq import ChatGroq
            return ChatGroq(model="llama-3.3-70b-versatile", temperature=0.0, groq_api_key=api_key)

        result = await safe_ainvoke_groq(build_chain, [HumanMessage(content="Reply with exactly: GROQ_OK")])
        content = result.content if hasattr(result, "content") else str(result)
        ok("Groq LLM response", content[:40].replace("\n", " "))
    except Exception as e:
        fail("Groq LLM connectivity", e)


async def test_12_gemini_connectivity():
    section("12 — Gemini LLM Connectivity")
    try:
        from app.Agent.Tools.LlmFactory import safe_ainvoke_gemini
        from langchain_core.messages import HumanMessage

        def build_chain(api_key: str):
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.0, google_api_key=api_key)

        result = await safe_ainvoke_gemini(build_chain, [HumanMessage(content="Reply with exactly: GEMINI_OK")])
        content = result.content if hasattr(result, "content") else str(result)
        ok("Gemini LLM response", content[:40].replace("\n", " "))
    except Exception as e:
        fail("Gemini LLM connectivity", e)


async def test_13_knowledge_assessor():
    section("13 — KnowledgeAssessor Node (End-to-End)")
    try:
        from app.Agent.Nodes.KnowledgeAssessor import knowledge_assessor_node
        state = {
            "user_id": TEST_USER_ID,
            "session_id": TEST_THREAD,
            "current_topic": TEST_TOPIC,
            "current_subtopic": "",
            "current_topic_id": "test-topic-id",
            "answered_questions": [],
            "loop_counters": {},
            "error": "",
        }
        result = await knowledge_assessor_node(state)

        if result.get("error"):
            fail("KnowledgeAssessor", result["error"])
            return None

        q = result.get("current_question", {})
        ok("KnowledgeAssessor returned question", f"type={q.get('type')}, source={q.get('source')}")
        print(f"    Question: {q.get('text', '')[:80]}...")
        if q.get("staging_id"):
            print(f"    staging_id: {q['staging_id'][:8]}...")
        return q
    except Exception as e:
        fail("KnowledgeAssessor", e)
        traceback.print_exc()
        return None


async def test_14_answer_evaluator_mcq():
    section("14 — AnswerEvaluator (MCQ exact-match, no LLM)")
    try:
        from app.Agent.Nodes.AnswerEvaluator import answer_evaluator_node
        state = {
            "current_question": {
                "type": "mcq",
                "text": "What does [x**2 for x in range(5)] produce?",
                "options": ["[0, 1, 4, 9, 16]", "[1, 4, 9, 16, 25]", "[0, 2, 4, 6, 8]", "[0, 1, 2, 3, 4]"],
                "expected": "[0, 1, 4, 9, 16]",
                "topic": TEST_TOPIC,
                "source": "cache",
                "staging_id": None,
            },
            "user_answer": "[0, 1, 4, 9, 16]",
            "answered_questions": [],
            "current_topic": TEST_TOPIC,
            "error": "",
        }
        result = await answer_evaluator_node(state)
        eval_data = result.get("evaluation", {})
        score = eval_data.get("score", -1)
        ok("MCQ correct answer", f"score={score} (expected 1.0)")
        assert score == 1.0, f"Expected 1.0, got {score}"

        # Test wrong answer
        state["user_answer"] = "wrong answer"
        result2 = await answer_evaluator_node(state)
        score2 = result2.get("evaluation", {}).get("score", -1)
        ok("MCQ wrong answer", f"score={score2} (expected 0.0)")
        assert score2 == 0.0, f"Expected 0.0, got {score2}"
    except Exception as e:
        fail("AnswerEvaluator MCQ", e)
        traceback.print_exc()


async def test_15_answer_evaluator_open(generated_question):
    section("15 — AnswerEvaluator (Open-ended, Groq grading)")
    if not generated_question:
        print(f"  {YELLOW}⚠ Skipped — no generated question from test 13{RESET}")
        return

    try:
        from app.Agent.Nodes.AnswerEvaluator import answer_evaluator_node
        state = {
            "current_question": {**generated_question, "topic": TEST_TOPIC},
            "user_answer": "A list comprehension is a concise way to generate a new list by applying an expression to each item in an iterable, optionally filtering with a condition. It replaces verbose for-loops.",
            "answered_questions": [],
            "current_topic": TEST_TOPIC,
            "error": "",
        }
        result = await answer_evaluator_node(state)
        eval_data = result.get("evaluation", {})
        score = eval_data.get("score", -1)
        ok("Open-ended Groq grading", f"score={score:.2f}")
        print(f"    Feedback: {eval_data.get('feedback', '')[:100]}...")
    except Exception as e:
        fail("AnswerEvaluator open-ended", e)
        traceback.print_exc()


async def test_16_quality_gate_promotion(staging_id: str):
    section("16 — QualityGate Promotion Flow")
    if not staging_id:
        print(f"  {YELLOW}⚠ Skipped — no staging_id from test 06{RESET}")
        return

    try:
        from app.Agent.Tools.QualityGate import evaluate_and_promote
        question = {
            "text": "What is a list comprehension in Python?",
            "type": "open_ended",
            "expected": "Concise list creation syntax.",
            "options": [],
            "topic": TEST_TOPIC,
        }
        await evaluate_and_promote(staging_id=staging_id, question=question, score=0.85)
        ok("evaluate_and_promote (score=0.85 → promotion)", f"staging_id={staging_id[:8]}...")

        # Verify in Postgres
        from app.Agent.Tools.Database import Database
        db = Database()
        import asyncio as _aio
        resp = await _aio.to_thread(
            db.client.table("staging_questions").select("status").eq("id", staging_id).execute
        )
        if resp.data:
            status = resp.data[0].get("status", "unknown")
            ok("Postgres status after promotion", f"status={status}")
        else:
            print(f"  {YELLOW}⚠ Could not verify Postgres status (row may not exist){RESET}")
    except Exception as e:
        fail("QualityGate promotion", e)
        traceback.print_exc()


async def test_17_vector_ingestion_gate():
    section("17 — VectorIngestionGate Node")
    try:
        from app.Agent.Swarm.Nodes.VectorIngestionGate import vector_ingestion_gate_node
        fake_lesson = """
# Python List Comprehensions

## Introduction
List comprehensions provide a concise way to create lists in Python.

## Syntax
```python
new_list = [expression for item in iterable if condition]
```

## Examples
```python
squares = [x**2 for x in range(10)]
evens = [x for x in range(20) if x % 2 == 0]
```

## When to Use
Use list comprehensions when you want to transform or filter an existing iterable.
They are more readable and often faster than equivalent for-loops.

## Sources
- https://docs.python.org/3/tutorial/datastructures.html
- https://en.wikipedia.org/wiki/List_comprehension
"""
        state = {
            "current_topic": TEST_TOPIC,
            "current_topic_id": "test-topic-uuid",
            "content_module": fake_lesson,
            "swarm_raw_results": [
                {"source_type": "web", "source_url": "https://docs.python.org", "title": "Python Docs", "raw_text": "", "metadata": {}},
            ],
        }
        result = await vector_ingestion_gate_node(state)
        ok("VectorIngestionGate ran", f"swarm_queries cleared={result.get('swarm_queries') == []}")
        ok("swarm_raw_results cleared", f"={result.get('swarm_raw_results') == []}")
    except Exception as e:
        fail("VectorIngestionGate", e)
        traceback.print_exc()


async def test_18_curriculum_planner():
    section("18 — CurriculumPlanner Node (Gemini)")
    try:
        from app.Agent.Nodes.CurriculumPlanner import curriculum_planner_node
        state = {
            "user_profile": {
                "name": "Test User",
                "learning_goals": ["Learn Python from scratch"],
                "background": "complete_beginner",
                "learning_style": "hands-on",
            },
            "current_topic": "",
            "current_topic_id": "",
            "content_module": "",
            "error": "",
        }
        result = await curriculum_planner_node(state)

        if result.get("error"):
            fail("CurriculumPlanner", result["error"])
            return

        topic = result.get("current_topic", "")
        topic_id = result.get("current_topic_id", "")
        ok("CurriculumPlanner selected topic", f"'{topic}'")
        ok("Topic ID created/fetched", f"id={topic_id[:8]}...")
    except Exception as e:
        fail("CurriculumPlanner", e)
        traceback.print_exc()


async def test_19_path_rerouter(db, topic_id: str):
    section("19 — PathRerouter Node (EMA mastery + DB write)")
    if not db or not topic_id:
        print(f"  {YELLOW}⚠ Skipped — missing DB or topic_id{RESET}")
        return

    try:
        from app.Agent.Nodes.PathRerouter import path_rerouter_node
        state = {
            "user_id": TEST_USER_ID,
            "current_topic": TEST_TOPIC,
            "current_topic_id": topic_id,
            "evaluation": {"score": 0.9, "feedback": "Great!", "misconceptions": []},
            "current_batch_scores": [0.8, 0.9, 0.7, 0.85, 0.9],
            "consecutive_streak": 3,
            "loop_counters": {},
            "error": "",
        }
        result = await path_rerouter_node(state)
        if result.get("error"):
            fail("PathRerouter", result["error"])
            return
        ok("PathRerouter ran", f"next_route={result.get('next_route', 'N/A')}")

        # Verify DB write
        progress = await db.get_topic_progress(TEST_USER_ID, topic_id)
        if progress:
            ok("user_progress DB write", f"mastery_score={progress.get('mastery_score', 'N/A'):.3f}")
        else:
            print(f"  {YELLOW}⚠ No user_progress row found (TEST_USER_ID may not exist){RESET}")
    except Exception as e:
        fail("PathRerouter", e)
        traceback.print_exc()


async def test_20_full_graph_start():
    section("20 — Full Graph: start_session → interrupt before answer_evaluator")
    try:
        from app.Agent.GraphService import GraphService
        events = []
        generator = await GraphService.start_session(
            user_id=TEST_USER_ID,
            thread_id=TEST_THREAD + "-full-graph"
        )
        async for event_str in generator:
            events.append(event_str.strip())

        event_types = [e for e in events if "\"type\"" in e]
        ok("Graph executed and streamed events", f"{len(event_types)} SSE events")

        has_complete = any("execution_complete" in e for e in events)
        has_error    = any("fatal_error" in e for e in events)

        if has_error:
            err_events = [e for e in events if "fatal_error" in e]
            fail("Graph execution (fatal_error detected)", err_events[0][:120])
        elif has_complete:
            ok("Graph reached execution_complete")
        else:
            print(f"  {YELLOW}⚠ Graph did not reach execution_complete (may have paused){RESET}")
    except Exception as e:
        fail("Full graph start_session", e)
        traceback.print_exc()


# ═══════════════════════════════════════════════════════════════════════════════
# RUNNER
# ═══════════════════════════════════════════════════════════════════════════════

async def run_all():
    print(f"\n{BOLD}{'='*60}")
    print(f"  Personalized Learning Agent — Integration Test Suite")
    print(f"  TEST_USER_ID: {TEST_USER_ID}")
    print(f"  TEST_TOPIC:   {TEST_TOPIC}")
    print(f"{'='*60}{RESET}")

    await test_01_environment()

    db       = await test_02_supabase_connection()
    await test_03_schema_tables(db)
    await test_04_user_profile(db)

    topic_id   = await test_05_topic_creation(db)
    staging_id = await test_06_staging_question_write()

    await test_07_pinecone_staging_upsert()
    await test_08_pinecone_content_upsert()
    await test_09_pinecone_content_search()
    await test_10_pinecone_questions_search()

    await test_11_groq_connectivity()
    await test_12_gemini_connectivity()

    generated_q = await test_13_knowledge_assessor()
    await test_14_answer_evaluator_mcq()
    await test_15_answer_evaluator_open(generated_q)
    await test_16_quality_gate_promotion(staging_id)

    await test_17_vector_ingestion_gate()
    await test_18_curriculum_planner()
    await test_19_path_rerouter(db, topic_id)
    await test_20_full_graph_start()

    # ── Summary ───────────────────────────────────────────────────────────────
    total = len(passed) + len(failed)
    print(f"\n{BOLD}{'='*60}")
    print(f"  RESULTS: {GREEN}{len(passed)} passed{RESET}{BOLD}  |  {RED}{len(failed)} failed{RESET}{BOLD}  |  {total} total")
    print(f"{'='*60}{RESET}")

    if failed:
        print(f"\n{RED}{BOLD}  Failed tests:{RESET}")
        for name in failed:
            print(f"  {RED}✗ {name}{RESET}")
        sys.exit(1)
    else:
        print(f"\n{GREEN}{BOLD}  All tests passed! 🎉{RESET}\n")


if __name__ == "__main__":
    asyncio.run(run_all())
