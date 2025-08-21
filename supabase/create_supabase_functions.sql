-- SQL functions to be created in Supabase for vector search support
-- Execute these in the Supabase SQL Editor

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Function for vector similarity search with cosine distance
CREATE OR REPLACE FUNCTION match_documents_vector(
  query_embedding vector(1536),
  match_table text,
  match_threshold float DEFAULT 0.7,
  match_count int DEFAULT 10
)
RETURNS TABLE (
  id bigint,
  jira_id text,
  key text,
  project text,
  project_name text,
  priority text,
  type text,
  status text,
  created timestamp,
  resolved timestamp,
  updated timestamp,
  component text,
  version text,
  reporter text,
  assignee text,
  title text,
  description text,
  content text,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  IF match_table = 'bugs' THEN
    RETURN QUERY
    SELECT 
      bugs.id,
      bugs.jira_id,
      bugs.key,
      bugs.project,
      bugs.project_name,
      bugs.priority,
      bugs.type,
      bugs.status,
      bugs.created,
      bugs.resolved,
      bugs.updated,
      bugs.component,
      bugs.version,
      bugs.reporter,
      bugs.assignee,
      bugs.title,
      bugs.description,
      bugs.content,
      1 - (bugs.embedding <=> query_embedding) AS similarity
    FROM bugs
    WHERE 1 - (bugs.embedding <=> query_embedding) > match_threshold
    ORDER BY bugs.embedding <=> query_embedding
    LIMIT match_count;
    
  ELSIF match_table = 'pcr' THEN
    RETURN QUERY
    SELECT 
      pcr.id,
      pcr.jira_id,
      pcr.key,
      pcr.project,
      pcr.project_name,
      pcr.priority,
      pcr.type,
      pcr.status,
      pcr.created,
      pcr.resolved,
      pcr.updated,
      pcr.component,
      pcr.version,
      pcr.reporter,
      pcr.assignee,
      pcr.title,
      pcr.description,
      pcr.content,
      1 - (pcr.embedding <=> query_embedding) AS similarity
    FROM pcr
    WHERE 1 - (pcr.embedding <=> query_embedding) > match_threshold
    ORDER BY pcr.embedding <=> query_embedding
    LIMIT match_count;
    
  ELSE
    RAISE EXCEPTION 'Invalid table name: %', match_table;
  END IF;
END;
$$;

-- Function for keyword search using full-text search
CREATE OR REPLACE FUNCTION match_documents_keyword(
  query_text text,
  match_table text,
  match_count int DEFAULT 10
)
RETURNS TABLE (
  id bigint,
  jira_id text,
  key text,
  project text,
  project_name text,
  priority text,
  type text,
  status text,
  created timestamp,
  resolved timestamp,
  updated timestamp,
  component text,
  version text,
  reporter text,
  assignee text,
  title text,
  description text,
  content text,
  rank float
)
LANGUAGE plpgsql
AS $$
BEGIN
  IF match_table = 'bugs' THEN
    RETURN QUERY
    SELECT 
      bugs.id,
      bugs.jira_id,
      bugs.key,
      bugs.project,
      bugs.project_name,
      bugs.priority,
      bugs.type,
      bugs.status,
      bugs.created,
      bugs.resolved,
      bugs.updated,
      bugs.component,
      bugs.version,
      bugs.reporter,
      bugs.assignee,
      bugs.title,
      bugs.description,
      bugs.content,
      ts_rank(bugs.content_tsvector, plainto_tsquery('english', query_text)) AS rank
    FROM bugs
    WHERE bugs.content_tsvector @@ plainto_tsquery('english', query_text)
    ORDER BY ts_rank(bugs.content_tsvector, plainto_tsquery('english', query_text)) DESC
    LIMIT match_count;
    
  ELSIF match_table = 'pcr' THEN
    RETURN QUERY
    SELECT 
      pcr.id,
      pcr.jira_id,
      pcr.key,
      pcr.project,
      pcr.project_name,
      pcr.priority,
      pcr.type,
      pcr.status,
      pcr.created,
      pcr.resolved,
      pcr.updated,
      pcr.component,
      pcr.version,
      pcr.reporter,
      pcr.assignee,
      pcr.title,
      pcr.description,
      pcr.content,
      ts_rank(pcr.content_tsvector, plainto_tsquery('english', query_text)) AS rank
    FROM pcr
    WHERE pcr.content_tsvector @@ plainto_tsquery('english', query_text)
    ORDER BY ts_rank(pcr.content_tsvector, plainto_tsquery('english', query_text)) DESC
    LIMIT match_count;
    
  ELSE
    RAISE EXCEPTION 'Invalid table name: %', match_table;
  END IF;
END;
$$;

-- Function for hybrid search combining vector and keyword search
CREATE OR REPLACE FUNCTION match_documents_hybrid(
  query_text text,
  query_embedding vector(1536),
  match_table text,
  match_threshold float DEFAULT 0.7,
  match_count int DEFAULT 10,
  vector_weight float DEFAULT 0.7,
  keyword_weight float DEFAULT 0.3
)
RETURNS TABLE (
  id bigint,
  jira_id text,
  key text,
  project text,
  project_name text,
  priority text,
  type text,
  status text,
  created timestamp,
  resolved timestamp,
  updated timestamp,
  component text,
  version text,
  reporter text,
  assignee text,
  title text,
  description text,
  content text,
  similarity float,
  keyword_rank float,
  combined_score float
)
LANGUAGE plpgsql
AS $$
BEGIN
  IF match_table = 'bugs' THEN
    RETURN QUERY
    SELECT 
      bugs.id,
      bugs.jira_id,
      bugs.key,
      bugs.project,
      bugs.project_name,
      bugs.priority,
      bugs.type,
      bugs.status,
      bugs.created,
      bugs.resolved,
      bugs.updated,
      bugs.component,
      bugs.version,
      bugs.reporter,
      bugs.assignee,
      bugs.title,
      bugs.description,
      bugs.content,
      1 - (bugs.embedding <=> query_embedding) AS similarity,
      COALESCE(ts_rank(bugs.content_tsvector, plainto_tsquery('english', query_text)), 0) AS keyword_rank,
      (
        (1 - (bugs.embedding <=> query_embedding)) * vector_weight + 
        COALESCE(ts_rank(bugs.content_tsvector, plainto_tsquery('english', query_text)), 0) * keyword_weight
      ) AS combined_score
    FROM bugs
    WHERE 
      (1 - (bugs.embedding <=> query_embedding)) > match_threshold OR
      bugs.content_tsvector @@ plainto_tsquery('english', query_text)
    ORDER BY combined_score DESC
    LIMIT match_count;
    
  ELSIF match_table = 'pcr' THEN
    RETURN QUERY
    SELECT 
      pcr.id,
      pcr.jira_id,
      pcr.key,
      pcr.project,
      pcr.project_name,
      pcr.priority,
      pcr.type,
      pcr.status,
      pcr.created,
      pcr.resolved,
      pcr.updated,
      pcr.component,
      pcr.version,
      pcr.reporter,
      pcr.assignee,
      pcr.title,
      pcr.description,
      pcr.content,
      1 - (pcr.embedding <=> query_embedding) AS similarity,
      COALESCE(ts_rank(pcr.content_tsvector, plainto_tsquery('english', query_text)), 0) AS keyword_rank,
      (
        (1 - (pcr.embedding <=> query_embedding)) * vector_weight + 
        COALESCE(ts_rank(pcr.content_tsvector, plainto_tsquery('english', query_text)), 0) * keyword_weight
      ) AS combined_score
    FROM pcr
    WHERE 
      (1 - (pcr.embedding <=> query_embedding)) > match_threshold OR
      pcr.content_tsvector @@ plainto_tsquery('english', query_text)
    ORDER BY combined_score DESC
    LIMIT match_count;
    
  ELSE
    RAISE EXCEPTION 'Invalid table name: %', match_table;
  END IF;
END;
$$;

-- Create indexes for optimal performance
-- These should be created after the tables are populated

-- Vector indexes for cosine similarity
CREATE INDEX IF NOT EXISTS bugs_embedding_cosine_idx ON bugs USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS pcr_embedding_cosine_idx ON pcr USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Full-text search indexes
CREATE INDEX IF NOT EXISTS bugs_content_search_idx ON bugs USING GIN (content_tsvector);
CREATE INDEX IF NOT EXISTS pcr_content_search_idx ON pcr USING GIN (content_tsvector);

-- Standard indexes for filtering
CREATE INDEX IF NOT EXISTS bugs_jira_id_idx ON bugs (jira_id);
CREATE INDEX IF NOT EXISTS bugs_project_idx ON bugs (project);
CREATE INDEX IF NOT EXISTS bugs_type_idx ON bugs (type);
CREATE INDEX IF NOT EXISTS bugs_status_idx ON bugs (status);
CREATE INDEX IF NOT EXISTS bugs_created_idx ON bugs (created);

CREATE INDEX IF NOT EXISTS pcr_jira_id_idx ON pcr (jira_id);
CREATE INDEX IF NOT EXISTS pcr_project_idx ON pcr (project);
CREATE INDEX IF NOT EXISTS pcr_type_idx ON pcr (type);
CREATE INDEX IF NOT EXISTS pcr_status_idx ON pcr (status);
CREATE INDEX IF NOT EXISTS pcr_created_idx ON pcr (created);

-- Grant permissions for the functions (adjust as needed for your setup)
-- GRANT EXECUTE ON FUNCTION match_documents_vector TO authenticated;
-- GRANT EXECUTE ON FUNCTION match_documents_keyword TO authenticated;
-- GRANT EXECUTE ON FUNCTION match_documents_hybrid TO authenticated;