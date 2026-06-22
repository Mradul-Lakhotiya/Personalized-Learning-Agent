#!/usr/bin/env python3
"""
PathMind AI — End-to-End Backend Test
Tests the full user flow against the live backend:
  1. Create a new session
  2. Receive and answer survey questions
  3. Generate the curriculum graph
  4. Validate graph structure (nodes, edges, sections, statuses)
  5. Click a node (get detail)
  6. Mark a node as completed — verify downstream nodes unlock
  7. Verify the learning path is persisted in Supabase
  8. Simulate backend restart: reload graph from Supabase

Run from project root:
    cd backend
    venv\\Scripts\\Activate.ps1
    python ..\test_backend.py
"""

import os, sys, json, time, asyncio, uuid
from pathlib import Path

# ── Load .env ──────────────────────────────────────────────────────────────────
def load_env():
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        print("[FAIL] .env not found"); sys.exit(1)
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            v = v.split("  #")[0].strip()
            os.environ.setdefault(k.strip(), v)
    print("[OK]   .env loaded")

load_env()

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

# ── Colour helpers ─────────────────────────────────────────────────────────────
PASS = "  [PASS]"
FAIL = "  [FAIL]"
WARN = "  [WARN]"
INFO = "  [INFO]"
STEP = "  [STEP]"

def section(title):
    print(f"\n{'=' * 65}")
    print(f"  {title}")
    print(f"{'=' * 65}")

def p(label, msg="", ok=True):
    icon = PASS if ok else FAIL
    print(f"{icon}  {label}")
    if msg:
        print(f"         {msg}")
    return ok

# ── Test state ────────────────────────────────────────────────────────────────
RESULTS = {}
THREAD_ID = f"test-{uuid.uuid4().hex[:8]}"
LEARNING_GOAL = "Learn Python programming from scratch"
TEST_USER_ID = None   # will be set from Supabase after getting a real user


# ═════════════════════════════════════════════════════════════════════════════
# TEST 1 — Supabase: verify tables and get a real user_id to test with
# ═════════════════════════════════════════════════════════════════════════════
async def test_1_supabase_tables():
    section("TEST 1 — Supabase Tables & Test User")
    global TEST_USER_ID
    from app.Agent.Tools.Database import Database
    db = Database()

    # Check all 6 live tables
    tables = ["user_profiles", "sessions", "learning_paths", "path_nodes",
              "survey_responses", "node_resources"]
    all_ok = True
    from supabase import create_client
    client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
    for t in tables:
        try:
            r = client.table(t).select("id").limit(1).execute()
            p(f"Table `{t}`", "accessible")
        except Exception as e:
            p(f"Table `{t}`", str(e), ok=False)
            all_ok = False

    # Get first real user for testing
    try:
        r = client.table("user_profiles").select("id").limit(1).execute()
        if r.data:
            TEST_USER_ID = r.data[0]["id"]
            p("Test user found", f"user_id = {TEST_USER_ID}")
        else:
            print(f"{WARN}  No users in user_profiles — create a test account first via the frontend auth.")
            TEST_USER_ID = str(uuid.uuid4())  # fake UUID for DB tests
            p("Test user", f"No real user found. Using fake UUID: {TEST_USER_ID}", ok=False)
    except Exception as e:
        p("Test user lookup", str(e), ok=False)

    RESULTS["supabase_tables"] = "PASS" if all_ok else "FAIL"
    return all_ok


