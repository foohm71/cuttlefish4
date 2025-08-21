#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
Simplified FastAPI app for testing authentication system.
This version excludes the LangChain agents to avoid dependency conflicts.
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Request, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
import uvicorn

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

try:
    from ..auth.routes import router as auth_router
    from ..auth.middleware import get_current_active_user, log_api_request
    from ..database.models import User, get_db
    from ..database.init_db import initialize_database, check_database_exists
except ImportError:
    from app.auth.routes import router as auth_router
    from app.auth.middleware import get_current_active_user, log_api_request
    from app.database.models import User, get_db
    from app.database.init_db import initialize_database, check_database_exists

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Cuttlefish Auth Test API",
    description="Authentication testing for Cuttlefish4",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Include authentication routes
app.include_router(auth_router)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Test models
class TestRequest(BaseModel):
    message: str

class TestResponse(BaseModel):
    message: str
    user_email: str
    timestamp: str

# Multi-agent RAG models (simplified for testing)
class MultiAgentRAGRequest(BaseModel):
    query: str
    user_can_wait: bool = True
    production_incident: bool = False
    openai_api_key: Optional[str] = None

class MultiAgentRAGResponse(BaseModel):
    query: str
    final_answer: str
    relevant_tickets: List[Dict[str, str]] = []
    routing_decision: str
    routing_reasoning: str
    retrieval_method: str
    retrieved_contexts: List[Dict[str, Any]] = []
    retrieval_metadata: Dict[str, Any]
    user_can_wait: bool
    production_incident: bool
    messages: List[Dict[str, str]] = []
    timestamp: str
    total_processing_time: float = 0.0

@app.get("/health")
async def health_check():
    """Health check endpoint (no auth required)."""
    return {
        "status": "healthy",
        "service": "Cuttlefish Auth Test",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/test-auth", response_model=TestResponse)
async def test_auth_endpoint(
    request: TestRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    http_request: Request = None
):
    """
    Test endpoint to verify authentication is working.
    Requires valid JWT token.
    """
    start_time = datetime.now()
    
    try:
        logger.info(f"Test auth request from {current_user.email}: {request.message}")
        
        # Log the request
        await log_api_request(
            request=http_request,
            user=current_user,
            endpoint="/test-auth",
            success=True,
            processing_time=(datetime.now() - start_time).total_seconds(),
            query_text=request.message,
            db=db
        )
        
        return TestResponse(
            message=f"Hello {current_user.display_name or current_user.email}! Auth working. Your message: {request.message}",
            user_email=current_user.email,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        # Log failed request
        await log_api_request(
            request=http_request,
            user=current_user,
            endpoint="/test-auth",
            success=False,
            error_message=str(e),
            processing_time=(datetime.now() - start_time).total_seconds(),
            query_text=request.message,
            db=db
        )
        
        logger.error(f"Test auth error for {current_user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/multiagent-rag", response_model=MultiAgentRAGResponse)
async def multiagent_rag_endpoint(
    request: MultiAgentRAGRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    http_request: Request = None
):
    """
    Mock multi-agent RAG endpoint for testing authentication.
    Returns formatted response while we work on integrating real workflow.
    """
    start_time = datetime.now()
    
    try:
        logger.info(f"Multi-agent RAG request from {current_user.email}: '{request.query[:50]}...'")
        
        # Mock multi-agent response
        mock_response = {
            "query": request.query,
            "final_answer": f"🔍 Mock Analysis: Your query '{request.query}' would be processed by our multi-agent system. This is a test response showing that authentication and API integration are working correctly. The real workflow will analyze JIRA tickets and provide detailed technical solutions.",
            "relevant_tickets": [
                {"key": "TEST-123", "title": "Sample ticket for testing purposes"},
                {"key": "AUTH-456", "title": "Authentication system integration"}
            ],
            "routing_decision": "MockAgent",
            "routing_reasoning": "This is a test query during system integration",
            "retrieval_method": "Mock",
            "retrieved_contexts": [],
            "retrieval_metadata": {
                "agent": "MockAgent",
                "num_results": 2,
                "processing_time": 0.1,
                "method_type": "mock"
            },
            "user_can_wait": request.user_can_wait,
            "production_incident": request.production_incident,
            "messages": [],
            "timestamp": datetime.now().isoformat(),
            "total_processing_time": 0.1
        }
        
        # Log the request
        processing_time = (datetime.now() - start_time).total_seconds()
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
        
        logger.info(f"Mock multi-agent RAG completed for {current_user.email}")
        return MultiAgentRAGResponse(**mock_response)
        
    except Exception as e:
        # Log failed request
        processing_time = (datetime.now() - start_time).total_seconds()
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
        
        logger.error(f"Mock multi-agent RAG error for {current_user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/")
async def root():
    """Root endpoint with simple HTML interface."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Cuttlefish Auth Test</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 600px; margin: 0 auto; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔐 Cuttlefish Auth Test API</h1>
            <p>Authentication system is running!</p>
            <ul>
                <li><a href="/docs">API Documentation</a></li>
                <li><a href="/health">Health Check</a></li>
                <li><a href="http://localhost:3000">Frontend (if running)</a></li>
            </ul>
            <h3>Available Endpoints:</h3>
            <ul>
                <li><code>POST /auth/google</code> - Google OAuth login</li>
                <li><code>GET /auth/me</code> - Get current user (requires auth)</li>
                <li><code>GET /auth/usage</code> - Get usage stats (requires auth)</li>
                <li><code>POST /test-auth</code> - Test authentication (requires auth)</li>
            </ul>
        </div>
    </body>
    </html>
    """
    return JSONResponse(content={"message": "Cuttlefish Auth Test API"})

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("🚀 Starting Cuttlefish Auth Test API...")
    try:
        # Initialize database
        if not check_database_exists():
            logger.info("Initializing database...")
            if not initialize_database():
                raise Exception("Failed to initialize database")
        else:
            logger.info("✅ Database ready")
        
        logger.info("✅ Auth test API startup complete")
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")
        raise

if __name__ == "__main__":
    # Development server
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "127.0.0.1")
    
    logger.info(f"Starting auth test server on {host}:{port}")
    
    uvicorn.run(
        "app.api.main_auth_test:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )