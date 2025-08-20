# ContextTestAgentWorkflow.md

## Overview
This document captures the context, learnings, and solutions discovered while creating and debugging the TestAgentWorkflow.ipynb notebook for comprehensive testing of the MultiAgentWorkflow system.

## Background
TestAgentWorkflow.ipynb is a comprehensive test notebook designed to validate the complete multi-agent workflow system before API integration. It tests initialization, routing, retrieval methods, end-to-end processing, and error handling.

## Issues Encountered and Solutions

### 1. Import System and Path Resolution Issues (Major Issue)

**Problem**: Relative import failures when trying to import MultiAgentWorkflow and related components.

**Error Messages**:
- `❌ MultiAgentWorkflow import failed: attempted relative import with no known parent package`
- `❌ Alternative import also failed: attempted relative import beyond top-level package`

**Root Causes**:
1. **Notebook Environment**: Jupyter notebooks don't handle relative imports the same way as Python modules
2. **Package Structure**: The workflow.py uses relative imports (`from ..agents import ...`) which fail in notebook context
3. **Missing CUTTLEFISH_HOME**: The system expected a CUTTLEFISH_HOME environment variable for path resolution

**Solutions Implemented**:

#### Solution 1: CUTTLEFISH_HOME Environment Variable
```python
# Set CUTTLEFISH_HOME to project root
if 'CUTTLEFISH_HOME' not in os.environ:
    os.environ['CUTTLEFISH_HOME'] = str(project_root)
    print(f"🏠 Set CUTTLEFISH_HOME to: {project_root}")
```

#### Solution 2: Multiple Path Strategy
```python
# Add multiple paths to sys.path for robust import resolution
paths_to_add = [
    str(project_root),  # Project root for absolute imports
    str(app_dir),       # App directory for component access
    str(current_dir),   # API directory for local imports
]

for path in paths_to_add:
    if path not in sys.path:
        sys.path.insert(0, path)
```

#### Solution 3: Workflow.py Import Fallback Pattern
The workflow.py was updated to handle both relative and absolute imports:
```python
try:
    # Try relative imports first (for when imported as part of package)
    from ..agents import (
        AgentState, SupervisorAgent, BM25Agent, ContextualCompressionAgent,
        EnsembleAgent, ResponseWriterAgent, measure_performance
    )
    from ..tools import get_rag_tools
except ImportError:
    # Fall back to absolute imports (for direct import)
    from agents import (
        AgentState, SupervisorAgent, BM25Agent, ContextualCompressionAgent,
        EnsembleAgent, ResponseWriterAgent, measure_performance
    )
    from tools import get_rag_tools
```

#### Solution 4: Import Utility Module
Created `import_fix.py` with helper functions:
```python
def setup_imports():
    """Setup proper import paths for the workflow testing."""
    current_dir = Path(__file__).parent
    app_dir = current_dir.parent
    project_root = app_dir.parent
    
    paths_to_add = [str(project_root), str(app_dir), str(current_dir)]
    for path in paths_to_add:
        if path not in sys.path:
            sys.path.insert(0, path)
    
    return current_dir, app_dir, project_root
```

### 2. Notebook Cell Ordering Issues

**Problem**: Initial notebook creation resulted in test cells in reverse order (Test 5, 4, 3, 2, 1).

**Root Cause**: Using `NotebookEdit` with `insert` mode appends cells at the end, creating reverse chronological order when building iteratively.

**Solution**: Recreated the entire notebook structure as a single JSON file with proper cell ordering from Test 1 → Test 5.

**Lesson Learned**: When creating complex notebooks programmatically, it's better to:
1. Design the complete structure first
2. Create as a single JSON file rather than iterative cell insertion
3. Always do visual verification of cell order

### 3. Async Function Testing in Jupyter

**Problem**: The workflow uses async functions, but Jupyter notebook testing requires special handling.