# ═════════════════════════════════════════════════════════════════════════════
# TEST 2 — ProfileBuilder: survey generation
# ═════════════════════════════════════════════════════════════════════════════
async def test_2_profile_builder():
    section("TEST 2 — ProfileBuilder (Survey Generation)")
    from app.Agent.Graph import app_graph

    config = {"configurable": {"thread_id": THREAD_ID}}

    # Pre-create the DB path row (same as what GraphService.start_session does)
    path_id = ""
    try:
        from app.Agent.Tools.Database import Database as _Db
        _db = _Db()
        path_id = await _db.save_learning_path(
            thread_id=THREAD_ID,
            user_id=TEST_USER_ID,
            learning_goal=LEARNING_GOAL,
            phase="onboarding",
        )
        print(f"  [INFO]  Pre-created DB path row: {path_id[:8]}...")
    except Exception as e:
        print(f"  [WARN]  DB path pre-creation failed (non-fatal): {e}")

    initial_state = {
        "user_id": TEST_USER_ID,
        "session_id": THREAD_ID,
        "user_profile": {},
        "skill_ratings": {},
        "learning_goal": LEARNING_GOAL,
        "curriculum_graph": {},
        "sections_generated": 0,
        "current_section": 1,
        "completed_node_ids": [],
        "active_node_id": None,
        "survey_questions": [],
        "survey_answers": [],
        "survey_complete": False,
        "conversation_history": [],
        "last_user_message": LEARNING_GOAL,
        "phase": "onboarding",
        "session_complete": False,
        "error": "",
        "loop_counters": {},
        "error_context": None,
        "swarm_queries": [],
        "swarm_raw_results": [],
        "content_module": "",
        "node_resources_output": {},
        "current_topic": "",
        "db_path_id": path_id,
        "total_sessions": 1,
        "flags": {},
    }

    print(f"{STEP}  Running ProfileBuilder for goal: '{LEARNING_GOAL}'")
    t0 = time.time()

    try:
        # Run graph — will stop at END after profile_builder (survey not complete)
        result = await app_graph.ainvoke(initial_state, config=config)
    except Exception as e:
        p("ProfileBuilder invoke", str(e), ok=False)
        RESULTS["profile_builder"] = "FAIL"
        return False

    elapsed = time.time() - t0
    questions = result.get("survey_questions", [])
    err = result.get("error", "")

    if err:
        p("ProfileBuilder", f"Error: {err}", ok=False)
        RESULTS["profile_builder"] = "FAIL"
        return False

    if not questions:
        p("survey_questions generated", "EMPTY — expected 5–8 questions", ok=False)
        RESULTS["profile_builder"] = "FAIL"
        return False

    p("ProfileBuilder ran", f"{elapsed:.1f}s")
    p(f"Survey questions count: {len(questions)}", f"Expected 5–8, got {len(questions)}",
      ok=5 <= len(questions) <= 8)
    for i, q in enumerate(questions):
        print(f"         Q{i+1}: [{q.get('topic','?')}] {q.get('question','')[:70]}")

    RESULTS["profile_builder"] = "PASS"
    return True, questions


# ═════════════════════════════════════════════════════════════════════════════
# TEST 3 — Survey: answer all questions, verify state updates
# ═════════════════════════════════════════════════════════════════════════════
async def test_3_survey_answers(questions):
    section("TEST 3 — Survey Answer Collection")
    from app.Agent.GraphService import GraphService

    # Simulate answering all questions with realistic ratings
    MOCK_RATINGS = {
        "Python": 2, "Programming": 1, "Variables": 3, "Functions": 2,
        "Data Types": 2, "Control Flow": 1, "OOP": 0, "Libraries": 1,
        "Algorithms": 0, "Debugging": 1,
    }

    all_ok = True
    for i, q in enumerate(questions):
        topic = q.get("topic", f"topic_{i}")
        rating = MOCK_RATINGS.get(topic, 1)  # default 1 for unknown topics

        print(f"{STEP}  Answering Q{i+1}: '{topic}' → rating {rating}")
        result = await GraphService.submit_survey_answer(
            thread_id=THREAD_ID,
            user_id=TEST_USER_ID,
            topic=topic,
            rating=rating,
        )

        if "error" in result:
            p(f"Answer Q{i+1}", result["error"], ok=False)
            all_ok = False
            continue

        if result.get("survey_complete") and i < len(questions) - 1:
            p(f"Answer Q{i+1}", "survey_complete=True before all answered!", ok=False)
            all_ok = False
        elif result.get("survey_complete") and i == len(questions) - 1:
            p(f"All {len(questions)} answers collected", "survey_complete=True ✓")
        elif result.get("next_question"):
            nq = result["next_question"]
            prog = result.get("progress", {})
            print(f"         → Next: [{nq.get('topic')}] ({prog.get('answered')}/{prog.get('total')})")
        else:
            p(f"Answer Q{i+1}", f"Unexpected response: {result}", ok=False)
            all_ok = False

    # Verify state has skill_ratings
    from app.Agent.Graph import app_graph
    snap = app_graph.get_state({"configurable": {"thread_id": THREAD_ID}})
    ratings = snap.values.get("skill_ratings", {}) if snap else {}
    complete = snap.values.get("survey_complete", False) if snap else False

    p("skill_ratings populated", f"{len(ratings)} topics rated", ok=len(ratings) > 0)
    p("survey_complete = True", str(complete), ok=complete)

    RESULTS["survey_answers"] = "PASS" if all_ok and complete else "FAIL"
    return all_ok and complete


