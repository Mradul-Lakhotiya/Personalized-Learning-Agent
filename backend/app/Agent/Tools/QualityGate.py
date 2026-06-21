"""
QualityGate.py — RAG Question Cache Quality Gate

Handles the full lifecycle of questions:
  staging_questions (Postgres) ←→ questions_staging (Pinecone namespace)
                                           ↓ (on correct answer)
                              questions (Pinecone namespace, verified pool)

Rules:
  - New LLM-generated questions → written to staging (unverified)
  - Score >= 0.70 on first correct answer → promoted to verified 'questions' namespace
  - Score < 0.70, 3+ wrong, 0 correct → rejected and deleted
"""
import asyncio
import uuid
from datetime import datetime, timezone
from ..Tools.Database import Database
from ..Tools.VectorStore import VectorStore
from ..Tools.Embeddings import EmbeddingFactory

# Promotion threshold — minimum score to promote a staged question to verified
PROMOTE_THRESHOLD_SCORE = 0.70
# Number of times a question must be correctly answered before it is promoted
PROMOTE_THRESHOLD_CORRECT = 1
# Auto-reject after this many wrong answers with zero correct ones
REJECT_THRESHOLD_INCORRECT = 3


async def write_question_to_staging(
    topic: str,
    subtopic: str,
    question_type: str,
    question_text: str,
    expected_answer: str,
    options: list[str],
) -> dict:
    """
    Writes a newly LLM-generated question to:
    1. Postgres `staging_questions` table (status='staging')
    2. Pinecone `questions_staging` namespace

    Returns the staging row dict including the staging_id UUID.
    """
    db = Database()
    vs = VectorStore()

    staging_id = str(uuid.uuid4())

    # 1. Insert into Postgres staging_questions
    payload = {
        "id": staging_id,
        "topic": topic,
        "subtopic": subtopic or "",
        "question_type": question_type,
        "question_text": question_text,
        "correct_answer": expected_answer,
        "distractors": options,
        "status": "staging",
        "times_served_correctly": 0,
        "times_served_incorrectly": 0,
    }

    try:
        await asyncio.to_thread(
            db.client.table("staging_questions").insert(payload).execute
        )
        print(f"[QualityGate] Wrote question {staging_id[:8]}... to staging_questions table.")
    except Exception as e:
        print(f"[QualityGate] ⚠️ Failed to write to staging_questions table: {e}")

    # 2. Embed and upsert to Pinecone questions_staging namespace
    embed_text = f"{question_text} | {expected_answer}"
    try:
        await vs.aupsert(
            texts=[embed_text],
            metadatas=[{
                "staging_id": staging_id,
                "topic": topic,
                "subtopic": subtopic or "",
                "type": question_type,
                "text": question_text,
                "expected": expected_answer,
                "options": str(options),
                "status": "staging",
            }],
            namespace="questions_staging"
        )
        print(f"[QualityGate] Upserted staging question to Pinecone 'questions_staging'.")
    except Exception as e:
        print(f"[QualityGate] ⚠️ Failed to upsert to Pinecone staging namespace: {e}")

    return {**payload, "staging_id": staging_id}


async def evaluate_and_promote(
    staging_id: str,
    question: dict,
    score: float,
) -> None:
    """
    Called by AnswerEvaluator after grading a staged question.
    Handles the promotion/rejection lifecycle:

    score >= PROMOTE_THRESHOLD → promote to verified 'questions' namespace
    score < PROMOTE_THRESHOLD → increment failure counter, auto-reject if threshold hit
    """
    if not staging_id:
        return

    db = Database()
    vs = VectorStore()

    # Fetch current staging row
    try:
        resp = await asyncio.to_thread(
            db.client.table("staging_questions")
              .select("*")
              .eq("id", staging_id)
              .execute
        )
        staging_row = resp.data[0] if resp.data else None
    except Exception as e:
        print(f"[QualityGate] ⚠️ Could not fetch staging row: {e}")
        return

    if not staging_row:
        print(f"[QualityGate] ⚠️ No staging row found for id={staging_id[:8]}...")
        return

    correct = staging_row.get("times_served_correctly", 0)
    incorrect = staging_row.get("times_served_incorrectly", 0)

    if score >= PROMOTE_THRESHOLD_SCORE:
        new_correct = correct + 1

        if new_correct >= PROMOTE_THRESHOLD_CORRECT:
            # ── PROMOTE: copy to verified 'questions' namespace ───────────────
            embed_text = f"{question.get('text', '')} | {question.get('expected', '')}"
            try:
                await vs.aupsert(
                    texts=[embed_text],
                    metadatas=[{
                        "staging_id": staging_id,
                        "topic": question.get("topic", ""),
                        "type": question.get("type", "open_ended"),
                        "text": question.get("text", ""),
                        "expected": question.get("expected", ""),
                        "options": str(question.get("options", [])),
                        "quality_score": score,
                        "promoted_at": datetime.now(timezone.utc).isoformat(),
                        "times_used": 1,
                    }],
                    namespace="questions"   # ← verified namespace
                )
                print(f"[QualityGate] ✅ Promoted question {staging_id[:8]}... to verified 'questions' namespace.")
            except Exception as e:
                print(f"[QualityGate] ⚠️ Failed to promote to Pinecone: {e}")

            # Update Postgres status to promoted
            try:
                await asyncio.to_thread(
                    db.client.table("staging_questions")
                      .update({
                          "status": "promoted",
                          "times_served_correctly": new_correct,
                          "promoted_at": datetime.now(timezone.utc).isoformat(),
                      })
                      .eq("id", staging_id)
                      .execute
                )
            except Exception as e:
                print(f"[QualityGate] ⚠️ Failed to update Postgres status to promoted: {e}")
        else:
            # Increment correct count but don't promote yet (PROMOTE_THRESHOLD_CORRECT > 1)
            try:
                await asyncio.to_thread(
                    db.client.table("staging_questions")
                      .update({"times_served_correctly": new_correct})
                      .eq("id", staging_id)
                      .execute
                )
            except Exception as e:
                print(f"[QualityGate] ⚠️ Failed to increment correct count: {e}")

    else:
        # ── FAILED: increment incorrect count, auto-reject if threshold hit ──
        new_incorrect = incorrect + 1

        if new_incorrect >= REJECT_THRESHOLD_INCORRECT and correct == 0:
            # Auto-reject: 3 wrong, 0 correct — likely a bad question
            try:
                await asyncio.to_thread(
                    db.client.table("staging_questions")
                      .update({
                          "status": "rejected",
                          "times_served_incorrectly": new_incorrect,
                          "rejected_at": datetime.now(timezone.utc).isoformat(),
                      })
                      .eq("id", staging_id)
                      .execute
                )
                print(f"[QualityGate] ❌ Auto-rejected question {staging_id[:8]}... (3 wrong, 0 correct).")
                # Note: Pinecone TTL cleanup is handled by nightly job (Sprint 5 / MemoryConsolidator)
            except Exception as e:
                print(f"[QualityGate] ⚠️ Failed to reject staging question: {e}")
        else:
            try:
                await asyncio.to_thread(
                    db.client.table("staging_questions")
                      .update({"times_served_incorrectly": new_incorrect})
                      .eq("id", staging_id)
                      .execute
                )
                print(f"[QualityGate] ↓ Question {staging_id[:8]}... failed (score={score:.2f}). Incorrect={new_incorrect}.")
            except Exception as e:
                print(f"[QualityGate] ⚠️ Failed to update incorrect count: {e}")
