# Supabase Integration Guide

## Overview

This document contains learnings and best practices for working with the Supabase Python client and vector database functionality in the Cuttlefish4 project.

## Key Learnings

### 1. Supabase Python Client API Compatibility

The Supabase Python client (v2.18.0) has specific API patterns that need to be followed:

#### Vector Search Issues
- **Problem**: `.rpc()` method doesn't chain properly with `.select()`
- **Solution**: Call RPC functions directly from the client root, not after table selection
```python
# ❌ Doesn't work
result = client.table(table).select('*').rpc('function_name', params)

# ✅ Works
result = client.rpc('function_name', params).execute()
```

#### Text Search Issues
- **Problem**: `.text_search()` doesn't support `.limit()` chaining
- **Solution**: Apply limit manually after getting results
```python
# ❌ Doesn't work
result = query_builder.text_search('content_tsvector', query).limit(10)

# ✅ Works
result = query_builder.text_search('content_tsvector', query).execute()
data = result.data[:limit]
```

### 2. Method Parameter Patterns

#### Unified Search Interface
Created a unified `search()` method that accepts:
- `query`: Search string
- `table`: Target table ('bugs' or 'pcr')
- `search_type`: Type of search ('vector', 'keyword', 'hybrid')
- `k`: Number of results (standard ML/search parameter name)

#### Backward Compatibility
Individual search methods support both `k` and `limit` parameters:
```python
def vector_search(self, query, table_name='bugs', k=10, limit=None, **kwargs):
    # Use k if provided, otherwise fall back to limit
    result_limit = k if k is not None else (limit if limit is not None else 10)
```

### 3. Error Handling Patterns

#### Graceful Fallbacks
Each search method has fallback mechanisms:
1. **Vector Search**: Falls back to ILIKE text matching if RPC functions unavailable
2. **Keyword Search**: Falls back to ILIKE search if full-text search unavailable
3. **Hybrid Search**: Combines results from both methods, handles partial failures

#### Error Messages
Clear error messages help debug missing dependencies:
- RPC function availability
- Table existence
- Column availability (content_tsvector)

## Database Setup Instructions

The errors you're seeing are expected when the database isn't fully configured. Here's what needs to be set up:

### 1. Missing RPC Function
**Error**: `Could not find the function public.match_documents_vector`
**Status**: This is expected - the RPC function doesn't exist yet
**Impact**: Vector search falls back to ILIKE text matching (still works)

### 2. Text Search Query Format
**Error**: `syntax error in tsquery: "login failed"`
**Fix**: Multi-word queries need proper PostgreSQL tsquery formatting
**Solution**: Queries are now automatically formatted with `&` operators

### 3. Missing tsvector Column
**Impact**: Full-text search falls back to ILIKE matching

## Database Schema Requirements

