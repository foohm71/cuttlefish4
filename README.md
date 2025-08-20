# Cuttlefish Multi-Agent RAG System

A comprehensive JIRA ticket retrieval system using multi-agent RAG architecture with intelligent query routing and specialized retrieval strategies.

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- OpenAI API key
- Supabase account and project
- Optional: Qdrant instance (for legacy support)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd cuttlefish4
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

Required environment variables:
```bash
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_EMBED_MODEL=text-embedding-3-small

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key

# Optional: Qdrant (legacy support)
QDRANT_URL=https://your-qdrant-instance.com
QDRANT_API_KEY=your-qdrant-key
QDRANT_COLLECTION=cuttlefish3
```

4. Set up Supabase database:
```bash
# Execute the SQL functions in suprabase/create_supabase_functions.sql
# in your Supabase SQL Editor
```

5. Upload data to Supabase:
```bash
python suprabase/upload_jira_csv_to_supabase.py your_jira_data.csv
```

6. Start the server:
```bash
# Development
python -m app.api.main

# Or with uvicorn
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```

## 🏗️ Architecture

### Multi-Agent System

The system uses specialized agents for different retrieval strategies:

- **SupervisorAgent** (GPT-4o): Intelligent query routing
- **BM25Agent** (GPT-4o-mini): Keyword-based search  
- **ContextualCompressionAgent** (GPT-4o-mini): Fast semantic search with reranking
- **EnsembleAgent** (GPT-4o-mini): Comprehensive multi-method retrieval
- **ResponseWriterAgent** (GPT-4o): Final response generation

### Directory Structure

```
app/
├── __init__.py
├── agents/           # Multi-agent system
│   ├── __init__.py
│   ├── common.py     # Shared utilities
│   ├── supervisor_agent.py
│   ├── bm25_agent.py
│   ├── contextual_compression_agent.py  
│   ├── ensemble_agent.py
│   └── response_writer_agent.py
├── rag/              # RAG retrieval functions
│   ├── __init__.py
│   └── supabase_retriever.py
├── tools/            # Tools mapping RAG functions
│   ├── __init__.py
│   └── rag_tools.py
└── api/              # FastAPI application
    ├── __init__.py
    ├── main.py       # FastAPI app and endpoints
    ├── models.py     # Pydantic models
    └── workflow.py   # Multi-agent workflow

suprabase/            # Supabase integration
├── upload_jira_csv_to_supabase.py
├── supabase_client.py
└── create_supabase_functions.sql

references/           # Original implementation
├── Cuttlefish3_Complete.ipynb
└── qdrant/          # Legacy Qdrant scripts
```

## 🔗 API Endpoints

### Main Endpoints

1. **Multi-Agent RAG** - `POST /multiagent-rag`
   - Intelligent JIRA ticket retrieval with routing
   - Parameters: query, user_can_wait, production_incident, openai_api_key

2. **Debug Routing** - `POST /debug/routing` 
   - Test routing decisions without full processing
   - Parameters: query, user_can_wait, production_incident

3. **Health Check** - `GET /health`
   - Service status and configuration

4. **Test Interface** - `GET /`
   - Interactive HTML testing interface

### Example Usage

```python
import requests

# Multi-agent search
response = requests.post('http://localhost:8000/multiagent-rag', json={
    "query": "authentication error in login system",
    "user_can_wait": False,
    "production_incident": True
})

# Debug routing
response = requests.post('http://localhost:8000/debug/routing', json={
    "query": "HBASE-123 connection timeout",
    "user_can_wait": False, 
    "production_incident": False
})
```

## 🔍 Retrieval Methods

### Vector Search
- Cosine similarity using OpenAI embeddings
- Supports both bugs and pcr collections
- Configurable similarity thresholds

### Keyword Search  
- Full-text search using PostgreSQL tsvector
- BM25-style scoring
- Optimized for specific ticket references

### Hybrid Search
- Combines vector and keyword search
- Weighted scoring with configurable weights
- Best of both semantic and exact matching

## 🤖 Agent Routing Logic

The SupervisorAgent routes queries based on:

- **BM25**: Specific ticket references (e.g., "HBASE-123")
- **ContextualCompression**: Production incidents or when speed is critical  
- **Ensemble**: When user can wait for comprehensive results
- **Default**: ContextualCompression for balanced performance

## 📊 Database Schema

### Supabase Tables

Both `bugs` and `pcr` tables share the same schema:

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
    content TEXT,
    embedding VECTOR(1536),
    content_tsvector TSVECTOR,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

## 🛠️ Development

### Running Tests

```bash
# Install test dependencies  
pip install pytest pytest-asyncio

# Run tests
pytest tests/
```

### Code Quality

```bash
# Format code
black app/

# Sort imports
isort app/

# Type checking
mypy app/
```

## 🚢 Deployment

### Docker

```bash
# Build image
docker build -t cuttlefish-rag .

# Run container
docker run -p 8000:8000 --env-file .env cuttlefish-rag
```

### Production Considerations

- Use proper CORS origins (not "*")
- Set up proper logging and monitoring
- Use a production WSGI server like Gunicorn
- Configure Supabase connection pooling
- Set up proper secret management
- Enable rate limiting and authentication

## 🔧 Configuration

### Environment Variables

See `.env.example` for full configuration options.

### Supabase Setup

1. Create a new Supabase project
2. Enable the `vector` and `pg_trgm` extensions
3. Execute the SQL functions from `suprabase/create_supabase_functions.sql`
4. Upload your JIRA data using the upload scripts

## 📈 Performance

- **Production Incidents**: ~21s average response time
- **Comprehensive Search**: ~47s with ensemble methods  
- **Vector Search**: Sub-second retrieval from Supabase
- **Keyword Search**: Fast full-text search with PostgreSQL

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure code quality checks pass
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Troubleshooting

### Common Issues

1. **Connection Errors**: Check your Supabase credentials and network connectivity
2. **OpenAI API Errors**: Verify your API key and rate limits
3. **Empty Results**: Ensure your data is properly uploaded and indexed
4. **Performance Issues**: Check your Supabase database performance metrics

### Getting Help

- Check the API documentation at `/docs`
- Use the test interface at `/` for debugging
- Check logs for detailed error messages
- Verify environment variables are set correctly

## 🔄 Migration from Cuttlefish3

This version (Cuttlefish4) provides the same API endpoints as Cuttlefish3 but with:

- Restructured codebase with proper separation of concerns
- FastAPI instead of Flask for better performance and documentation
- Supabase integration alongside Qdrant support
- Enhanced error handling and logging
- Improved test interface and debugging capabilities

The migration maintains backward compatibility with existing API clients.