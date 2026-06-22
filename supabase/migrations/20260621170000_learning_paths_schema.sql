-- Migration: Visual Learning Path Generator — New Tables
-- Replaces the Q&A pipeline tables with graph-based learning path persistence.
-- The old tables (staging_questions, answered_questions, curricula) are kept as-is
-- (no destructive changes) but are no longer written to by the new backend.

-- ── 1. Learning Paths ────────────────────────────────────────────────────────
-- One row per learning path (one LangGraph session = one path).
CREATE TABLE IF NOT EXISTS public.learning_paths (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id           TEXT UNIQUE NOT NULL,
    user_id             UUID NOT NULL REFERENCES public.user_profiles(id) ON DELETE CASCADE,
    learning_goal       TEXT NOT NULL,
    skill_ratings       JSONB DEFAULT '{}',        -- { "Python": 3, "Statistics": 1 }
    curriculum_graph    JSONB,                     -- { goal, section_titles, nodes, edges }
    completed_node_ids  TEXT[] DEFAULT '{}',
    sections_generated  INT DEFAULT 0,
    current_section     INT DEFAULT 1,
    phase               TEXT DEFAULT 'onboarding', -- 'onboarding' | 'graph_ready'
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast user history lookup
CREATE INDEX IF NOT EXISTS idx_learning_paths_user_id
    ON public.learning_paths(user_id, created_at DESC);

-- Auto-update updated_at on change
CREATE OR REPLACE FUNCTION public.update_learning_path_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_learning_paths_updated_at ON public.learning_paths;
CREATE TRIGGER trg_learning_paths_updated_at
    BEFORE UPDATE ON public.learning_paths
    FOR EACH ROW EXECUTE FUNCTION public.update_learning_path_timestamp();

-- RLS
ALTER TABLE public.learning_paths ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can manage own paths" ON public.learning_paths;
CREATE POLICY "Users can manage own paths"
    ON public.learning_paths FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);


-- ── 2. Path Nodes ────────────────────────────────────────────────────────────
-- One row per node per learning path — for fast per-node queries.
CREATE TABLE IF NOT EXISTS public.path_nodes (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    path_id             UUID NOT NULL REFERENCES public.learning_paths(id) ON DELETE CASCADE,
    user_id             UUID NOT NULL REFERENCES public.user_profiles(id) ON DELETE CASCADE,
    node_id             TEXT NOT NULL,             -- URL-safe slug: "python-basics"
    title               TEXT NOT NULL,
    description         TEXT,
    section_number      INT DEFAULT 1,
    section_title       TEXT,
    difficulty          INT DEFAULT 1 CHECK (difficulty BETWEEN 1 AND 5),
    estimated_minutes   INT DEFAULT 30,
    is_major            BOOLEAN DEFAULT FALSE,
    prerequisites       TEXT[] DEFAULT '{}',       -- array of node_id slugs
    status              TEXT DEFAULT 'locked'
                            CHECK (status IN ('locked', 'available', 'in_progress', 'completed')),
    resources_cached    JSONB,                     -- null until swarm generates resources
    completed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(path_id, node_id)
);

-- Index for status-based queries (e.g. "what nodes are available?")
CREATE INDEX IF NOT EXISTS idx_path_nodes_status
    ON public.path_nodes(path_id, status);

-- RLS
ALTER TABLE public.path_nodes ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can manage own nodes" ON public.path_nodes;
CREATE POLICY "Users can manage own nodes"
    ON public.path_nodes FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);


-- ── 3. Survey Responses ──────────────────────────────────────────────────────
-- Stores each self-assessment answer for historical analysis.
CREATE TABLE IF NOT EXISTS public.survey_responses (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    path_id     UUID REFERENCES public.learning_paths(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES public.user_profiles(id) ON DELETE CASCADE,
    topic       TEXT NOT NULL,
    question    TEXT NOT NULL,
    rating      INT NOT NULL CHECK (rating BETWEEN 0 AND 5),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Index for aggregated skill view per user
CREATE INDEX IF NOT EXISTS idx_survey_responses_user
    ON public.survey_responses(user_id, topic);

-- RLS
ALTER TABLE public.survey_responses ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can manage own surveys" ON public.survey_responses;
CREATE POLICY "Users can manage own surveys"
    ON public.survey_responses FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);


-- ── 4. Node Resources Cache ──────────────────────────────────────────────────
-- Shared cache of resources generated by the Content Swarm per topic slug.
-- Shared across all users: if two users learn "python-basics", only one swarm run needed.
CREATE TABLE IF NOT EXISTS public.node_resources (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_slug       TEXT UNIQUE NOT NULL,          -- e.g. "python-basics"
    title           TEXT NOT NULL,
    description     TEXT,                          -- 2-3 sentence summary
    resources       JSONB NOT NULL DEFAULT '[]',   -- [{ type, title, url, why_relevant }]
    pinecone_ids    TEXT[] DEFAULT '{}',           -- Pinecone vector IDs in node_content ns
    generated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- RLS: anyone can read (shared global cache); only service role writes
ALTER TABLE public.node_resources ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Public read node resources" ON public.node_resources;
CREATE POLICY "Public read node resources"
    ON public.node_resources FOR SELECT
    USING (true);
-- Backend uses SUPABASE_SERVICE_KEY which bypasses RLS for writes