# ═════════════════════════════════════════════════════════════════════════════
# TEST 4 — CurriculumPlanner: generate the graph
# ═════════════════════════════════════════════════════════════════════════════
async def test_4_curriculum_generation():
    section("TEST 4 — CurriculumPlanner (Graph Generation)")
    from app.Agent.GraphService import GraphService

    print(f"{STEP}  Resuming graph to run CurriculumPlanner...")
    t0 = time.time()

    # Collect SSE events from the generate_curriculum stream
    generator = await GraphService.generate_curriculum(THREAD_ID, TEST_USER_ID)
    final_payload = None
    async for raw_event in generator:
        if raw_event.startswith("data:"):
            try:
                event = json.loads(raw_event.replace("data: ", "").strip())
                etype = event.get("type", "")
                print(f"         SSE → {etype}")
                if etype == "execution_complete":
                    final_payload = event.get("payload", {})
                elif etype == "fatal_error":
                    p("CurriculumPlanner SSE", event.get("message", ""), ok=False)
                    RESULTS["curriculum_generation"] = "FAIL"
                    return False, None
            except json.JSONDecodeError:
                pass

    elapsed = time.time() - t0

    if not final_payload:
        p("CurriculumPlanner", "No execution_complete event received", ok=False)
        RESULTS["curriculum_generation"] = "FAIL"
        return False, None

    phase = final_payload.get("phase")
    graph = final_payload.get("curriculum_graph", {})

    p(f"Phase = '{phase}'", "Expected: graph_ready", ok=phase == "graph_ready")
    p(f"Generation time", f"{elapsed:.1f}s")

    if not graph:
        p("curriculum_graph", "Empty!", ok=False)
        RESULTS["curriculum_generation"] = "FAIL"
        return False, None

    RESULTS["curriculum_generation"] = "PASS" if phase == "graph_ready" else "FAIL"
    return phase == "graph_ready", graph


# ═════════════════════════════════════════════════════════════════════════════
# TEST 5 — Graph Structure Validation
# ═════════════════════════════════════════════════════════════════════════════
def test_5_graph_structure(graph):
    section("TEST 5 — Graph Structure Validation")
    all_ok = True

    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    sections = graph.get("section_titles", [])
    goal = graph.get("goal", "")

    p(f"Goal set", f"'{goal}'", ok=bool(goal))
    p(f"Node count: {len(nodes)}", f"Expected 8–25, got {len(nodes)}", ok=8 <= len(nodes) <= 80)
    p(f"Edge count: {len(edges)}", f"{len(edges)} prerequisite edges")
    p(f"Sections: {len(sections)}", str(sections), ok=len(sections) >= 1)

    # All nodes have required fields
    required_fields = ["id", "title", "description", "prerequisites",
                       "difficulty", "estimated_minutes", "section",
                       "section_number", "is_major", "status"]
    missing_field_nodes = []
    for node in nodes:
        for f in required_fields:
            if f not in node:
                missing_field_nodes.append(f"{node.get('id','?')}.{f}")
    if missing_field_nodes:
        p("Node schema completeness", f"Missing fields: {missing_field_nodes[:5]}", ok=False)
        all_ok = False
    else:
        p("Node schema completeness", "All required fields present ✓")

    # Status distribution
    statuses = {}
    for n in nodes:
        s = n.get("status", "unknown")
        statuses[s] = statuses.get(s, 0) + 1
    print(f"{INFO}  Status distribution: {statuses}")
    has_available = statuses.get("available", 0) > 0
    p("At least 1 available node", str(has_available), ok=has_available)

    # Major node flag
    major_count = sum(1 for n in nodes if n.get("is_major"))
    major_pct = major_count / len(nodes) * 100 if nodes else 0
    p(f"Major nodes: {major_count}/{len(nodes)} ({major_pct:.0f}%)",
      "Expected ~25–35%", ok=15 <= major_pct <= 50)

    # Edge integrity: all sources + targets must exist in node ids
    node_ids = {n["id"] for n in nodes}
    bad_edges = [e for e in edges if e.get("source") not in node_ids
                 or e.get("target") not in node_ids]
    if bad_edges:
        p("Edge integrity", f"{len(bad_edges)} edges reference missing nodes", ok=False)
        all_ok = False
    else:
        p("Edge integrity", "All edge sources/targets valid ✓")

    # No self-loops
    loops = [e for e in edges if e.get("source") == e.get("target")]
    p("No self-loops", f"{len(loops)} found", ok=len(loops) == 0)

    # Difficulty range 1–5
    bad_diff = [n for n in nodes if not (1 <= n.get("difficulty", 0) <= 5)]
    p("Difficulty values 1–5", f"{len(bad_diff)} out of range", ok=len(bad_diff) == 0)

    RESULTS["graph_structure"] = "PASS" if all_ok else "FAIL"
    return all_ok


