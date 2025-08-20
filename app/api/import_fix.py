#!/usr/bin/env python3
"""
Import fix for TestAgentWorkflow.ipynb
This script helps resolve the relative import issues in workflow.py
"""

import os
import sys
from pathlib import Path

def setup_imports():
    """Setup proper import paths for the workflow testing."""
    
    # Get the current directory (should be app/api)
    current_dir = Path(__file__).parent
    app_dir = current_dir.parent
    project_root = app_dir.parent
    
    # Add necessary paths to Python path
    paths_to_add = [
        str(project_root),  # Project root
        str(app_dir),       # App directory
        str(current_dir),   # API directory
    ]
    
    for path in paths_to_add:
        if path not in sys.path:
            sys.path.insert(0, path)
    
    return current_dir, app_dir, project_root

def import_workflow():
    """Import the MultiAgentWorkflow with proper path setup."""
    current_dir, app_dir, project_root = setup_imports()
    
    # Now we can import the workflow
    try:
        from workflow import MultiAgentWorkflow
        return MultiAgentWorkflow
    except ImportError as e:
        print(f"Import error: {e}")
        print(f"Current sys.path: {sys.path[:5]}...")  # Show first 5 paths
        raise

def import_models():
    """Import the Pydantic models."""
    setup_imports()
    
    try:
        from models import (
            MultiAgentRAGRequest, MultiAgentRAGResponse,
            DebugRoutingRequest, DebugRoutingResponse,
            RetrievalMetadata, RetrievedContext, RelevantTicket
        )
        return {
            'MultiAgentRAGRequest': MultiAgentRAGRequest,
            'MultiAgentRAGResponse': MultiAgentRAGResponse,
            'DebugRoutingRequest': DebugRoutingRequest,
            'DebugRoutingResponse': DebugRoutingResponse,
            'RetrievalMetadata': RetrievalMetadata,
            'RetrievedContext': RetrievedContext,
            'RelevantTicket': RelevantTicket
        }
    except ImportError as e:
        print(f"Models import error: {e}")
        raise

if __name__ == "__main__":
    # Test the imports
    print("Testing imports...")
    try:
        MultiAgentWorkflow = import_workflow()
        print("✅ MultiAgentWorkflow imported successfully")
        
        models = import_models()
        print("✅ Models imported successfully")
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()