-- ============================================================================
-- AI Wingman - Database Initialization Script
-- ============================================================================
-- This script runs automatically on first container startup
-- Creates tables, indexes, and enables required extensions

-- Enable required PostgreSQL extensions
-- ----------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create schema for organization
-- ----------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS ai_wingman;
SET search_path TO ai_wingman, public;

-- Main table: Slack messages with vector embeddings
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS slack_messages (
    -- Primary identifier
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Slack metadata
    slack_message_id VARCHAR(100) NOT NULL UNIQUE,
    channel_id VARCHAR(100) NOT NULL,
    channel_name VARCHAR(255),
    user_id VARCHAR(100) NOT NULL,
    user_name VARCHAR(255),
    
    -- Message content
    message_text TEXT NOT NULL,
    message_type VARCHAR(50) DEFAULT 'message',
    
    -- Vector embedding for semantic search
    embedding vector(384),  -- 384 dimensions for all-MiniLM-L6-v2
    
    -- Timestamps
    slack_timestamp DECIMAL(16, 6) NOT NULL,  -- Slack's timestamp format
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Additional metadata (JSON for flexibility)
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Soft delete flag
    is_deleted BOOLEAN DEFAULT FALSE
);

-- Performance indexes
-- ----------------------------------------------------------------------------
-- Index for fast user lookups
CREATE INDEX idx_slack_messages_user_id 
    ON slack_messages(user_id) 
    WHERE is_deleted = FALSE;

-- Index for channel-based queries
CREATE INDEX idx_slack_messages_channel_id 
    ON slack_messages(channel_id) 
    WHERE is_deleted = FALSE;

-- Index for time-based queries
CREATE INDEX idx_slack_messages_timestamp 
    ON slack_messages(slack_timestamp DESC) 
    WHERE is_deleted = FALSE;

-- Vector similarity search index (HNSW algorithm)
CREATE INDEX idx_slack_messages_embedding 
    ON slack_messages 
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Alternative: IVFFlat index (faster build, slightly slower search)
-- CREATE INDEX idx_slack_messages_embedding 
--     ON slack_messages 
--     USING ivfflat (embedding vector_cosine_ops)
--     WITH (lists = 100);

-- Metadata search index
CREATE INDEX idx_slack_messages_metadata 
    ON slack_messages USING gin(metadata);

-- Composite index for filtered vector search
CREATE INDEX idx_slack_messages_user_embedding 
    ON slack_messages(user_id, embedding);

-- Table: User context summaries (for personalization)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_contexts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(100) NOT NULL UNIQUE,
    user_name VARCHAR(255),
    
    -- Aggregated insights
    total_messages INTEGER DEFAULT 0,
    first_message_at TIMESTAMP,
    last_message_at TIMESTAMP,
    
    -- User preferences and patterns
    communication_style TEXT,
    topics_of_interest JSONB DEFAULT '[]'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: Conversation threads (for context grouping)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conversation_threads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    thread_ts DECIMAL(16, 6) NOT NULL UNIQUE,  -- Slack thread timestamp
    channel_id VARCHAR(100) NOT NULL,
    
    -- Thread summary
    summary TEXT,
    participant_count INTEGER DEFAULT 0,
    message_count INTEGER DEFAULT 0,
    
    -- Timestamps
    started_at TIMESTAMP,
    last_activity_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Helper function: Update updated_at timestamp
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for automatic timestamp updates
-- ----------------------------------------------------------------------------
CREATE TRIGGER trigger_slack_messages_updated_at
    BEFORE UPDATE ON slack_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_user_contexts_updated_at
    BEFORE UPDATE ON user_contexts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Helper function: Vector similarity search
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION search_similar_messages(
    query_embedding vector(384),
    similarity_threshold FLOAT DEFAULT 0.7,
    result_limit INTEGER DEFAULT 5
)
RETURNS TABLE (
    message_id UUID,
    message_text TEXT,
    user_name VARCHAR,
    channel_name VARCHAR,
    similarity FLOAT,
    slack_timestamp DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        sm.id,
        sm.message_text,
        sm.user_name,
        sm.channel_name,
        1 - (sm.embedding <=> query_embedding) AS similarity,
        sm.slack_timestamp
    FROM slack_messages sm
    WHERE 
        sm.is_deleted = FALSE
        AND sm.embedding IS NOT NULL
        AND 1 - (sm.embedding <=> query_embedding) >= similarity_threshold
    ORDER BY sm.embedding <=> query_embedding
    LIMIT result_limit;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions (if using non-superuser)
-- ----------------------------------------------------------------------------
-- GRANT ALL PRIVILEGES ON SCHEMA ai_wingman TO wingman;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA ai_wingman TO wingman;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA ai_wingman TO wingman;

-- Completion message
-- ----------------------------------------------------------------------------
DO $$ 
BEGIN 
    RAISE NOTICE 'AI Wingman database initialized successfully!';
    RAISE NOTICE 'Schema: ai_wingman';
    RAISE NOTICE 'Tables: slack_messages, user_contexts, conversation_threads';
    RAISE NOTICE 'Indexes: Optimized for vector similarity search';
END $$;