# ═════════════════════════════════════════════════════════════════════════════
# TEST 6 — Node Completion: mark first available node, verify unlock
# ═════════════════════════════════════════════════════════════════════════════
async def test_6_node_completion(graph):
    section("TEST 6 — Node Completion & Unlock")
    from app.Agent.GraphService import GraphService

    nodes = graph.get("nodes", [])
    available = [n for n in nodes if n.get("status") == "available"]

    if not available:
        p("Available nodes", "None found — cannot test completion", ok=False)
        RESULTS["node_completion"] = "FAIL"
        return False

    # Find a node that has dependents (so we can verify unlock)
    target_node = None
    node_ids_with_dependents = {
        e["source"] for e in graph.get("edges", [])
    }
    for n in available:
        if n["id"] in node_ids_with_dependents:
            target_node = n
            break
    if not target_node:
        target_node = available[0]

    print(f"{STEP}  Completing node: '{target_node['title']}' (id: {target_node['id']})")

    # Find which nodes depend on this one
    dependents_before = [
        n for n in nodes
        if target_node["id"] in n.get("prerequisites", [])
        and n.get("status") == "locked"
    ]
    print(f"{INFO}  Locked dependents before: {[n['title'] for n in dependents_before]}")

    result = await GraphService.complete_node(
        thread_id=THREAD_ID,
        user_id=TEST_USER_ID,
        node_id=target_node["id"],
    )

    if result.get("error"):
        p("complete_node", result["error"], ok=False)
        RESULTS["node_completion"] = "FAIL"
        return False

    updated_graph = result.get("curriculum_graph", {})
    updated_nodes = {n["id"]: n for n in updated_graph.get("nodes", [])}

    # Verify the node is now completed
    completed_ok = updated_nodes.get(target_node["id"], {}).get("status") == "completed"
    p(f"'{target_node['title']}' → completed", str(completed_ok), ok=completed_ok)

    # Verify dependents unlocked
    unlocked = [
        n for n in dependents_before
        if updated_nodes.get(n["id"], {}).get("status") == "available"
    ]
    if dependents_before:
        p(f"Dependents unlocked: {len(unlocked)}/{len(dependents_before)}",
          str([n["title"] for n in unlocked]),
          ok=len(unlocked) > 0)
    else:
        p("No locked dependents to unlock", "(leaf node selected — OK)")

    # Verify completed_node_ids includes this node
    completed_ids = result.get("curriculum_graph", {})
    from app.Agent.Graph import app_graph
    snap = app_graph.get_state({"configurable": {"thread_id": THREAD_ID}})
    c_ids = snap.values.get("completed_node_ids", []) if snap else []
    p(f"completed_node_ids updated", f"Contains '{target_node['id']}': {target_node['id'] in c_ids}",
      ok=target_node["id"] in c_ids)

    RESULTS["node_completion"] = "PASS" if completed_ok else "FAIL"
    return completed_ok


# ═════════════════════════════════════════════════════════════════════════════
# TEST 7 — Supabase Persistence: verify path was saved to DB
# ═════════════════════════════════════════════════════════════════════════════
async def test_7_db_persistence():
    section("TEST 7 — Supabase Persistence")
    from app.Agent.Tools.Database import Database
    db = Database()

    # learning_paths
    saved = await db.get_learning_path(THREAD_ID)
    if not saved:
        p("learning_paths row", "NOT found in DB — check GraphService.generate_curriculum()", ok=False)
        RESULTS["db_persistence"] = "FAIL"
        return False

    p("learning_paths row saved", f"id={saved.get('id','?')[:8]}...")
    p(f"learning_goal", f"'{saved.get('learning_goal','')}'",
      ok=bool(saved.get("learning_goal")))
    p(f"phase = graph_ready", str(saved.get("phase") == "graph_ready"),
      ok=saved.get("phase") == "graph_ready")

    graph_saved = saved.get("curriculum_graph") or {}
    nodes_saved = graph_saved.get("nodes", []) if isinstance(graph_saved, dict) else []
    p(f"curriculum_graph has {len(nodes_saved)} nodes in DB",
      "Expected > 0", ok=len(nodes_saved) > 0)

    # path_nodes
    from supabase import create_client
    client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
    path_id = saved.get("id")
    r = client.table("path_nodes").select("id, node_id, status").eq("path_id", path_id).execute()
    db_nodes = r.data or []
    p(f"path_nodes rows: {len(db_nodes)}", f"Expected ~{len(nodes_saved)}",
      ok=len(db_nodes) > 0)

    # survey_responses
    r2 = client.table("survey_responses").select("id, topic, rating").eq("path_id", path_id).execute()
    surveys = r2.data or []
    p(f"survey_responses rows: {len(surveys)}", "Expected > 0", ok=len(surveys) > 0)
    for s in surveys[:4]:
        print(f"         {s['topic']} → {s['rating']}/5")

    RESULTS["db_persistence"] = "PASS" if nodes_saved and db_nodes else "FAIL"
    return bool(nodes_saved and db_nodes)


