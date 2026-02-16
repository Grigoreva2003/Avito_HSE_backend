-- Migration: V003 - Moderation Results Table
-- Description: Create table for storing asynchronous moderation results

CREATE TABLE moderation_results (
    id SERIAL PRIMARY KEY,
    item_id INTEGER NOT NULL REFERENCES ads(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    is_violation BOOLEAN,
    probability FLOAT,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for better query performance
CREATE INDEX idx_moderation_results_item_id ON moderation_results(item_id);
CREATE INDEX idx_moderation_results_status ON moderation_results(status);
CREATE INDEX idx_moderation_results_created_at ON moderation_results(created_at);

-- Constraint for status values
ALTER TABLE moderation_results 
ADD CONSTRAINT check_status 
CHECK (status IN ('pending', 'completed', 'failed'));

-- Comments
COMMENT ON TABLE moderation_results IS 'Asynchronous moderation results for ads';
COMMENT ON COLUMN moderation_results.status IS 'Moderation status: pending, completed, failed';
COMMENT ON COLUMN moderation_results.is_violation IS 'Moderation result (NULL if not processed yet)';
COMMENT ON COLUMN moderation_results.probability IS 'Violation probability (0.0 to 1.0)';
COMMENT ON COLUMN moderation_results.error_message IS 'Error message if status is failed';
COMMENT ON COLUMN moderation_results.processed_at IS 'Processing timestamp (NULL if still pending)';
