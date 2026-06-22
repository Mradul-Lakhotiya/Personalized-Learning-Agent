-- Migration: Drop all tables from the old Q&A pipeline architecture.
-- These tables were part of the KnowledgeAssessor / AnswerEvaluator / PathRerouter
-- flow which has been fully replaced by the visual learning path graph system.
--
-- Tables being KEPT:
--   user_profiles        → core auth & onboarding profile (KEEP)
--   sessions             → session history for MemoryConsolidator (KEEP, simplified)
--   learning_paths       → new core table (KEEP)
--   path_nodes           → new core table (KEEP)
--   survey_responses     → new core table (KEEP)
--   node_resources       → new shared resource cache (KEEP)
--
-- Tables being DROPPED:
--   topics               → old CurriculumPlanner topic registry (not used)
--   user_progress        → old Q&A mastery score tracker (FK to topics)
--   user_subscriptions   → never wired to any logic
--   skill_map            → old AnswerEvaluator confidence scores
--   curricula            → old flat curriculum list
--   staging_questions    → old Q&A quality gate staging pool
--   answered_questions   → old Q&A audit log

-- ── Step 1: Drop tables with FK dependencies first ──────────────────────────

-- answered_questions references sessions and staging_questions
DROP TABLE IF EXISTS public.answered_questions CASCADE;

-- staging_questions
DROP TABLE IF EXISTS public.staging_questions CASCADE;

-- curricula references user_profiles
DROP TABLE IF EXISTS public.curricula CASCADE;

-- skill_map references user_profiles
DROP TABLE IF EXISTS public.skill_map CASCADE;

-- user_subscriptions references user_profiles
DROP TABLE IF EXISTS public.user_subscriptions CASCADE;

-- user_progress references user_profiles and topics
DROP TABLE IF EXISTS public.user_progress CASCADE;

-- topics (no more FKs after user_progress is dropped)
DROP TABLE IF EXISTS public.topics CASCADE;

-- ── Step 2: Clean up related functions/triggers no longer needed ─────────────

DROP TRIGGER IF EXISTS on_profile_created_add_subscription ON public.user_profiles;
DROP FUNCTION IF EXISTS public.handle_new_subscription();

-- ── Step 3: Simplify sessions table (remove Q&A-specific columns) ───────────
-- Remove avg_score and questions_answered — no longer relevant without Q&A.
ALTER TABLE public.sessions
    DROP COLUMN IF EXISTS avg_score,
    DROP COLUMN IF EXISTS questions_answered;

-- Rename topics_covered to reflect graph-based paths (keep as TEXT[] for compat)
-- topics_covered is now used to log which learning_path.learning_goal was worked on.
-- No rename needed — the column semantics shift naturally.

-- ── Step 4: Verify the clean schema ─────────────────────────────────────────
-- After this migration the only tables in public schema are:
--   user_profiles, sessions, learning_paths, path_nodes, survey_responses, node_resources
