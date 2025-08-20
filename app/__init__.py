#!/usr/bin/env python3
"""
Cuttlefish Multi-Agent RAG System

A comprehensive JIRA ticket retrieval system using multi-agent RAG architecture
with support for both Qdrant (legacy) and Supabase (new) vector databases.

Main Components:
- agents/: Multi-agent system with specialized retrieval agents
- rag/: RAG retrieval functions with Supabase integration  
- tools/: Tools module mapping RAG functions to agent tools
- api/: FastAPI application with same endpoints as original Flask API

Usage:
    # Start the FastAPI server
    python -m app.api.main
    
    # Or use uvicorn
    uvicorn app.api.main:app --host 0.0.0.0 --port 8000
"""

__version__ = "1.0.0"
__author__ = "Cuttlefish Team"
__description__ = "Multi-Agent RAG System for JIRA Ticket Retrieval"