### Required Extensions
```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

### Table Schema
```sql
CREATE TABLE bugs (
    id BIGSERIAL PRIMARY KEY,
    jira_id TEXT,
    key TEXT,
    project TEXT,
    project_name TEXT,
    priority TEXT,
    type TEXT,
    status TEXT,
    created TIMESTAMP,
    resolved TIMESTAMP,
    updated TIMESTAMP,
    component TEXT,
    version TEXT,
    reporter TEXT,
    assignee TEXT,
    title TEXT,
    description TEXT,
    content TEXT, -- Formatted content for RAG
    embedding VECTOR(1536), -- OpenAI text-embedding-3-small dimension
    content_tsvector TSVECTOR, -- For full-text search
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Required Indexes
```sql
-- Vector similarity search
CREATE INDEX bugs_embedding_idx ON bugs 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Full-text search
CREATE INDEX bugs_content_search_idx ON bugs 
    USING GIN (content_tsvector);

-- Standard indexes
CREATE INDEX bugs_jira_id_idx ON bugs (jira_id);
CREATE INDEX bugs_key_idx ON bugs (key);
CREATE INDEX bugs_project_idx ON bugs (project);
CREATE INDEX bugs_type_idx ON bugs (type);
CREATE INDEX bugs_status_idx ON bugs (status);
```

### Automatic tsvector Updates
```sql
CREATE OR REPLACE FUNCTION bugs_tsvector_trigger() RETURNS trigger AS $$
BEGIN
    NEW.content_tsvector := to_tsvector('english', 
        COALESCE(NEW.title, '') || ' ' || COALESCE(NEW.description, ''));
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

CREATE TRIGGER bugs_tsvector_update BEFORE INSERT OR UPDATE
    ON bugs FOR EACH ROW EXECUTE FUNCTION bugs_tsvector_trigger();
```

### Required RPC Functions

#### Vector Similarity Search Function
```sql
CREATE OR REPLACE FUNCTION match_documents_vector(
    query_embedding vector(1536),
    match_table text,
    match_count int DEFAULT 10,
    similarity_threshold float DEFAULT 0.7
)
RETURNS TABLE(
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
    created_at timestamp,
    updated_at timestamp
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
            1 - (bugs.embedding <=> query_embedding) as similarity,
            bugs.created_at,
            bugs.updated_at
        FROM bugs
        WHERE 1 - (bugs.embedding <=> query_embedding) > similarity_threshold
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
            1 - (pcr.embedding <=> query_embedding) as similarity,
            pcr.created_at,
            pcr.updated_at
        FROM pcr
        WHERE 1 - (pcr.embedding <=> query_embedding) > similarity_threshold
        ORDER BY pcr.embedding <=> query_embedding
        LIMIT match_count;
    END IF;
END;
$$;
```

## Upload Script Usage

### Environment Variables
Create a `.env` file with:
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key
OPENAI_API_KEY=your-openai-api-key
OPENAI_EMBED_MODEL=text-embedding-3-small
BATCH_SIZE=50
```

### CSV Requirements
The upload script expects CSV files with these columns:
- `id`, `key`, `project`, `project_name`
- `priority`, `type`, `status`
- `created`, `resolved`, `updated`
- `component`, `version`, `reporter`, `assignee`
- `title`, `description`

### Large Description Handling
Set CSV field size limit for large JIRA descriptions:
```python
csv.field_size_limit(10000000)
```

### Record Classification
The script automatically classifies records into 'bugs' and 'pcr' tables based on:

**PCR Classification Patterns:**
- Type contains: release, pcr, change, enhancement, feature, improvement, epic, story, task
- Project contains: release, pcr
- Title contains: release, pcr, feature, enhancement

**Default to Bugs:**
- All other records (including bug, defect, incident types)

### Usage Examples
```bash
# Upload to both tables
python upload_jira_csv_to_supabase.py JIRA_DATA.csv

# Upload to specific table only
python upload_jira_csv_to_supabase.py JIRA_DATA.csv --tables bugs

# Resume from specific line
python upload_jira_csv_to_supabase.py JIRA_DATA.csv --start-line 500
```

### Batch Size Optimization
- Default batch size: 100 records
- Reduce to 50 if experiencing SSL/TLS errors
- Adjust via environment variable: `BATCH_SIZE=50`

## Client Usage Examples

### Basic Search Operations
```python
from supabase_client import SupabaseVectorClient

client = SupabaseVectorClient()

# Vector search
results = client.search("authentication error", table="bugs", search_type="vector", k=5)

# Keyword search
results = client.search("login failed", table="bugs", search_type="keyword", k=5)

# Hybrid search
results = client.search("database timeout", search_type="hybrid", k=5,
                       vector_weight=0.7, keyword_weight=0.3)
```

### Advanced Usage
```python
# Search with filters
results = client.vector_search(
    query="connection timeout",
    table_name="bugs",
    k=10,
    similarity_threshold=0.8,
    filters={"project": "MyProject", "status": "Open"}
)

# Get document by ID
doc = client.get_by_jira_id("PROJ-123", table_name="bugs")

# Count documents
count = client.count_documents("bugs", filters={"status": "Open"})
```

## Common Issues and Solutions

### 1. Missing Dependencies
**Error**: `ModuleNotFoundError: No module named 'supabase'`
**Solution**: Install in virtual environment or use system override
```bash
# Virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-pinned.txt

# System override (not recommended)
pip install --break-system-packages supabase==2.18.0
```

### 2. SSL/TLS Errors During Upload
**Error**: `ssl.SSLError: [SSL: BAD_RECORD_MAC] bad record mac`
**Solution**: Reduce batch size
```bash
export BATCH_SIZE=50
```

### 3. Vector Search Not Working
**Error**: `RPC function not available`
**Solution**: Create required RPC functions in Supabase or ensure fallback works
- Vector search falls back to ILIKE text matching
- Check database logs for function creation errors

### 4. Full-text Search Not Working
**Error**: `column "content_tsvector" does not exist`
**Solution**: Ensure table schema includes tsvector column and trigger

### 5. Zero PCR Records Found
**Error**: Division by zero in upload statistics
**Solution**: Enhanced classification patterns now catch more PCR types

### 6. Text Search Syntax Errors
**Error**: `syntax error in tsquery: "login failed"`
**Root Cause**: PostgreSQL tsquery requires proper formatting for multi-word queries
**Solution**: Queries are automatically formatted (spaces replaced with ` & `)

### 7. Current Status (Expected Behavior)
When you run `supabase_client.py`, you should see:
```
✅ Table 'bugs' is accessible  
✅ Table 'pcr' is accessible
✅ Connection test passed

🔍 Testing unified search interface...
RPC function not available: [error about match_documents_vector]
Vector search error: Vector search RPC function not available
Vector search (bugs): 0 results

Full-text search not available: [tsvector error]  
Keyword search error: Full-text search not available
Keyword search (bugs): 0 results

Hybrid search (bugs): 2 results  ← This should work via fallbacks!
```

**This is normal!** The hybrid search works because it falls back to ILIKE matching.

## Performance Considerations

### Vector Search
- Use appropriate similarity thresholds (0.7-0.8 typically good)
- Vector index using ivfflat with lists=100 for moderate dataset sizes
- Consider adjusting lists parameter for larger datasets

### Keyword Search
- GIN index on tsvector provides fast full-text search
- Manual limit application due to API limitations
- Fallback to ILIKE for broader compatibility

### Hybrid Search
- Combines both methods with configurable weights
- Fetches 2x desired results from each method for better ranking
- Deduplicates and scores based on combined relevance

## Future Improvements

1. **RPC Functions**: Implement proper vector similarity RPC functions in Supabase
2. **Pagination**: Add proper pagination support for large result sets
3. **Caching**: Implement embedding caching for repeated queries
4. **Monitoring**: Add query performance monitoring and logging
5. **Schema Evolution**: Version management for schema changes