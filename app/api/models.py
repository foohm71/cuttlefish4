#!/usr/bin/env python3
"""
Pydantic models for FastAPI request and response validation.
"""

from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field

# Request Models

class MultiAgentRAGRequest(BaseModel):
    """Request model for the main multi-agent RAG endpoint."""
    
    query: str = Field(
        ..., 
        description="User query for JIRA ticket search",
        example="authentication error in login system"
    )
    user_can_wait: bool = Field(
        False,
        description="Whether user can wait for comprehensive results (enables Ensemble agent)"
    )
    production_incident: bool = Field(
        False,
        description="Whether this is a production incident requiring urgent response"
    )
    openai_api_key: Optional[str] = Field(
        None,
        description="Optional OpenAI API key for this request"
    )

class DebugRoutingRequest(BaseModel):
    """Request model for the debug routing endpoint."""
    
    query: str = Field(
        ..., 
        description="Query to test routing decision",
        example="HBASE-123 connection timeout"
    )
    user_can_wait: bool = Field(
        False,
        description="Whether user can wait for comprehensive results"
    )
    production_incident: bool = Field(
        False,
        description="Whether this is a production incident"
    )

# Response Models

class RetrievalMetadata(BaseModel):
    """Metadata about the retrieval process."""
    
    agent: str = Field(description="Agent that performed retrieval")
    num_results: int = Field(description="Number of results retrieved")
    processing_time: float = Field(description="Processing time in seconds")
    method_type: str = Field(description="Type of retrieval method used")
    
    # Optional fields for different agent types
    bm25_available: Optional[bool] = Field(None, description="Whether BM25 was available")
    is_urgent: Optional[bool] = Field(None, description="Whether urgent processing was used")
    methods_used: Optional[List[str]] = Field(None, description="Methods used in ensemble")
    primary_source: Optional[str] = Field(None, description="Primary source of results")
    source: Optional[str] = Field(None, description="Source type")
    content_filtered: Optional[bool] = Field(None, description="Whether content was filtered")

class RetrievedContext(BaseModel):
    """A retrieved document context."""
    
    content: str = Field(description="Document content")
    metadata: Dict[str, Any] = Field(description="Document metadata")
    source: str = Field(description="Source of the document")
    score: float = Field(description="Relevance score")

class RelevantTicket(BaseModel):
    """Information about a relevant JIRA ticket."""
    
    key: str = Field(description="JIRA ticket key (e.g., HBASE-123)")
    title: str = Field(description="Ticket title")

class MessageInfo(BaseModel):
    """Information about agent messages."""
    
    content: str = Field(description="Message content")
    type: str = Field(description="Message type")

class MultiAgentRAGResponse(BaseModel):
    """Response model for the main multi-agent RAG endpoint."""
    
    # Core response data
    query: str = Field(description="Original query")
    final_answer: str = Field(description="Generated response")
    relevant_tickets: List[RelevantTicket] = Field(description="Relevant JIRA tickets found")
    
    # Agent routing information
    routing_decision: str = Field(description="Which agent was selected")
    routing_reasoning: str = Field(description="Reasoning for agent selection")
    
    # Retrieval information
    retrieval_method: str = Field(description="Retrieval method used")
    retrieved_contexts: List[RetrievedContext] = Field(description="Retrieved document contexts")
    retrieval_metadata: RetrievalMetadata = Field(description="Retrieval process metadata")
    
    # Request parameters
    user_can_wait: bool = Field(description="Whether user could wait")
    production_incident: bool = Field(description="Whether this was production incident")
    
    # Processing information
    messages: List[Dict[str, Any]] = Field(description="Processing messages from agents")
    timestamp: str = Field(description="Response timestamp")
    
    # Performance metrics
    total_processing_time: Optional[float] = Field(None, description="Total processing time in seconds")

class DebugRoutingResponse(BaseModel):
    """Response model for the debug routing endpoint."""
    
    query: str = Field(description="Original query")
    user_can_wait: bool = Field(description="User can wait parameter")
    production_incident: bool = Field(description="Production incident parameter")
    routing_decision: str = Field(description="Selected agent")
    routing_reasoning: str = Field(description="Reasoning for agent selection")
    timestamp: str = Field(description="Response timestamp")

class HealthResponse(BaseModel):
    """Response model for the health check endpoint."""
    
    status: str = Field(description="Service status", example="healthy")
    service: str = Field(description="Service name")
    version: str = Field(description="Service version")
    timestamp: str = Field(description="Health check timestamp")
    agents: Dict[str, str] = Field(description="Agent configuration")

class ErrorResponse(BaseModel):
    """Response model for error cases."""
    
    error: str = Field(description="Error message")
    timestamp: str = Field(description="Error timestamp")
    query: Optional[str] = Field(None, description="Query that caused the error")
    path: Optional[str] = Field(None, description="API path that caused the error")