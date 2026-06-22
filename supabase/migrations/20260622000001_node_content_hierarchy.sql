-- Migration: Add questions_cached to path_nodes for hierarchical storage
ALTER TABLE public.path_nodes 
ADD COLUMN IF NOT EXISTS questions_cached JSONB;
