#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
WebSearch Integration Tests
End-to-end integration tests for WebSearch functionality with workflow
"""

import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_websearch_integration(workflow, summary_data):
    """Test WebSearch integration with full workflow."""
    print("🔗 TESTING: WebSearch Integration")
    print("=" * 50)
    
    integration_results = []
    
    # Test cases that should route to WebSearch
    integration_test_cases = [
        {
            'query': 'Is AWS Lambda service down right now?',
            'production_incident': True,
            'user_can_wait': False,
            'expected_routing': 'WebSearch',
            'test_type': 'status_check'
        },
        {
            'query': 'GitHub outage status today',
            'production_incident': True,
            'user_can_wait': False,
            'expected_routing': 'WebSearch',
            'test_type': 'status_check'
        },
        {
            'query': 'Docker Hub service status',
            'production_incident': False,
            'user_can_wait': True,
            'expected_routing': 'WebSearch',
            'test_type': 'service_status'
        }
    ]
    
    for i, test_case in enumerate(integration_test_cases, 1):
        print(f"\n🧪 Integration Test {i}: {test_case['query'][:40]}...")
        
        try:
            start_time = time.time()
            
            # Test routing decision first
            routing_result = workflow.get_routing_decision(
                query=test_case['query'],
                user_can_wait=test_case['user_can_wait'],
                production_incident=test_case['production_incident']
            )
            
            routing_time = time.time() - start_time
            routing_decision = routing_result.get('routing_decision')
            
            print(f"   📍 Routing: {routing_decision} (expected: {test_case['expected_routing']})")
            print(f"   ⏱️  Routing time: {routing_time:.2f}s")
            
            routing_correct = routing_decision == test_case['expected_routing']
            
            if routing_correct:
                print("   ✅ Routing correct - proceeding with full workflow test")
                
                # Test full workflow processing
                full_start_time = time.time()
                
                result = workflow.process_query(
                    query=test_case['query'],
                    user_can_wait=test_case['user_can_wait'],
                    production_incident=test_case['production_incident']
                )
                
                full_processing_time = time.time() - full_start_time
                
                # Analyze results
                num_contexts = len(result.get('retrieved_contexts', []))
                final_answer = result.get('final_answer', '')
                retrieval_method = result.get('retrieval_method', '')
                
                print(f"   📊 Retrieved contexts: {num_contexts}")
                print(f"   🔧 Retrieval method: {retrieval_method}")
                print(f"   📝 Answer length: {len(final_answer)} chars")
                print(f"   ⏱️  Total processing time: {full_processing_time:.2f}s")
                
                # Quality assessment
                if num_contexts >= 3 and len(final_answer) > 100 and full_processing_time < 15:
                    status = "✅ EXCELLENT"
                elif num_contexts >= 2 and len(final_answer) > 50:
                    status = "🟡 GOOD"
                elif num_contexts >= 1:
                    status = "🟠 FAIR"
                else:
                    status = "❌ POOR"
                
                integration_results.append({
                    'query': test_case['query'],
                    'routing_correct': True,
                    'num_contexts': num_contexts,
                    'answer_length': len(final_answer),
                    'processing_time': full_processing_time,
                    'status': status,
                    'retrieval_method': retrieval_method
                })
                
                print(f"   {status}")
                
            else:
                print(f"   🟡 Routing incorrect - got {routing_decision}, expected {test_case['expected_routing']}")
                
                integration_results.append({
                    'query': test_case['query'],
                    'routing_correct': False,
                    'routing_decision': routing_decision,
                    'expected_routing': test_case['expected_routing'],
                    'status': "🟡 ROUTING_ISSUE"
                })
                
        except Exception as e:
            print(f"   ❌ Integration test failed: {e}")
            
            integration_results.append({
                'query': test_case['query'],
                'status': "❌ ERROR",
                'error': str(e)
            })
    
    # Integration test summary
    print(f"\n📊 WEBSEARCH INTEGRATION SUMMARY:")
    print(f"   Total tests: {len(integration_test_cases)}")
    
    successful_tests = sum(1 for r in integration_results if "ERROR" not in r['status'])
    routing_correct_count = sum(1 for r in integration_results if r.get('routing_correct', False))
    
    print(f"   Successful tests: {successful_tests}/{len(integration_test_cases)}")
    print(f"   Correct routing: {routing_correct_count}/{len(integration_test_cases)}")
    
    if successful_tests > 0:
        excellent_count = sum(1 for r in integration_results if r.get('status', '').startswith('✅'))
        good_count = sum(1 for r in integration_results if r.get('status', '').startswith('🟡'))
        
        print(f"   Excellent results: {excellent_count}")
        print(f"   Good results: {good_count}")
        
        # Calculate averages for successful tests
        successful_results = [r for r in integration_results if 'processing_time' in r]
        if successful_results:
            avg_contexts = sum(r.get('num_contexts', 0) for r in successful_results) / len(successful_results)
            avg_time = sum(r.get('processing_time', 0) for r in successful_results) / len(successful_results)
            
            print(f"   Avg contexts per query: {avg_contexts:.1f}")
            print(f"   Avg processing time: {avg_time:.2f}s")
            
            # Overall integration status
            if excellent_count >= 2 and routing_correct_count >= 2:
                integration_status = "✅ EXCELLENT"
            elif successful_tests >= 2:
                integration_status = "🟡 GOOD"
            elif successful_tests >= 1:
                integration_status = "🟠 FAIR"
            else:
                integration_status = "❌ POOR"
        else:
            integration_status = "❌ POOR"
    else:
        integration_status = "❌ POOR"
    
    print(f"   Overall Integration Status: {integration_status}")
    
    # Store results for overall summary
    summary_data['components_tested'].append('WebSearchIntegration')
    summary_data['test_results']['WebSearchIntegration'] = {
        'status': integration_status,
        'successful_tests': successful_tests,
        'total_tests': len(integration_test_cases),
        'routing_accuracy': f"{routing_correct_count}/{len(integration_test_cases)}",
        'excellent_results': excellent_count if 'excellent_count' in locals() else 0
    }
    
    if integration_status in ["❌ POOR", "❌ ERROR"]:
        summary_data['recommendations'].append(
            "WebSearch Integration: Check end-to-end workflow and routing logic"
        )
    elif integration_status == "🟠 FAIR":
        summary_data['recommendations'].append(
            "WebSearch Integration: Consider optimizing response generation and context retrieval"
        )
    
    print("\n" + "=" * 50)
    return summary_data