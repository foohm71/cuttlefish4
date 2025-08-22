# PROMPTS.md

This file records all prompts used to generate code and documentation in the Cuttlefish4 project.

## Session: API Documentation and Testing Setup

### Prompt 1: Import Issue Investigation
**User Query:** "Take a look at cell tagged 'import_components' in the notebook 'TestAgentWorkflow.ipynb' in 'app/api' folder. The file 'workflow.py' is in the same folder as the notebook but it isn't able to find it to import MultiAgentWorkflow"

**Context:** The user was experiencing import errors in a Jupyter notebook when trying to import the MultiAgentWorkflow class from workflow.py.

**Solution:** 
- Identified that workflow.py was using relative imports (`from ..agents import`, `from ..tools import`) which don't work when imported directly
- Fixed the imports in workflow.py to handle both relative and absolute imports using try/except blocks
- Created import_fix.py helper script to properly set up Python paths
- Updated the notebook to use the import fix

### Prompt 2: Supabase Test Script Issue
**User Query:** "in the folder 'supabase' the supabase_client.py is querying correctly but it looks like the 'test_search.py' script is not returning any results. Can you check to see what is missing or incorrect in the 'test_search.py' script?"

**Context:** The test_search.py script was not working correctly while supabase_client.py was functioning properly.

**Solution:**
- Identified incorrect field access in test_search.py (trying to access `result.get('metadata', {}).get('title')` instead of `result.get('title')`)
- Fixed wrong score field access (looking for generic `score` instead of `similarity` for vector search and `combined_score` for hybrid search)
- Fixed import path issues
- Updated the script to correctly access result fields returned by supabase_client.py

### Prompt 3: A2A Protocol Discussion
**User Query:** "Are you familiar with the A2A protocol?" followed by "Agent-to-Agent"

**Context:** User was asking about Agent-to-Agent communication protocols.

**Response:** Provided information about A2A protocols including message passing, task delegation, state synchronization, error handling, and resource sharing patterns.

### Prompt 4: Comprehensive API Documentation and Testing Setup
**User Query:** "Ok now create a Postman collection and OpenAPI spec in the 'api' folder and a README.md on how to start the server, perform tests ie. all the TestXXX.ipynb and the postman tests"

**Context:** User wanted comprehensive API documentation and testing setup for the Cuttlefish4 project.

**Deliverables Created:**

1. **OpenAPI Specification** (`app/api/openapi.yaml`)
   - Complete API documentation with all endpoints
   - Request/response schemas
   - Examples for different query types
   - Comprehensive descriptions and usage instructions

2. **Postman Collection** (`app/api/Cuttlefish4_API.postman_collection.json`)
   - Complete collection with all API endpoints
   - Pre-configured test scenarios
   - Environment variables setup
   - Automated test scripts for response validation
   - Examples for different query types (production incidents, comprehensive analysis, specific tickets, general queries)

3. **Comprehensive README.md** (`app/api/README.md`)
   - Quick start guide
   - Environment setup instructions
   - Multiple server startup methods
   - Detailed testing instructions for:
     - Notebook testing (TestAgentWorkflow.ipynb)
     - Postman testing with collection
     - Interactive web interface
     - Command line testing
   - API endpoint documentation
   - Multi-agent system explanation
   - Configuration options
   - Troubleshooting guide
   - Deployment instructions

4. **API Test Script** (`app/api/test_api.py`)
   - Automated test suite for all API endpoints
   - Health check testing
   - Debug routing testing
   - Multi-agent RAG testing
   - Interactive interface testing
   - API documentation testing
   - Comprehensive test results summary

## Key Technical Solutions Implemented

### Import System Fix
- **Problem:** Relative imports in workflow.py causing import errors in notebooks
- **Solution:** Implemented try/except blocks to handle both relative and absolute imports
- **Files Modified:** `app/api/workflow.py`, `app/api/import_fix.py`

### Test Script Fix
- **Problem:** Incorrect field access in test_search.py
- **Solution:** Updated field access to match actual response structure from supabase_client.py
- **Files Modified:** `app/api/test_search.py`

### API Documentation
- **Problem:** Need comprehensive API documentation and testing setup
- **Solution:** Created complete OpenAPI spec, Postman collection, README, and test scripts
- **Files Created:** 
  - `app/api/openapi.yaml`
  - `app/api/Cuttlefish4_API.postman_collection.json`
  - `app/api/README.md`
  - `app/api/test_api.py`

## Testing Strategy Implemented

1. **Notebook Testing:** Comprehensive workflow testing in TestAgentWorkflow.ipynb
2. **Postman Testing:** API endpoint testing with pre-configured scenarios
3. **Automated Testing:** Python test script for quick validation
4. **Interactive Testing:** Web interface for manual testing
5. **Documentation Testing:** Swagger UI and ReDoc for API exploration

## Environment Setup Requirements

- Python 3.8+
- Virtual environment
- Required environment variables (OPENAI_API_KEY, SUPABASE_URL, SUPABASE_KEY)
- Optional Qdrant configuration for vectorstore
- Jupyter for notebook testing
- Postman for API testing

## Next Steps for Users

