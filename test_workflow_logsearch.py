#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
Test the workflow integration with LogSearch agent.
"""

import os
import sys
import asyncio
from datetime import datetime

# Set up environment
os.environ['USE_GCP_LOGGING'] = 'true'
os.environ['GOOGLE_CLOUD_PROJECT'] = 'octopus-282815'
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'scripts/logsearch-sa-key.json'

# Add app directory to path
sys.path.append('app')

try:
    from app.api.workflow import MultiAgentWorkflow
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

async def test_workflow_logsearch():
    """Test the workflow with LogSearch routing."""
    print("🚀 Testing Multi-Agent Workflow with LogSearch Integration")
    print("=" * 70)
    
    try:
        # Initialize workflow
        workflow = MultiAgentWorkflow()
        print("✅ Multi-Agent Workflow initialized")
        
        # Test 1: LogSearch routing decision
        print(f"\n📋 TEST 1: LogSearch Routing Decision")
        routing = await workflow.get_routing_decision(
            query="investigate recent database connection errors in production logs",
            production_incident=True
        )
        print(f"Routing decision: {routing['routing_decision']}")
        print(f"Reasoning: {routing['routing_reasoning']}")
        
        # Test 2: Full LogSearch workflow
        print(f"\n📋 TEST 2: Full LogSearch Workflow")
        result = await workflow.process_query(
            query="find recent certificate expired errors in the logs",
            production_incident=True,
            user_can_wait=False
        )
        
        print(f"Query: {result['query']}")
        print(f"Routing: {result['routing_decision']} - {result['routing_reasoning']}")
        print(f"Retrieval method: {result['retrieval_method']}")
        print(f"Results found: {result['retrieval_metadata'].get('num_results', 0)}")
        print(f"Backend used: {result['retrieval_metadata'].get('backend', 'unknown')}")
        print(f"Processing time: {result['total_processing_time']:.2f}s")
        print(f"Final answer length: {len(result['final_answer'])} chars")
        
        print(f"\n🎉 All workflow tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    success = asyncio.run(test_workflow_logsearch())
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()