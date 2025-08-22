#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
FastAPI main application for Cuttlefish multi-agent RAG system.
Converted from Flask implementation with same endpoints and functionality.
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
import traceback

# Authentication bypass flag
BYPASS_AUTH = os.environ.get('BYPASS_AUTH', 'false').lower() == 'true'


from fastapi import FastAPI, HTTPException, Request, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import uvicorn

try:
    # Try relative imports first (for when imported as part of package)
    from ..agents import (
        AgentState, SupervisorAgent, BM25Agent, ContextualCompressionAgent,
        EnsembleAgent, ResponseWriterAgent
    )
    from ..tools import get_rag_tools
except ImportError:
    # Fall back to absolute imports (for direct import)
    from agents import (
        AgentState, SupervisorAgent, BM25Agent, ContextualCompressionAgent,
        EnsembleAgent, ResponseWriterAgent
    )
    from tools import get_rag_tools
try:
    # Try relative imports first (for when imported as part of package)
    from .models import (
        MultiAgentRAGRequest, MultiAgentRAGResponse, DebugRoutingRequest,
        DebugRoutingResponse, HealthResponse, ErrorResponse
    )
    from .workflow import MultiAgentWorkflow
    from ..auth.routes import router as auth_router
    from ..auth.middleware import get_current_active_user, log_api_request
    from ..database.models import User, get_db, db_manager
except ImportError:
    # Fall back to absolute imports (for direct import)
    from app.api.models import (
        MultiAgentRAGRequest, MultiAgentRAGResponse, DebugRoutingRequest,
        DebugRoutingResponse, HealthResponse, ErrorResponse
    )
    from app.api.workflow import MultiAgentWorkflow
    from app.auth.routes import router as auth_router
    from app.auth.middleware import get_current_active_user, log_api_request
    from app.database.models import User, get_db, db_manager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Cuttlefish Multi-Agent RAG API",
    description="Intelligent JIRA ticket retrieval using multi-agent RAG system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Include authentication routes
app.include_router(auth_router)

# CORS configuration (same as Flask version)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - restrict in production
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Global workflow instance (initialized lazily)
workflow_instance: Optional[MultiAgentWorkflow] = None