**Solution**: Implemented comprehensive async handling:
```python
# Handle different event loop scenarios
try:
    loop = asyncio.get_event_loop()
    if loop.is_running():
        import nest_asyncio
        nest_asyncio.apply()
        result = await workflow.process_query(...)
    else:
        result = loop.run_until_complete(workflow.process_query(...))
except RuntimeError:
    # No existing loop, create new one
    result = asyncio.run(workflow.process_query(...))
```

**Key Insight**: Jupyter environments may have running event loops, requiring `nest_asyncio` for nested async execution.

### 4. Package Dependency Management

**Problem**: The workflow system has numerous dependencies that may not be installed in test environments.

**Solution**: Created comprehensive package installation cell:
```python
required_packages = [
    "openai>=1.0.0",
    "langchain-openai", 
    "langchain-core",
    "langchain-qdrant",
    "supabase>=2.0.0",
    "python-dotenv",
    "pydantic>=2.0.0",
    "qdrant-client",
    "nest-asyncio",  # Critical for async support
    "numpy",
    "pandas",
]
```

**Lesson Learned**: Always include `nest-asyncio` for Jupyter notebooks that test async functionality.

## Technical Architecture Understanding

### MultiAgentWorkflow Structure
```
MultiAgentWorkflow
├── LLM Components
│   ├── supervisor_llm (gpt-4o)
│   ├── rag_llm (gpt-4o-mini) 
│   └── response_writer_llm (gpt-4o)
├── Storage Systems
│   ├── vectorstore (Qdrant - optional)
│   └── rag_tools (Supabase fallback)
├── Agent Components
│   ├── supervisor_agent (always initialized)
│   ├── response_writer_agent (always initialized)
│   ├── bm25_agent (optional - Qdrant dependent)
│   ├── contextual_compression_agent (optional)
│   └── ensemble_agent (optional)
└── Fallback Methods
    ├── _supabase_bm25_fallback
    ├── _supabase_vector_fallback
    └── _supabase_hybrid_fallback
```

### Routing Logic
1. **Production Incidents** → ContextualCompression (urgent response)
2. **User Can Wait** → Ensemble (comprehensive analysis)  
3. **JIRA Ticket References** → BM25 (exact matching)
4. **General Queries** → ContextualCompression (default)

### Processing Pipeline
```
Query Input → Supervisor Agent → Retrieval Agent → Response Writer → Final Answer
```

## Test Coverage Implementation

### 1. Initialization Testing
- **LLM Setup**: Validates all three LLM components
- **Vectorstore Connection**: Tests Qdrant connection (expected to fail, fallback to Supabase)
- **Agent Initialization**: Verifies supervisor and response writer (required) vs optional agents
- **RAG Tools**: Confirms Supabase integration

### 2. Routing Decision Testing
- **Scenario-Based Testing**: 4 different query types with expected routing outcomes
- **Performance Measurement**: Timing for routing decisions
- **Reasoning Validation**: Checks if routing reasoning contains expected keywords

### 3. Fallback Method Testing
- **Individual Testing**: BM25, Vector, and Hybrid methods tested separately
- **Performance Metrics**: Timing and context retrieval success rates
- **Error Handling**: Graceful degradation when methods fail

### 4. End-to-End Processing
- **Complete Pipeline**: Full supervisor → retrieval → response workflow
- **Response Validation**: Structure validation and content relevance checking
- **Performance Analysis**: Processing time, context count, answer quality

### 5. Error Handling and Edge Cases
- **Input Validation**: Empty queries, long queries, special characters, Unicode
- **Robustness Testing**: Network failures, missing dependencies
- **Graceful Degradation**: Empty results fallback testing

## Performance Benchmarks

### Expected Performance Ranges
- **Routing Decisions**: 0.5-2.0 seconds
- **Individual Retrieval**: 1-3 seconds
- **End-to-End Processing**: 5-15 seconds
- **Context Retrieval**: 3-10 relevant documents

