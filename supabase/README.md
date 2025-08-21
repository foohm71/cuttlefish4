# Supabase Vector Database Integration

This folder contains the Supabase integration for the Cuttlefish4 RAG system, providing vector similarity search and full-text search capabilities for JIRA ticket data.

## 📁 Files Overview

### Core Components
- **`supabase_client.py`** - Main Supabase client with unified search interface
- **`upload_jira_csv_to_supabase.py`** - CSV data upload script with embedding generation
- **`Supabase.md`** - Comprehensive technical documentation and API learnings

### Utilities
- **`nuke_supabase.py`** - Database cleanup and reset utility (⚠️ DESTRUCTIVE)
- **`test_supabase_connection.py`** - Simple connection testing
- **`test_search.py`** - Search functionality testing

## 🚀 Quick Start

### 1. Environment Setup

Create a `.env` file in this directory:

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key
OPENAI_API_KEY=your-openai-api-key
OPENAI_EMBED_MODEL=text-embedding-3-small
BATCH_SIZE=50
```

### 2. Install Dependencies

```bash
pip install -r ../requirements-pinned.txt
```

### 3. Database Setup

Create tables in Supabase SQL Editor (see [Database Schema](#database-schema) below):

```sql
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create tables (bugs and pcr)
-- See full schema in Supabase.md
```

### 4. Upload Data

```bash
# Upload JIRA CSV to both bugs and pcr tables
python upload_jira_csv_to_supabase.py your_jira_data.csv

# Upload to specific table only
python upload_jira_csv_to_supabase.py your_jira_data.csv --tables bugs

# Resume from specific line
python upload_jira_csv_to_supabase.py your_jira_data.csv --start-line 500
```

### 5. Test Search

```bash
# Interactive search testing
python supabase_client.py
```

## 🔍 Search Capabilities

The client provides three search methods:

### Vector Search
- Uses OpenAI embeddings (text-embedding-3-small, 1536 dimensions)
- Cosine similarity matching
- Falls back to text matching if vector RPC unavailable

### Keyword Search  
- PostgreSQL full-text search with tsvector
- Falls back to ILIKE pattern matching
- Automatic query formatting for tsquery

### Hybrid Search
- Combines vector and keyword search results
- Configurable weights (default: 70% vector, 30% keyword)
- Deduplicates and ranks by combined scores

## 💻 Usage Examples

### Basic Usage

```python
from supabase_client import SupabaseVectorClient

client = SupabaseVectorClient()

# Vector search
results = client.search("authentication error", 
                       table="bugs", 
                       search_type="vector", 
                       k=5)

# Keyword search
results = client.search("login failed", 
                       table="bugs", 
                       search_type="keyword", 
                       k=5)

# Hybrid search (recommended)
results = client.search("database timeout", 
                       search_type="hybrid", 
                       k=5,
                       vector_weight=0.7, 
                       keyword_weight=0.3)
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

# Get document by JIRA ID
doc = client.get_by_jira_id("PROJ-123", table_name="bugs")

# Count documents
count = client.count_documents("bugs", filters={"status": "Open"})
```

## 🗃️ Database Schema

### Required Tables: `bugs` and `pcr`

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
    embedding VECTOR(1536), -- OpenAI embeddings
    content_tsvector TSVECTOR, -- Full-text search
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

## 📊 Data Classification

The upload script automatically classifies JIRA tickets:

### PCR (Product Change Request) Classification
Records go to the `pcr` table if they contain:
- **Type**: release, pcr, change, enhancement, feature, improvement, epic, story, task
- **Project**: release, pcr  
- **Title**: release, pcr, feature, enhancement

### Bug Classification
All other records go to the `bugs` table (default), including:
- bug, defect, incident types
- Any records not matching PCR patterns

## 🛠️ Troubleshooting

### Common Issues

#### 1. Zero Search Results
- **Cause**: Database not populated or search methods falling back
- **Check**: Run `python supabase_client.py` for debug output
- **Solution**: Ensure data upload completed and database triggers created

#### 2. Vector Search Not Working  
- **Error**: "RPC function not available"
- **Impact**: Falls back to text matching (still works)
- **Solution**: Create RPC functions in Supabase (see `Supabase.md`)

#### 3. SSL/TLS Upload Errors
- **Error**: `ssl.SSLError: [SSL: BAD_RECORD_MAC]`
- **Solution**: Reduce batch size: `export BATCH_SIZE=50`

#### 4. Missing Dependencies
- **Error**: `ModuleNotFoundError: No module named 'supabase'`
- **Solution**: Install in virtual environment:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  pip install -r ../requirements-pinned.txt
  ```

#### 5. Large CSV Files
- **Error**: CSV field size limit exceeded
- **Solution**: Already handled automatically with `csv.field_size_limit(10000000)`

### Debug Mode Output

When testing searches, you'll see detailed breakdown:

```
🔍 Testing search methods for 'Java' in table 'bugs'

📊 Vector search: 3 results
  1. JBIDE-16273: Java EE Web Project archetype... (sim: 0.85)
  2. SPR-11209: Recently changes of GenericTypeAware... (sim: 0.82)

📝 Keyword search: 2 results  
  1. JBIDE-16273: Java EE Web Project archetype...
  2. SPR-11209: Recently changes of GenericTypeAware...

🔄 Hybrid search: 5 results
  1. JBIDE-16273: Java EE Web Project archetype...
      Combined: 0.91, Vector: 0.85, Keyword: 0.8
```

This shows which search methods are working and their relative performance.

## ⚠️ Important Notes

### Security
- Use **service role key** for SUPABASE_KEY (not anon key)
- Never commit API keys to repository
- Use `.env` file for environment variables

### Performance
- Default similarity threshold: 0.7 (adjust as needed)
- Batch size: 50-100 records (reduce if SSL errors)
- Vector index uses ivfflat with lists=100 (adjust for dataset size)

### Data Persistence
- **NEVER** run `nuke_supabase.py` on production data
- Always backup before schema changes
- Upload script uses `upsert` to handle duplicates

## 📚 Further Reading

- **`Supabase.md`** - Detailed technical documentation with API learnings
- **Supabase Vector Documentation** - https://supabase.com/docs/guides/ai/vector-embeddings
- **pgvector Documentation** - https://github.com/pgvector/pgvector

## 🔧 Maintenance Scripts

```bash
# Check table statistics
python nuke_supabase.py --stats

# Test connections
python test_supabase_connection.py

# Interactive search testing
python test_search.py

# Reset database (⚠️ DESTRUCTIVE)
python nuke_supabase.py --tables bugs --confirm
```

---

For detailed API reference and troubleshooting, see [`Supabase.md`](./Supabase.md).

## License
**BUSL-1.1 (non-production)** — see [LICENSE](../LICENSE).  
Commercial/production use requires a separate agreement with the author.  
On **2029-08-20**, Cuttlefish converts to **Apache-2.0**.

Contact: foohm@kawan2.com