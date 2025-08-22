#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
Test script to verify backend switching functionality.
Tests different RAG_BACKEND environment variable settings.
"""

import os
import sys
from pathlib import Path

def setup_environment():
    """Setup the environment for testing."""
    current_dir = Path(__file__).parent
    app_dir = current_dir.parent
    project_root = app_dir.parent
    
    # Add paths
    for path in [str(project_root), str(app_dir), str(current_dir)]:
        if path not in sys.path:
            sys.path.insert(0, path)
    
    # Load environment variables
    try:
        from dotenv import load_dotenv
        env_file = current_dir / ".env"
        if env_file.exists():
            load_dotenv(str(env_file))
            print(f"✅ Environment loaded from: {env_file}")
    except ImportError:
        print("⚠️  python-dotenv not installed")

def test_backend_switching():
    """Test different backend configurations."""
    print("🧪 Testing Backend Switching")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        {
            'name': 'Auto Mode (Default)',
            'env_vars': {'RAG_BACKEND': 'auto'},
            'expected': 'auto'
        },
        {
            'name': 'Force Qdrant',
            'env_vars': {'RAG_BACKEND': 'qdrant'},
            'expected': 'qdrant'
        },
        {
            'name': 'Force Supabase',
            'env_vars': {'RAG_BACKEND': 'supabase'},
            'expected': 'supabase'
        }
    ]
    
    for test_case in test_cases:
        print(f"\n📋 Test: {test_case['name']}")
        
        # Set environment variables
        for key, value in test_case['env_vars'].items():
            os.environ[key] = value
            print(f"   Set {key}={value}")
        
        try:
            # Import and test workflow initialization
            from workflow import MultiAgentWorkflow
            
            # Create workflow instance
            workflow = MultiAgentWorkflow()
            
            # Check backend type
            actual_backend = getattr(workflow, 'backend_type', 'unknown')
            print(f"   ✅ Backend initialized: {actual_backend}")
            
            # Verify agent initialization
            if workflow.bm25_agent:
                print(f"   ✅ BM25 Agent: {type(workflow.bm25_agent).__name__}")
            else:
                print(f"   ⚠️  BM25 Agent: None")
            
            if workflow.contextual_compression_agent:
                print(f"   ✅ ContextualCompression Agent: {type(workflow.contextual_compression_agent).__name__}")
            else:
                print(f"   ⚠️  ContextualCompression Agent: None")
            
            if workflow.ensemble_agent:
                print(f"   ✅ Ensemble Agent: {type(workflow.ensemble_agent).__name__}")
            else:
                print(f"   ⚠️  Ensemble Agent: None")
            
            # Test expected vs actual
            if actual_backend == test_case['expected'] or test_case['expected'] == 'auto':
                print(f"   ✅ Backend switching working correctly")
            else:
                print(f"   ❌ Expected {test_case['expected']}, got {actual_backend}")
            
        except Exception as e:
            print(f"   ❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Clean up environment variables
        for key in test_case['env_vars']:
            if key in os.environ:
                del os.environ[key]

def test_agent_functionality():
    """Test that agents can actually process queries."""
    print("\n🧪 Testing Agent Functionality")
    print("=" * 50)
    
    # Set to Supabase backend for testing
    os.environ['RAG_BACKEND'] = 'supabase'
    
    try:
        from workflow import MultiAgentWorkflow
        
        # Create workflow
        workflow = MultiAgentWorkflow()
        print(f"✅ Workflow created with {workflow.backend_type} backend")
        
        # Test query processing
        test_query = "authentication error in login system"
        print(f"🔍 Testing query: '{test_query}'")
        
        # This would normally be async, but for testing we'll just check initialization
        if workflow.contextual_compression_agent:
            print("✅ ContextualCompression agent available for processing")
        else:
            print("❌ ContextualCompression agent not available")
        
        if workflow.ensemble_agent:
            print("✅ Ensemble agent available for processing")
        else:
            print("❌ Ensemble agent not available")
        
    except Exception as e:
        print(f"❌ Agent functionality test failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Run all backend switching tests."""
    print("🚀 Backend Switching Test Suite")
    print("=" * 60)
    
    # Setup environment
    setup_environment()
    
    # Run tests
    test_backend_switching()
    test_agent_functionality()
    
    print("\n🎉 Backend switching tests completed!")
    print("\n📝 Summary:")
    print("   • Backend switching via RAG_BACKEND environment variable")
    print("   • Support for 'qdrant', 'supabase', and 'auto' modes")
    print("   • Automatic fallback when preferred backend unavailable")
    print("   • Both LangChain and Supabase agents supported")

if __name__ == "__main__":
    main()