### Quality Thresholds
- **Overall Success Rate**: ≥80% for production readiness
- **Routing Accuracy**: ≥80% correct decisions  
- **Context Retrieval**: ≥70% successful retrieval
- **Error Handling**: ≥80% graceful handling

## Best Practices Identified

### 1. Jupyter Notebook Testing
- **Path Management**: Always set CUTTLEFISH_HOME and multiple sys.path entries
- **Async Handling**: Include nest_asyncio for async function testing
- **Import Strategy**: Use try/except blocks with multiple import approaches
- **Visual Verification**: Always visually check notebook cell order

### 2. Workflow Testing
- **Component Isolation**: Test each component individually before integration
- **Fallback Validation**: Ensure fallback methods work when primary systems fail  
- **Performance Monitoring**: Track timing and resource usage metrics
- **Error Recovery**: Test graceful degradation scenarios

### 3. Environment Setup
- **Dependency Management**: Install all required packages upfront
- **Environment Variables**: Validate all required API keys and configuration
- **Path Resolution**: Use both environment variables and programmatic path setup

## Future Improvements

### 1. Test Automation
- **CI/CD Integration**: Run notebook tests as part of deployment pipeline
- **Automated Reporting**: Generate HTML reports from notebook execution
- **Performance Regression**: Track performance metrics over time

### 2. Enhanced Testing
- **Load Testing**: Test with concurrent requests and high query volumes
- **Integration Testing**: Test with real API endpoints and production data
- **Monitoring Integration**: Add telemetry and logging for production analysis

### 3. Documentation
- **API Documentation**: Generate OpenAPI specs from the workflow
- **Performance Guide**: Document optimization strategies and configuration
- **Troubleshooting Guide**: Common issues and resolution steps

## Key Files Created

### Core Files
- `/Users/foohm/github/cuttlefish4/app/api/TestAgentWorkflow.ipynb` - Main test notebook
- `/Users/foohm/github/cuttlefish4/app/api/import_fix.py` - Import resolution utilities

### Test Structure
```
TestAgentWorkflow.ipynb
├── Package Installation (dependencies)
├── Environment Setup (paths, variables)
├── Component Imports (workflow, models)
├── Test 1: Initialization
├── Test 2: Supervisor Routing  
├── Test 3: Supabase Fallbacks
├── Test 4: End-to-End Processing
├── Test 5: Error Handling
└── Final Report (comprehensive analysis)
```

## Environment Dependencies

### Required Environment Variables
```bash
OPENAI_API_KEY=your_openai_key
SUPABASE_URL=your_supabase_url  
SUPABASE_KEY=your_supabase_key
CUTTLEFISH_HOME=/path/to/project/root  # Auto-set if missing
```

### Optional Environment Variables
```bash
QDRANT_URL=your_qdrant_url      # For vectorstore testing
QDRANT_API_KEY=your_qdrant_key  # For vectorstore testing
COHERE_API_KEY=your_cohere_key  # For reranking features
```

## Troubleshooting Common Issues

### Import Errors
1. **Check CUTTLEFISH_HOME**: Ensure it points to project root
2. **Verify Python Path**: Confirm sys.path includes necessary directories  
3. **Restart Kernel**: Clear import cache with kernel restart
4. **Check Dependencies**: Ensure all required packages are installed

### Async Execution Errors
1. **Install nest-asyncio**: `pip install nest-asyncio`
2. **Apply nest_asyncio**: Add `nest_asyncio.apply()` before await calls
3. **Event Loop Issues**: Use try/except blocks with multiple async strategies

### Test Failures
1. **Environment Variables**: Verify all API keys are set correctly
2. **Network Connectivity**: Check Supabase and OpenAI API access
3. **Resource Limits**: Ensure sufficient API rate limits and quotas
4. **Version Compatibility**: Check package version compatibility

---

**Document Created**: August 15, 2025  
**Last Updated**: August 15, 2025  
**Status**: Complete - All import and testing issues resolved  
**Next Steps**: Run comprehensive testing and integrate with CI/CD pipeline