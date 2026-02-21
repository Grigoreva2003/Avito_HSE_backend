-- Migration: V004 - Add is_closed flag to ads
-- Description: Add explicit close-state marker for ads lifecycle.

ALTER TABLE ads
ADD COLUMN is_closed BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN ads.is_closed IS 'Ad close flag: TRUE when ad is closed by user';
