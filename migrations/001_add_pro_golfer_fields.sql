-- Migration: Add professional golfer fields for filtering
-- Run this in your Supabase SQL editor

-- Add pro golfer fields
ALTER TABLE golf_drills ADD COLUMN IF NOT EXISTS is_professional boolean DEFAULT false;
ALTER TABLE golf_drills ADD COLUMN IF NOT EXISTS pro_golfer text;
ALTER TABLE golf_drills ADD COLUMN IF NOT EXISTS pro_golfer_slug text;

-- Index for filtering by pro golfer
CREATE INDEX IF NOT EXISTS idx_golf_drills_pro_golfer ON golf_drills(pro_golfer);
CREATE INDEX IF NOT EXISTS idx_golf_drills_pro_golfer_slug ON golf_drills(pro_golfer_slug);
CREATE INDEX IF NOT EXISTS idx_golf_drills_is_professional ON golf_drills(is_professional);

COMMENT ON COLUMN golf_drills.is_professional IS 'True if video features a professional golfer giving instruction';
COMMENT ON COLUMN golf_drills.pro_golfer IS 'Full name of pro golfer (e.g. Tiger Woods)';
COMMENT ON COLUMN golf_drills.pro_golfer_slug IS 'URL-safe slug (e.g. tiger-woods) for filtering';
