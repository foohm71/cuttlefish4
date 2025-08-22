# Cuttlefish4 Multi-Agent RAG API

Intelligent JIRA ticket retrieval using a multi-agent RAG (Retrieval-Augmented Generation) system. This API provides sophisticated query processing with intelligent routing to specialized agents based on query characteristics.

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Virtual environment (recommended)
- Required environment variables (see [Environment Setup](#environment-setup))

### Installation

1. **Clone and navigate to the project:**
   ```bash
   cd /Users/foohm/github/cuttlefish4
   ```

2. **Activate virtual environment:**
   ```bash
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Environment Setup

Create a `.env` file in the project root with the following variables:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_EMBED_MODEL=text-embedding-3-small

# Supabase Configuration
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_anon_key_here

# Optional: Qdrant Configuration (for vectorstore)
QDRANT_URL=your_qdrant_url_here
QDRANT_API_KEY=your_qdrant_api_key_here
QDRANT_COLLECTION=cuttlefish3

# RAG Backend Configuration
RAG_BACKEND=auto  # Options: 'qdrant', 'supabase', 'auto'

# Search Configuration
SIMILARITY_THRESHOLD=0.1  # Similarity threshold for vector search (0.0-1.0)

# Application Configuration
CUTTLEFISH_HOME=/Users/foohm/github/cuttlefish4
PORT=8000
HOST=127.0.0.1
```

## 🏃‍♂️ Starting the Server

### Method 1: Direct Python Execution

```bash
cd app/api
python main.py
```

### Method 2: Using Uvicorn

```bash
cd app/api
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### Method 3: Using the Project Script

```bash
# From project root
python run_server.py
```

The server will start on `http://localhost:8000` with the following endpoints:

- **API Documentation**: `http://localhost:8000/docs` (Swagger UI)
- **ReDoc Documentation**: `http://localhost:8000/redoc`
- **Interactive Test Interface**: `http://localhost:8000/`
- **Health Check**: `http://localhost:8000/health`

## 🧪 Testing

### 1. Automated Testing

#### API Testing
```bash
# Run the automated API test script
cd app/api
python test_api.py
```

#### Supabase Agents Testing
```bash
# Test the new Supabase-based agents
cd app/agents
python TestSupabaseAgents.py
```

#### Backend Switching Testing
```bash
# Test the backend switching functionality
cd app/api
python test_backend_switching.py
```

### 2. Notebook Testing

The project includes comprehensive Jupyter notebooks for testing different components:

#### TestAgentWorkflow.ipynb
Tests the complete multi-agent workflow system:

```bash
cd app/api
jupyter notebook TestAgentWorkflow.ipynb
```

**Test Coverage:**
- ✅ Workflow initialization and component setup
- ✅ Supervisor routing decisions
- ✅ Supabase fallback methods (BM25, Vector, Hybrid)
- ✅ Complete query processing pipeline
- ✅ Error handling and edge cases
- ✅ Performance metrics and timing

**Running the Tests:**
1. Open the notebook in Jupyter
2. Run cells sequentially from top to bottom
3. Monitor the output for test results and any errors
4. Check the final test report for overall system health

#### Other Test Notebooks
- `app/agents/TestAgents.ipynb` - Individual agent testing
- `references/Cuttlefish3_Complete.ipynb` - Legacy system testing

### 2. Postman Testing

Import the provided Postman collection for API testing:

#### Import Collection
1. Open Postman
2. Click "Import" → "File" → Select `Cuttlefish4_API.postman_collection.json`
3. The collection will be imported with all endpoints and test examples

#### Environment Variables
Set up a Postman environment with these variables:
- `base_url`: `http://localhost:8000`
- `custom_query`: Your test query
- `user_can_wait`: `false` or `true`
- `production_incident`: `false` or `true`
- `openai_api_key`: Your OpenAI API key (optional)

#### Test Scenarios

**Health Check:**
- Endpoint: `GET /health`
- Purpose: Verify API is running and healthy
- Expected: 200 status with service information

**Production Incident Query:**
```json
{
  "query": "database connection timeout causing login failures",
  "user_can_wait": false,
  "production_incident": true,
  "openai_api_key": null
}
```

**Comprehensive Analysis Query:**
```json
{
  "query": "authentication error patterns in recent tickets",
  "user_can_wait": true,
  "production_incident": false,
  "openai_api_key": null
}
```

**Specific Ticket Query:**
```json
{
  "query": "HBASE-12345 connection timeout issue details",
  "user_can_wait": false,
  "production_incident": false,
  "openai_api_key": null
}
```

**Debug Routing:**
```json
{
  "query": "authentication error in login system",
  "user_can_wait": false,
  "production_incident": false
}
```

### 3. Interactive Web Interface

Access the built-in test interface:
```
http://localhost:8000/
```

This provides a user-friendly web form for testing all API endpoints without needing Postman.

### 4. Command Line Testing

#### Health Check
```bash
curl http://localhost:8000/health
```

#### Multi-Agent RAG Query
```bash
curl -X POST http://localhost:8000/multiagent-rag \
  -H "Content-Type: application/json" \
  -d '{
    "query": "authentication error in login system",
    "user_can_wait": false,
    "production_incident": false,
    "openai_api_key": null
  }'
```

#### Debug Routing
```bash
curl -X POST http://localhost:8000/debug/routing \
  -H "Content-Type: application/json" \
  -d '{
    "query": "authentication error in login system",
    "user_can_wait": false,
    "production_incident": false
  }'
```

## 📊 API Endpoints

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check and service status |
| `/multiagent-rag` | POST | Main RAG query processing |
| `/debug/routing` | POST | Test routing decisions only |
| `/` | GET | Interactive test interface |
| `/docs` | GET | Swagger API documentation |
| `/redoc` | GET | ReDoc API documentation |

### Request/Response Models

#### MultiAgentRAGRequest
```json
{
  "query": "string (required)",
  "user_can_wait": "boolean (default: false)",
  "production_incident": "boolean (default: false)",
  "openai_api_key": "string (optional)"
}
```

#### MultiAgentRAGResponse
```json
{
  "query": "string",
  "final_answer": "string",
  "relevant_tickets": [
    {
      "key": "string",
      "title": "string"
    }
  ],
  "routing_decision": "string",
  "routing_reasoning": "string",
  "retrieval_method": "string",
  "retrieved_contexts": [...],
  "retrieval_metadata": {...},
  "timestamp": "string",
  "total_processing_time": "number"
}
```

## 🤖 Multi-Agent System

### Agent Types

1. **Supervisor Agent** (GPT-4o)
   - Routes queries to appropriate retrieval agents
   - Analyzes query characteristics and urgency

2. **BM25 Agent**
   - Keyword-based search for exact matches
   - Best for specific ticket references

3. **Contextual Compression Agent**
   - Semantic search with content compression
   - Default for general technical queries

4. **Ensemble Agent**
   - Combines multiple retrieval methods
   - Used for comprehensive analysis

5. **Response Writer Agent** (GPT-4o)
   - Generates final responses
   - Synthesizes retrieved information

### Routing Logic

| Query Type | Conditions | Agent Selected |
|------------|------------|----------------|
| Production Incident | `production_incident: true` | ContextualCompression |
| Comprehensive Analysis | `user_can_wait: true` | Ensemble |
| Specific Ticket | Contains ticket number | BM25 |
| General Query | Default | ContextualCompression |

## 🔧 Configuration

### Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `OPENAI_API_KEY` | Yes | OpenAI API key | - |
| `SUPABASE_URL` | Yes | Supabase project URL | - |
| `SUPABASE_KEY` | Yes | Supabase anon key | - |
| `OPENAI_EMBED_MODEL` | No | Embedding model | `text-embedding-3-small` |
| `QDRANT_URL` | No | Qdrant vectorstore URL | - |
| `QDRANT_API_KEY` | No | Qdrant API key | - |
| `PORT` | No | Server port | `8000` |
| `HOST` | No | Server host | `127.0.0.1` |

### Database Configuration

The system supports two database backends that can be switched using the `RAG_BACKEND` environment variable:

#### Backend Options

1. **`RAG_BACKEND=qdrant`** - Force Qdrant usage
   - High-performance vector database
   - Uses LangChain agents with vectorstore
   - Requires Qdrant configuration

2. **`RAG_BACKEND=supabase`** - Force Supabase usage
   - PostgreSQL with vector extensions
   - Uses Supabase agents with RAG tools
   - Requires Supabase configuration

3. **`RAG_BACKEND=auto`** (default) - Automatic selection
   - Uses Qdrant if available and configured
   - Falls back to Supabase if Qdrant is not available
   - Provides maximum flexibility

#### Backend Comparison

| Feature | Qdrant Backend | Supabase Backend |
|---------|----------------|------------------|
| **Performance** | High-performance vector DB | PostgreSQL with extensions |
| **Agents** | LangChain agents | Supabase agents |
| **Retrieval** | Vectorstore-based | RAG tools-based |
| **Use Case** | Production deployments | Development/testing |
| **Configuration** | QDRANT_URL, QDRANT_API_KEY | SUPABASE_URL, SUPABASE_KEY |

## 🐛 Troubleshooting

### Common Issues

#### Import Errors
If you encounter import errors in notebooks:
```bash
# Use the import fix
cd app/api
python import_fix.py
```

#### Environment Variables
Verify all required environment variables are set:
```bash
echo $OPENAI_API_KEY
echo $SUPABASE_URL
echo $SUPABASE_KEY
```

#### Database Connection
Test Supabase connection:
```bash
cd supabase
python test_supabase_connection.py
```

#### Workflow Initialization
Test workflow initialization:
```bash
cd app/api
python test_import_fix.py
```

### Logs and Debugging

The API provides comprehensive logging:
- Application logs: Console output
- Error logs: Detailed error messages with stack traces
- Performance logs: Processing times and metrics

### Performance Monitoring

Monitor API performance:
- Response times in API responses
- Processing time breakdowns
- Agent selection metrics
- Retrieval method statistics

## 📚 Documentation

### API Documentation
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI Spec**: `app/api/openapi.yaml`

### Code Documentation
- **Workflow**: `app/api/workflow.py`
- **Models**: `app/api/models.py`
- **Main API**: `app/api/main.py`

### Testing Documentation
- **Notebook Tests**: `app/api/TestAgentWorkflow.ipynb`
- **Postman Collection**: `app/api/Cuttlefish4_API.postman_collection.json`
- **Import Fix**: `app/api/import_fix.py`

## 🚀 Deployment

### Development
```bash
cd app/api
python main.py
```

### Production
```bash
# Using Gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Using Docker (if Dockerfile available)
docker build -t cuttlefish4-api .
docker run -p 8000:8000 cuttlefish4-api
```

### Environment-Specific Configuration

#### Development
- Uses Supabase fallbacks
- Detailed logging enabled
- CORS allows all origins

#### Production
- Configure Qdrant for vectorstore
- Restrict CORS origins
- Enable authentication
- Set up monitoring and alerting

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Run tests to ensure everything works
4. Submit a pull request

### Testing Checklist
- [ ] Run `TestAgentWorkflow.ipynb` notebook
- [ ] Test all Postman collection endpoints
- [ ] Verify health check endpoint
- [ ] Test error handling scenarios
- [ ] Check performance metrics

## 📄 License

**BUSL-1.1 (non-production)** — see [LICENSE](../../LICENSE).  
Commercial/production use requires a separate agreement with the author.  
On **2029-08-20**, Cuttlefish converts to **Apache-2.0**.

Contact: foohm@kawan2.com

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review the API documentation
3. Run the test notebooks
4. Check the logs for error details

---

**Happy Testing! 🎉**
