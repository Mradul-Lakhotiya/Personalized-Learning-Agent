-- Migration: Complete schema alignment with architecture plan
-- Adds: sessions, skill_map, curricula, staging_questions, answered_questions, user_subscriptions
-- Expands: user_profiles with learning_style, background, daily_time_budget
-- NOTE: topics, user_profiles, user_progress already exist from initial migration

-- ── Expand user_profiles with richer onboarding fields ─────────────────────
ALTER TABLE public.user_profiles
    ADD COLUMN IF NOT EXISTS background TEXT,
    ADD COLUMN IF NOT EXISTS learning_style TEXT CHECK (learning_style IN ('visual', 'reading', 'hands-on', 'mixed')),
    ADD COLUMN IF NOT EXISTS daily_time_budget_minutes INT DEFAULT 30,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- ── User Subscriptions ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.user_subscriptions (
    user_id UUID REFERENCES public.user_profiles(id) ON DELETE CASCADE PRIMARY KEY,
    tier TEXT DEFAULT 'free' CHECK (tier IN ('free', 'pro', 'team')),
    sessions_this_month INT DEFAULT 0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Auto-create subscription row when a user_profile is created
CREATE OR REPLACE FUNCTION public.handle_new_subscription()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.user_subscriptions (user_id) VALUES (NEW.id)
  ON CONFLICT (user_id) DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_profile_created_add_subscription ON public.user_profiles;
CREATE TRIGGER on_profile_created_add_subscription
  AFTER INSERT ON public.user_profiles
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_subscription();

-- ── Skill Map ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.skill_map (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.user_profiles(id) ON DELETE CASCADE,
    topic TEXT NOT NULL,
    subtopic TEXT,
    confidence FLOAT DEFAULT 0.0 CHECK (confidence BETWEEN 0 AND 1),
    level TEXT DEFAULT 'novice' CHECK (level IN ('novice', 'beginner', 'intermediate', 'advanced', 'expert')),
    last_assessed_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(user_id, topic, subtopic)
);

-- ── Curricula (Ordered Learning Plan per User) ──────────────────────────────
CREATE TABLE IF NOT EXISTS public.curricula (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.user_profiles(id) ON DELETE CASCADE,
    unit_index INT NOT NULL,
    topic TEXT NOT NULL,
    subtopics JSONB DEFAULT '[]',
    estimated_minutes INT DEFAULT 30,
    prerequisites JSONB DEFAULT '[]',
    resources JSONB DEFAULT '[]',
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'completed', 'skipped', 'remediation')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ── Sessions ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.user_profiles(id) ON DELETE CASCADE,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ended_at TIMESTAMP WITH TIME ZONE,
    summary TEXT,                  -- LLM-compressed episodic memory
    avg_score FLOAT,
    topics_covered JSONB DEFAULT '[]',
    questions_answered INT DEFAULT 0
);

-- ── Staging Questions (Quality Gate — Unverified Pool) ──────────────────────
-- New LLM-generated questions live here first.
-- They are promoted to the Pinecone "questions" namespace only after a user
-- correctly answers them (quality gate passed in AnswerEvaluator).
CREATE TABLE IF NOT EXISTS public.staging_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic TEXT NOT NULL,
    subtopic TEXT,
    difficulty TEXT CHECK (difficulty IN ('easy', 'medium', 'hard')),
    bloom_level TEXT,
    question_type TEXT CHECK (question_type IN ('mcq', 'open_ended', 'code', 'scenario')),
    question_text TEXT NOT NULL,
    correct_answer TEXT,
    distractors JSONB DEFAULT '[]',    -- MCQ options
    rubric JSONB DEFAULT '[]',         -- Open-ended criteria
    pinecone_vector_id TEXT,           -- ID in "questions_staging" Pinecone namespace
    status TEXT DEFAULT 'staging' CHECK (status IN ('staging', 'promoted', 'rejected')),
    times_served_correctly INT DEFAULT 0,
    times_served_incorrectly INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    promoted_at TIMESTAMP WITH TIME ZONE,
    rejected_at TIMESTAMP WITH TIME ZONE
);

-- Index for nightly TTL cleanup job (remove staging questions older than 72h)
CREATE INDEX IF NOT EXISTS idx_staging_cleanup
    ON public.staging_questions(status, created_at)
    WHERE status = 'staging';

-- ── Answered Questions (Audit Log + Analytics) ──────────────────────────────
CREATE TABLE IF NOT EXISTS public.answered_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES public.sessions(id) ON DELETE SET NULL,
    user_id UUID REFERENCES public.user_profiles(id) ON DELETE CASCADE,
    topic TEXT,
    question_type TEXT,
    question_text TEXT,
    user_answer TEXT,
    score FLOAT,
    feedback TEXT,
    cache_hit BOOLEAN DEFAULT FALSE,           -- served from verified Pinecone "questions" namespace?
    staging_question_id UUID REFERENCES public.staging_questions(id) ON DELETE SET NULL,
    triggered_promotion BOOLEAN DEFAULT FALSE, -- did this answer promote a staged question?
    answered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ── Row Level Security for new tables ───────────────────────────────────────
ALTER TABLE public.user_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.skill_map ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.curricula ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.staging_questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.answered_questions ENABLE ROW LEVEL SECURITY;

-- user_subscriptions
CREATE POLICY "Users can read own subscription" ON public.user_subscriptions
    FOR SELECT USING (auth.uid() = user_id);

-- skill_map
CREATE POLICY "Users can read own skill map" ON public.skill_map
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can write own skill map" ON public.skill_map
    FOR ALL USING (auth.uid() = user_id);

-- curricula
CREATE POLICY "Users can read own curricula" ON public.curricula
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can write own curricula" ON public.curricula
    FOR ALL USING (auth.uid() = user_id);

-- sessions
CREATE POLICY "Users can read own sessions" ON public.sessions
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Service role can write sessions" ON public.sessions
    FOR ALL USING (true);

-- staging_questions (service role only writes; readable by all for assessment)
CREATE POLICY "Staging questions readable by authenticated" ON public.staging_questions
    FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Service role manages staging questions" ON public.staging_questions
    FOR ALL USING (auth.role() = 'service_role');

-- answered_questions
CREATE POLICY "Users can read own answers" ON public.answered_questions
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Service role can write answers" ON public.answered_questions
    FOR ALL USING (true);