def get_workflow() -> MultiAgentWorkflow:
    """Get or create the multi-agent workflow instance."""
    global workflow_instance
    
    if workflow_instance is None:
        try:
            workflow_instance = MultiAgentWorkflow()
            logger.info("✅ Multi-agent workflow initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize workflow: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initialize workflow: {str(e)}"
            )
    
    return workflow_instance

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    error_msg = f"Internal server error: {str(exc)}"
    logger.error(f"Unhandled exception for {request.url}: {error_msg}")
    logger.error(traceback.format_exc())
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": error_msg,
            "timestamp": datetime.now().isoformat(),
            "path": str(request.url)
        }
    )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    Returns service status and configuration information.
    """
    return HealthResponse(
        status="healthy",
        service="Cuttlefish3 Multi-Agent RAG",
        version="1.0.0",
        timestamp=datetime.now().isoformat(),
        agents={
            "supervisor": "GPT-4o",
            "response_writer": "GPT-4o"
        }
    )


def create_multiagent_rag_endpoint():
    """Create the multiagent-rag endpoint with conditional authentication."""
    if BYPASS_AUTH:
        # No authentication required
        @app.post("/multiagent-rag", response_model=MultiAgentRAGResponse)
        async def multiagent_rag_endpoint_no_auth(
            request: MultiAgentRAGRequest,
            http_request: Request
        ):
            return await _process_multiagent_rag(request, http_request, None, None)
    else:
        # Authentication required
        @app.post("/multiagent-rag", response_model=MultiAgentRAGResponse)
        async def multiagent_rag_endpoint_with_auth(
            request: MultiAgentRAGRequest,
            current_user: User = Depends(get_current_active_user),
            db: Session = Depends(get_db),
            http_request: Request = None
        ):
            return await _process_multiagent_rag(request, http_request, current_user, db)

async def _process_multiagent_rag(
    request: MultiAgentRAGRequest,
    http_request: Request,
    current_user: Optional[User],
    db: Optional[Session]
):
    """
    Main multi-agent RAG processing logic.
    
    Args:
        request: Query and configuration parameters
        http_request: FastAPI request object
        current_user: Authenticated user (None if auth bypassed)
        db: Database session (None if auth bypassed)
    
    Returns:
        Comprehensive results from multi-agent processing
    """
    start_time = datetime.now()
    
    try:
        user_email = current_user.email if current_user else "anonymous"
        logger.info(f"Multi-agent RAG request from {user_email}: '{request.query[:50]}...'")
        
        # Get workflow instance
        workflow = get_workflow()
        
        # Process query through multi-agent workflow
        result = await workflow.process_query(
            query=request.query,
            user_can_wait=request.user_can_wait,
            production_incident=request.production_incident,
            openai_api_key=request.openai_api_key
        )
        
        # Log successful request (only if auth is enabled)
        processing_time = (datetime.now() - start_time).total_seconds()
        if not BYPASS_AUTH and current_user and db:
            await log_api_request(
                request=http_request,
                user=current_user,
                endpoint="/multiagent-rag",
                success=True,
                processing_time=processing_time,
                query_text=request.query,
                user_can_wait=request.user_can_wait,
                production_incident=request.production_incident,
                db=db
            )
        
        logger.info(f"Multi-agent RAG completed successfully for {user_email}")
        return MultiAgentRAGResponse(**result)
        
    except ValueError as ve:
        error_msg = f"Invalid request: {str(ve)}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    except Exception as e:
        # Log failed request (only if auth is enabled)
        processing_time = (datetime.now() - start_time).total_seconds()
        if not BYPASS_AUTH and current_user and db:
            await log_api_request(
                request=http_request,
                user=current_user,
                endpoint="/multiagent-rag",
                success=False,
                error_message=str(e),
                processing_time=processing_time,
                query_text=request.query,
                user_can_wait=request.user_can_wait,
                production_incident=request.production_incident,
                db=db
            )
        
        error_msg = f"Processing error: {str(e)}"
        logger.info(f"Multi-agent RAG error for {user_email}: {error_msg}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )

# Create the endpoint with the appropriate authentication
create_multiagent_rag_endpoint()

@app.post("/debug/routing", response_model=DebugRoutingResponse)
async def debug_routing_endpoint(
    request: DebugRoutingRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    http_request: Request = None
):
    """
    Debug endpoint for testing routing decisions without full processing.
    
    Useful for understanding how the supervisor agent routes different queries
    to specialized retrieval agents.
    
    Args:
        request: Query and configuration parameters
    
    Returns:
        Routing decision and reasoning from supervisor agent
    
    Raises:
        HTTPException: 400 for invalid requests, 500 for routing errors
    """
    start_time = datetime.now()
    
    try:
        logger.info(f"Debug routing request from {current_user.email}: '{request.query[:50]}...'")
        
        # Get workflow instance  
        workflow = get_workflow()
        
        # Get routing decision only
        routing_result = await workflow.get_routing_decision(
            query=request.query,
            user_can_wait=request.user_can_wait,
            production_incident=request.production_incident
        )
        
        # Log successful request
        processing_time = (datetime.now() - start_time).total_seconds()
        await log_api_request(
            request=http_request,
            user=current_user,
            endpoint="/debug/routing",
            success=True,
            processing_time=processing_time,
            query_text=request.query,
            user_can_wait=request.user_can_wait,
            production_incident=request.production_incident,
            db=db
        )
        
        logger.info(f"Debug routing completed for {current_user.email}: {routing_result['routing_decision']}")
        
        return DebugRoutingResponse(
            query=request.query,
            user_can_wait=request.user_can_wait,
            production_incident=request.production_incident,
            routing_decision=routing_result['routing_decision'],
            routing_reasoning=routing_result['routing_reasoning'],
            timestamp=datetime.now().isoformat()
        )
        
    except ValueError as ve:
        error_msg = f"Invalid routing request: {str(ve)}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    except Exception as e:
        # Log failed request
        processing_time = (datetime.now() - start_time).total_seconds()
        await log_api_request(
            request=http_request,
            user=current_user,
            endpoint="/debug/routing",
            success=False,
            error_message=str(e),
            processing_time=processing_time,
            query_text=request.query,
            user_can_wait=request.user_can_wait,
            production_incident=request.production_incident,
            db=db
        )
        
        error_msg = f"Routing error: {str(e)}"
        logger.error(f"Debug routing error for {current_user.email}: {error_msg}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )

@app.get("/", response_class=HTMLResponse)
async def test_interface():
    """
    Interactive testing interface for the API.
    Returns HTML page for testing endpoints.
    """
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Cuttlefish Multi-Agent RAG API Test</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                max-width: 1200px; 
                margin: 0 auto; 
                padding: 20px; 
                background-color: #f5f5f5;
            }
            .container { 
                background: white; 
                padding: 30px; 
                border-radius: 10px; 
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 { 
                color: #333; 
                text-align: center;
                margin-bottom: 30px;
            }
            .form-group { 
                margin-bottom: 20px; 
            }
            label { 
                display: block; 
                margin-bottom: 5px; 
                font-weight: bold;
                color: #555;
            }
            input, textarea, select { 
                width: 100%; 
                padding: 10px; 
                border: 2px solid #ddd; 
                border-radius: 5px;
                font-size: 14px;
            }
            textarea { 
                resize: vertical; 
                min-height: 60px;
            }
            button { 
                background-color: #007bff; 
                color: white; 
                padding: 12px 24px; 
                border: none; 
                border-radius: 5px; 
                cursor: pointer;
                font-size: 16px;
                margin-right: 10px;
            }
            button:hover { 
                background-color: #0056b3; 
            }
            .debug-btn { 
                background-color: #28a745; 
            }
            .debug-btn:hover { 
                background-color: #1e7e34; 
            }
            .health-btn {
                background-color: #17a2b8;
            }
            .health-btn:hover {
                background-color: #117a8b;
            }
            #response { 
                margin-top: 20px; 
                padding: 15px; 
                border: 2px solid #ddd; 
                border-radius: 5px; 
                background-color: #f8f9fa;
                white-space: pre-wrap;
                font-family: monospace;
                max-height: 600px;
                overflow-y: auto;
            }
            .checkbox-group {
                display: flex;
                gap: 20px;
                align-items: center;
            }
            .checkbox-item {
                display: flex;
                align-items: center;
                gap: 5px;
            }
            .checkbox-item input {
                width: auto;
            }
            .status-indicator {
                display: inline-block;
                width: 12px;
                height: 12px;
                border-radius: 50%;
                margin-right: 8px;
            }
            .status-healthy {
                background-color: #28a745;
            }
            .status-error {
                background-color: #dc3545;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🐙 Cuttlefish Multi-Agent RAG API</h1>
            
            <div class="form-group">
                <label for="query">Query:</label>
                <textarea id="query" placeholder="Enter your JIRA ticket search query...">authentication error in login system</textarea>
            </div>
            
            <div class="form-group">
                <div class="checkbox-group">
                    <div class="checkbox-item">
                        <input type="checkbox" id="user_can_wait">
                        <label for="user_can_wait">User can wait (comprehensive search)</label>
                    </div>
                    <div class="checkbox-item">
                        <input type="checkbox" id="production_incident">
                        <label for="production_incident">Production incident (urgent)</label>
                    </div>
                </div>
            </div>
            
            <div class="form-group">
                <label for="openai_api_key">OpenAI API Key (optional):</label>
                <input type="password" id="openai_api_key" placeholder="sk-...">
            </div>
            
            <div style="margin-bottom: 20px;">
                <button onclick="callMultiAgentRAG()">🔍 Multi-Agent Search</button>
                <button onclick="callDebugRouting()" class="debug-btn">🧠 Debug Routing</button>
                <button onclick="callHealthCheck()" class="health-btn">❤️ Health Check</button>
            </div>
            
            <div id="response"></div>
        </div>

        <script>
            async function callMultiAgentRAG() {
                const responseDiv = document.getElementById('response');
                responseDiv.innerHTML = '⏳ Processing multi-agent query...';
                
                try {
                    const response = await fetch('/multiagent-rag', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            query: document.getElementById('query').value,
                            user_can_wait: document.getElementById('user_can_wait').checked,
                            production_incident: document.getElementById('production_incident').checked,
                            openai_api_key: document.getElementById('openai_api_key').value || null
                        })
                    });
                    
                    const data = await response.json();
                    responseDiv.innerHTML = `<span class="status-indicator ${response.ok ? 'status-healthy' : 'status-error'}"></span>` +
                                          `Status: ${response.status}\\n\\n` +
                                          JSON.stringify(data, null, 2);
                } catch (error) {
                    responseDiv.innerHTML = `<span class="status-indicator status-error"></span>Error: ${error.message}`;
                }
            }
            
            async function callDebugRouting() {
                const responseDiv = document.getElementById('response');
                responseDiv.innerHTML = '⏳ Analyzing routing decision...';
                
                try {
                    const response = await fetch('/debug/routing', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            query: document.getElementById('query').value,
                            user_can_wait: document.getElementById('user_can_wait').checked,
                            production_incident: document.getElementById('production_incident').checked
                        })
                    });
                    
                    const data = await response.json();
                    responseDiv.innerHTML = `<span class="status-indicator ${response.ok ? 'status-healthy' : 'status-error'}"></span>` +
                                          `Status: ${response.status}\\n\\n` +
                                          JSON.stringify(data, null, 2);
                } catch (error) {
                    responseDiv.innerHTML = `<span class="status-indicator status-error"></span>Error: ${error.message}`;
                }
            }
            
            async function callHealthCheck() {
                const responseDiv = document.getElementById('response');
                responseDiv.innerHTML = '⏳ Checking service health...';
                
                try {
                    const response = await fetch('/health');
                    const data = await response.json();
                    responseDiv.innerHTML = `<span class="status-indicator ${response.ok ? 'status-healthy' : 'status-error'}"></span>` +
                                          `Status: ${response.status}\\n\\n` +
                                          JSON.stringify(data, null, 2);
                } catch (error) {
                    responseDiv.innerHTML = `<span class="status-indicator status-error"></span>Error: ${error.message}`;
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("🚀 Starting Cuttlefish Multi-Agent RAG API...")
    try:
        # Test database connection (don't create tables on startup)
        logger.info("Initializing database connection...")
        if BYPASS_AUTH:
            logger.info("⚠️  BYPASS_AUTH=true - Running without database authentication")
            logger.info("✅ Database authentication bypassed")
        else:
            logger.info("Testing database connection...")
            # Just test connection, don't create tables (tables should be created by scripts)
            db_manager.test_connection()
            logger.info("✅ Database connection verified")
        
        # Initialize workflow (lazy loading)
        logger.info("API startup complete - workflow will be initialized on first request")
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")
        raise

# Shutdown event

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("🛑 Shutting down Cuttlefish Multi-Agent RAG API...")


if __name__ == "__main__":
    # Development server
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")  # Bind to all interfaces for production
    
    logger.info(f"Starting development server on {host}:{port}")
    
    uvicorn.run(
        "app.api.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )