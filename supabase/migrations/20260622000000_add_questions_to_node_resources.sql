-- Migration: Add questions to node_resources
ALTER TABLE public.node_resources 
ADD COLUMN IF NOT EXISTS questions JSONB NOT NULL DEFAULT '[]';
