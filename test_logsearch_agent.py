#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
Test script for the updated LogSearch Agent with GCP backend.
"""

import os
import sys
from datetime import datetime

# Add app directory to path
sys.path.append('app')

# Set up GCP environment
os.environ['USE_GCP_LOGGING'] = 'true'
os.environ['GOOGLE_CLOUD_PROJECT'] = 'octopus-282815'
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'scripts/logsearch-sa-key.json'

try:
    from langchain_openai import ChatOpenAI
    from app.agents.log_search_agent import LogSearchAgent
    from app.agents.common import AgentState
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def test_logsearch_agent():
    """Test the LogSearch Agent with GCP backend."""
    print("🚀 Testing LogSearch Agent with GCP Backend")
    print("=" * 60)
    
    try:
        # Initialize LLM (using a dummy API key for this test)
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=os.environ.get('OPENAI_API_KEY', 'test-key'),
            temperature=0
        )
        
        # Initialize LogSearch Agent (should auto-detect GCP backend)
        agent = LogSearchAgent(llm, max_searches=2)
        
        print(f"✅ LogSearch Agent initialized with backend: {agent.backend}")
        
        # Test 1: Simple error search
        print(f"\n📋 TEST 1: Simple Error Search")
        test_state = {
            'query': 'find recent error logs',
            'production_incident': False
        }
        
        result_state = agent.process(test_state)
        
        print(f"Retrieved contexts: {len(result_state.get('retrieved_contexts', []))}")
        print(f"Retrieval method: {result_state.get('retrieval_method', 'None')}")
        print(f"Backend used: {result_state.get('retrieval_metadata', {}).get('backend', 'unknown')}")
        
        if result_state.get('retrieved_contexts'):
            sample_result = result_state['retrieved_contexts'][0]
            print(f"Sample result metadata: {sample_result.get('metadata', {})}")
            print(f"Sample content: {sample_result.get('content', 'No content')[:100]}...")
        
        # Test 2: Production incident search
        print(f"\n📋 TEST 2: Production Incident Search")
        incident_state = {
            'query': 'certificate expired errors',
            'production_incident': True
        }
        
        incident_result = agent.process(incident_state)
        
        print(f"Retrieved contexts: {len(incident_result.get('retrieved_contexts', []))}")
        print(f"Production incident handling: {incident_result.get('retrieval_metadata', {}).get('production_incident', False)}")
        print(f"Search strategy: {incident_result.get('retrieval_metadata', {}).get('search_strategy', 'unknown')}")
        
        # Test 3: Health check
        print(f"\n📋 TEST 3: Backend Health Check")
        health = agent.search_tools.health_check()
        print(f"Health status: {health.get('status', 'unknown')}")
        print(f"Authentication method: {health.get('authentication', {}).get('auth_method', 'unknown')}")
        
        print(f"\n🎉 All tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    success = test_logsearch_agent()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()