1. Set up environment variables
2. Start the server using provided methods
3. Run the test script to verify API functionality
4. Import Postman collection for detailed testing
5. Run notebook tests for comprehensive workflow validation
6. Use interactive web interface for manual testing

### Prompt 5: Backend Switching Implementation
**User Query:** "Can we keep the code for the QDrant vector store intact and use an env var to switch between the 2? Where would the code change happen at?"

**Context:** User wanted to maintain both Qdrant and Supabase backends while using an environment variable to switch between them.

**Solution Implemented:**

1. **Environment Variable Control**: Added `RAG_BACKEND` environment variable with options:
   - `qdrant` - Force Qdrant usage
   - `supabase` - Force Supabase usage  
   - `auto` - Automatic selection (default)

2. **Code Changes Location**: Modified `app/api/workflow.py` in the `_initialize_agents()` method

3. **New Files Created**:
   - `app/agents/supabase_agents.py` - Supabase-based agent implementations
   - `app/api/test_backend_switching.py` - Test script for backend switching

4. **Backend Integration**:
   - **Qdrant Backend**: Uses existing LangChain agents with vectorstore
   - **Supabase Backend**: Uses new Supabase agents with RAG tools
   - **Automatic Fallback**: Gracefully falls back when preferred backend unavailable

5. **Documentation Updates**:
   - Updated `app/api/README.md` with backend switching documentation
   - Added environment variable configuration examples
   - Created comparison table of backend features

**Key Benefits**:
- ✅ **Both backends preserved** - No existing code removed
- ✅ **Easy switching** - Single environment variable control
- ✅ **Automatic fallback** - System works regardless of backend availability
- ✅ **Same interface** - Agents provide consistent API regardless of backend
- ✅ **Production ready** - Can deploy with either backend based on requirements

### Prompt 6: Supabase Agents Testing Implementation
**User Query:** "Can you review TestAgents.ipynb and create a TestSupabaseAgents.ipynb so that they can be tested?"

**Context:** User wanted to test the new Supabase agents that were created for the backend switching functionality.

**Solution Implemented:**

1. **Simplified Approach**: Created `TestSupabaseAgents.py` instead of a notebook for easier execution and maintenance

2. **Comprehensive Testing**: The script tests:
   - **Environment Setup**: Supabase connection, LLM connectivity, RAG tools initialization
   - **SupabaseBM25Agent**: Keyword search functionality with normal/urgent modes
   - **SupabaseContextualCompressionAgent**: Vector similarity search
   - **SupabaseEnsembleAgent**: Multi-method retrieval combining all approaches
   - **Backend Switching**: Environment variable-based backend selection
   - **Performance Comparison**: Execution time and result count analysis

3. **Test Structure**:
   - Individual test functions for each component
   - Performance benchmarking between agents
   - Backend switching verification
   - Comprehensive error handling and reporting

4. **Documentation Updates**:
   - Updated `app/api/README.md` with testing instructions
   - Added automated testing section with script execution commands

**Key Features**:
- ✅ **Comprehensive Coverage**: Tests all Supabase agent types and functionality
- ✅ **Performance Analysis**: Compares execution times and result quality
- ✅ **Agent Integration**: Verifies agents can work together properly
- ✅ **Error Handling**: Graceful failure handling with detailed error reporting
- ✅ **Easy Execution**: Simple Python script that can be run from command line

### Prompt 7: Test Query and Similarity Threshold Improvements
**User Query:** "you can actually look at 'JIRA_OPEN_DATA_LARGESET_DATESHIFTED_ABRIDGED.csv' and 'JIRA_OPEN_DATA_LARGESET_RELEASE_TICKETS_SYNTHETIC.csv' in the data folder to understand the data that is in supabase. Let's have some queries that will show up in the search. Also is there a similarity threshold we use for similarity retrieval? If so let's use the env var SIMILARITY_THRESHOLD"

**Context:** User wanted to improve the test queries to match actual data in Supabase and add configurable similarity threshold.

**Solution Implemented:**

1. **Data Analysis**: Examined the JIRA CSV files to understand actual data content:
   - Found Spring Framework, Eclipse, memory errors, ControllerAdvice annotations
   - Identified common terms like "error", "bug", "issue", "problem", "fail"

2. **Updated Test Queries**: Replaced generic queries with data-specific ones:
   - **BM25 Agent**: "Eclipse memory error", "Spring Framework bug", "ControllerAdvice annotation"
   - **ContextualCompression Agent**: "Spring Framework error", "Eclipse OutOfMemoryError", "BeanUtils copyProperties"
   - **Ensemble Agent**: "Spring Framework issues", "Eclipse memory problems", "BeanFactory annotation"

3. **Configurable Similarity Threshold**: Added `SIMILARITY_THRESHOLD` environment variable:
   - Default value: 0.1
   - Configurable range: 0.0-1.0
   - Used in vector similarity searches

4. **Documentation Updates**:
   - Updated `app/api/README.md` with new environment variable
   - Added search configuration section

**Key Benefits**:
- ✅ **Realistic Testing**: Queries based on actual data in Supabase
- ✅ **Better Results**: More likely to return meaningful search results
- ✅ **Configurable Search**: Adjustable similarity threshold for fine-tuning
- ✅ **Data-Driven**: Test queries match the actual JIRA ticket content