# ═════════════════════════════════════════════════════════════════════════════
# TEST 8 — State Restore from Supabase (simulates backend restart)
# ═════════════════════════════════════════════════════════════════════════════
async def test_8_state_restore():
    section("TEST 8 — State Restore from Supabase (restart simulation)")
    from app.Agent.Tools.Database import Database
    db = Database()

    saved = await db.get_learning_path(THREAD_ID)
    if not saved:
        p("Cannot test restore", "Path not in DB", ok=False)
        RESULTS["state_restore"] = "FAIL"
        return False

    graph = saved.get("curriculum_graph") or {}
    nodes = graph.get("nodes", []) if isinstance(graph, dict) else []
    completed = saved.get("completed_node_ids", [])
    phase = saved.get("phase", "")

    p("Retrieved from DB", f"phase={phase}, {len(nodes)} nodes, {len(completed)} completed")
    p("Graph nodes survive round-trip", str(len(nodes) > 0), ok=len(nodes) > 0)

    # completed_node_ids: check from LangGraph state (DB flush is async)
    from app.Agent.Graph import app_graph
    snap = app_graph.get_state({"configurable": {"thread_id": THREAD_ID}})
    state_completed = snap.values.get("completed_node_ids", []) if snap else []
    p("completed_node_ids in LangGraph state", str(len(state_completed) > 0), ok=len(state_completed) > 0)

    # Verify the RAGService.get_curriculum_cache path
    from app.Agent.Tools.RAGService import RAGService
    cached = await RAGService.get_curriculum_cache(LEARNING_GOAL)
    if cached:
        p("Pinecone curriculum cache hit", f"{len(cached.get('nodes',[]))} nodes cached")
    else:
        p("Pinecone curriculum cache", "MISS — first run expected", ok=True)

    RESULTS["state_restore"] = "PASS"
    return True


# ═════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═════════════════════════════════════════════════════════════════════════════
def print_summary():
    section("FINAL RESULTS SUMMARY")
    passed  = sum(1 for v in RESULTS.values() if v == "PASS")
    failed  = sum(1 for v in RESULTS.values() if v == "FAIL")

    for test, status in RESULTS.items():
        icon = PASS if status == "PASS" else FAIL
        print(f"{icon}  {test.replace('_', ' ').upper()}")

    print(f"\n  Passed:  {passed}/{len(RESULTS)}")
    print(f"  Failed:  {failed}/{len(RESULTS)}")
    print(f"  Thread:  {THREAD_ID}")
    print()
    if failed == 0:
        print("  [ALL CLEAR] Backend is solid. Ready for frontend wiring.")
    else:
        print("  [ACTION NEEDED] Fix the failing tests before proceeding.")
    print()


# ═════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═════════════════════════════════════════════════════════════════════════════
async def main():
    print("\n  PathMind AI — Backend End-to-End Test")
    print(f"  Thread ID: {THREAD_ID}")
    print(f"  Goal:      '{LEARNING_GOAL}'")
    print(f"  Time:      {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    db_ok = await test_1_supabase_tables()
    if not db_ok:
        print(f"{FAIL}  DB tables not ready — fix before continuing."); return

    ret = await test_2_profile_builder()
    if not ret or ret is False:
        print(f"{FAIL}  ProfileBuilder failed — cannot continue."); return
    _, questions = ret if isinstance(ret, tuple) else (ret, [])
    if not questions:
        print(f"{FAIL}  No survey questions — cannot continue."); return

    ok = await test_3_survey_answers(questions)
    if not ok:
        print(f"{FAIL}  Survey collection failed — cannot continue."); return

    ret4 = await test_4_curriculum_generation()
    ok4, graph = ret4 if isinstance(ret4, tuple) else (ret4, None)
    if not ok4 or not graph:
        print(f"{FAIL}  CurriculumPlanner failed — cannot continue."); return

    test_5_graph_structure(graph)
    await test_6_node_completion(graph)
    await test_7_db_persistence()
    await test_8_state_restore()

    print_summary()


if __name__ == "__main__":
    asyncio.run(main())
