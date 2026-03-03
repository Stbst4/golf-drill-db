-- Golf Drill Database Schema
-- Run this in your Supabase SQL editor

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS golf_drills (
  id                uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  drill_name        text NOT NULL,
  problem_fixed     text[] DEFAULT '{}',
  category          text CHECK (category IN ('swing', 'short_game', 'putting', 'mental', 'fitness')),
  skill_level       text CHECK (skill_level IN ('beginner', 'intermediate', 'advanced')),
  steps             jsonb DEFAULT '[]',
  equipment_needed  text[] DEFAULT '{}',
  key_feel          text,
  duration_minutes  integer,
  source_platform   text CHECK (source_platform IN ('tiktok', 'youtube')),
  source_url        text NOT NULL,
  creator_handle    text,
  creator_name      text,
  transcript        text,
  video_id          text UNIQUE NOT NULL,
  quality_score     integer CHECK (quality_score BETWEEN 1 AND 5),
  tags              text[] DEFAULT '{}',
  is_professional   boolean DEFAULT false,
  pro_golfer        text,
  pro_golfer_slug   text,
  processed_at      timestamptz DEFAULT now(),
  created_at        timestamptz DEFAULT now()
);

-- Indexes for common search patterns
CREATE INDEX IF NOT EXISTS idx_golf_drills_category ON golf_drills(category);
CREATE INDEX IF NOT EXISTS idx_golf_drills_skill_level ON golf_drills(skill_level);
CREATE INDEX IF NOT EXISTS idx_golf_drills_problem_fixed ON golf_drills USING GIN(problem_fixed);
CREATE INDEX IF NOT EXISTS idx_golf_drills_tags ON golf_drills USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_golf_drills_creator ON golf_drills(creator_handle);
CREATE INDEX IF NOT EXISTS idx_golf_drills_video_id ON golf_drills(video_id);
CREATE INDEX IF NOT EXISTS idx_golf_drills_pro_golfer ON golf_drills(pro_golfer);
CREATE INDEX IF NOT EXISTS idx_golf_drills_pro_golfer_slug ON golf_drills(pro_golfer_slug);
CREATE INDEX IF NOT EXISTS idx_golf_drills_is_professional ON golf_drills(is_professional);

-- Full text search index
CREATE INDEX IF NOT EXISTS idx_golf_drills_fts ON golf_drills
  USING GIN(to_tsvector('english', coalesce(drill_name,'') || ' ' || coalesce(key_feel,'') || ' ' || coalesce(array_to_string(tags,' '),'')));

COMMENT ON TABLE golf_drills IS 'Golf instruction drills extracted from TikTok and YouTube Shorts';
