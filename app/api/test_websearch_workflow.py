#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
WebSearch Workflow Integration Tests
Tests for WebSearch agent integration within the full multi-agent workflow
"""

import time
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_websearch_workflow_integration(workflow, summary_data=None):
    """Test WebSearch integration within the full multi-agent workflow."""
    print("🔗 TESTING: WebSearch Workflow Integration")
    print("=" * 60)
    
    # Test cases that should route to and use WebSearch
    websearch_workflow_tests = [
        {
            'query': 'Is GitHub down right now?',
            'production_incident': True,
            'user_can_wait': False,
            'expected_routing': 'WebSearch',
            'test_type': 'status_check',
            'description': 'GitHub service status inquiry'
        },
        {
            'query': 'AWS Lambda outage today',
            'production_incident': True,
            'user_can_wait': False,
            'expected_routing': 'WebSearch', 
            'test_type': 'outage_check',
            'description': 'AWS Lambda service outage check'
        },
        {
            'query': 'Docker Hub registry down',
            'production_incident': False,
            'user_can_wait': True,
            'expected_routing': 'WebSearch',
            'test_type': 'service_status',
            'description': 'Docker Hub registry status'
        },
        {
            'query': 'Latest security vulnerability in Java Spring Boot',
            'production_incident': False,
            'user_can_wait': True,
            'expected_routing': 'WebSearch',
            'test_type': 'research',
            'description': 'Security research query'
        }
    ]
    
    workflow_results = []
    
    print(f"🧪 Running {len(websearch_workflow_tests)} WebSearch workflow integration tests...")
    
    for i, test_case in enumerate(websearch_workflow_tests, 1):
        print(f"\n📋 Test {i}: {test_case['description']}")
        print(f"   Query: '{test_case['query']}'")
        print(f"   Expected routing: {test_case['expected_routing']}")
        
        try:
            start_time = time.time()
            
            # Test complete workflow processing
            result = await workflow.process_query(
                query=test_case['query'],
                user_can_wait=test_case['user_can_wait'],
                production_incident=test_case['production_incident']
            )
            
            processing_time = time.time() - start_time
            
            # Extract key results
            routing_decision = result.get('routing_decision', 'UNKNOWN')
            final_answer = result.get('final_answer', '')
            retrieved_contexts = result.get('retrieved_contexts', [])
            retrieval_method = result.get('retrieval_method', '')
            routing_reasoning = result.get('routing_reasoning', '')
            
            print(f"   📍 Actual routing: {routing_decision}")
            print(f"   🔧 Retrieval method: {retrieval_method}")
            print(f"   📊 Retrieved contexts: {len(retrieved_contexts)}") 
            print(f"   📝 Answer length: {len(final_answer)} chars")
            print(f"   ⏱️  Processing time: {processing_time:.2f}s")
            
            # Verify routing accuracy
            routing_correct = routing_decision == test_case['expected_routing']
            
            # Check if WebSearch was actually used (for WebSearch-routed queries)
            websearch_used = 'WebSearch' in str(retrieval_method) or 'tavily' in str(retrieval_method).lower()
            
            # Quality assessment
            has_good_contexts = len(retrieved_contexts) >= 2
            has_substantial_answer = len(final_answer) > 100
            reasonable_time = processing_time < 15
            
            # Check for web-specific indicators in contexts
            web_indicators = 0
            for ctx in retrieved_contexts[:3]:  # Check first 3 contexts
                metadata = ctx.get('metadata', {})
                if metadata.get('url') or metadata.get('source') == 'tavily':
                    web_indicators += 1
            
            has_web_sources = web_indicators > 0
            
            print(f"   ✅ Routing correct: {routing_correct}")
            print(f"   🌐 WebSearch used: {websearch_used}")
            print(f"   🔗 Web sources found: {has_web_sources} ({web_indicators} sources)")
            print(f"   📊 Quality metrics: Contexts={has_good_contexts}, Answer={has_substantial_answer}, Time={reasonable_time}")
            
            # Overall assessment
            if routing_correct and websearch_used and has_web_sources and has_good_contexts and has_substantial_answer:
                status = "✅ EXCELLENT"
            elif routing_correct and (websearch_used or has_web_sources) and has_good_contexts:
                status = "🟡 GOOD"
            elif routing_correct:
                status = "🟠 FAIR"
            else:
                status = "❌ POOR"
            
            workflow_results.append({
                'query': test_case['query'],
                'test_type': test_case['test_type'],
                'routing_correct': routing_correct,
                'websearch_used': websearch_used,
                'has_web_sources': has_web_sources,
                'num_contexts': len(retrieved_contexts),
                'answer_length': len(final_answer),
                'processing_time': processing_time,
                'status': status,
                'routing_decision': routing_decision,
                'retrieval_method': retrieval_method,
                'routing_reasoning': routing_reasoning[:100] + '...' if len(routing_reasoning) > 100 else routing_reasoning
            })
            
            print(f"   🎯 Overall: {status}")
            
        except Exception as e:
            print(f"   ❌ Workflow test failed: {e}")
            workflow_results.append({
                'query': test_case['query'],
                'test_type': test_case['test_type'],
                'status': "❌ ERROR",
                'error': str(e),
                'routing_correct': False,
                'websearch_used': False
            })
    
    # Workflow integration summary
    print(f"\n📊 WEBSEARCH WORKFLOW INTEGRATION SUMMARY:")
    print(f"   Total tests: {len(websearch_workflow_tests)}")
    
    successful_tests = sum(1 for r in workflow_results if "ERROR" not in r['status'])
    routing_correct_count = sum(1 for r in workflow_results if r.get('routing_correct', False))
    websearch_used_count = sum(1 for r in workflow_results if r.get('websearch_used', False))
    excellent_count = sum(1 for r in workflow_results if r.get('status', '').startswith('✅'))
    
    print(f"   Successful tests: {successful_tests}/{len(websearch_workflow_tests)}")
    print(f"   Correct routing: {routing_correct_count}/{len(websearch_workflow_tests)}")
    print(f"   WebSearch actually used: {websearch_used_count}/{len(websearch_workflow_tests)}")
    print(f"   Excellent results: {excellent_count}/{len(websearch_workflow_tests)}")
    
    # Calculate averages for successful tests
    successful_results = [r for r in workflow_results if 'processing_time' in r]
    if successful_results:
        avg_contexts = sum(r.get('num_contexts', 0) for r in successful_results) / len(successful_results)
        avg_time = sum(r.get('processing_time', 0) for r in successful_results) / len(successful_results)
        avg_answer_length = sum(r.get('answer_length', 0) for r in successful_results) / len(successful_results)
        
        print(f"   Average contexts per query: {avg_contexts:.1f}")
        print(f"   Average processing time: {avg_time:.2f}s")
        print(f"   Average answer length: {avg_answer_length:.0f} chars")
    
    # Overall integration status
    if excellent_count >= 3 and routing_correct_count >= 3 and websearch_used_count >= 3:
        integration_status = "✅ EXCELLENT"
    elif excellent_count >= 2 and routing_correct_count >= 3:
        integration_status = "🟡 GOOD"
    elif successful_tests >= 2 and routing_correct_count >= 2:
        integration_status = "🟠 FAIR"
    else:
        integration_status = "❌ POOR"
    
    print(f"   Overall Integration Status: {integration_status}")
    
    # Detailed breakdown by test type
    print(f"\n📋 DETAILED RESULTS BY TEST TYPE:")
    test_types = {}
    for result in workflow_results:
        test_type = result.get('test_type', 'unknown')
        if test_type not in test_types:
            test_types[test_type] = []
        test_types[test_type].append(result)
    
    for test_type, results in test_types.items():
        successful_in_type = sum(1 for r in results if "ERROR" not in r['status'])
        print(f"   {test_type}: {successful_in_type}/{len(results)} successful")
    
    # Store results in summary_data if provided
    if summary_data is not None:
        summary_data['components_tested'].append('WebSearchWorkflowIntegration')
        summary_data['test_results']['WebSearchWorkflowIntegration'] = {
            'status': integration_status,
            'successful_tests': successful_tests,
            'total_tests': len(websearch_workflow_tests),
            'routing_accuracy': f"{routing_correct_count}/{len(websearch_workflow_tests)}",
            'websearch_usage': f"{websearch_used_count}/{len(websearch_workflow_tests)}",
            'excellent_results': excellent_count,
            'avg_processing_time': avg_time if 'avg_time' in locals() else 0,
            'test_breakdown': {test_type: len(results) for test_type, results in test_types.items()}
        }
        
        # Add recommendations based on results
        if integration_status == "❌ POOR":
            summary_data['recommendations'].append(
                "WebSearch Workflow: Check routing logic and WebSearch agent integration"
            )
        elif integration_status == "🟠 FAIR":
            summary_data['recommendations'].append(
                "WebSearch Workflow: Improve WebSearch result quality and response generation"
            )
        elif routing_correct_count < len(websearch_workflow_tests):
            summary_data['recommendations'].append(
                "WebSearch Workflow: Review supervisor routing logic for better WebSearch detection"
            )
        elif websearch_used_count < routing_correct_count:
            summary_data['recommendations'].append(
                "WebSearch Workflow: Verify WebSearch agent is properly processing routed queries"
            )
    
    print("\n" + "=" * 60)
    return summary_data

def test_websearch_routing_only(workflow, summary_data=None):
    """Test just the routing decisions for WebSearch queries (synchronous)."""
    print("🧠 TESTING: WebSearch Routing Decisions")
    print("=" * 50)
    
    routing_test_cases = [
        {
            'query': 'Is GitHub down?',
            'production_incident': True,
            'user_can_wait': False,
            'expected': 'WebSearch'
        },
        {
            'query': 'AWS Lambda outage',
            'production_incident': True, 
            'user_can_wait': False,
            'expected': 'WebSearch'
        },
        {
            'query': 'Spring Boot security vulnerability',
            'production_incident': False,
            'user_can_wait': True,
            'expected': 'WebSearch'
        },
        {
            'query': 'How to configure HBase cluster',
            'production_incident': False,
            'user_can_wait': True,
            'expected': 'BM25'  # Should route to internal knowledge, not web search
        }
    ]
    
    routing_results = []
    
    async def test_routing_async():
        for i, test_case in enumerate(routing_test_cases, 1):
            print(f"\n🔍 Routing Test {i}: '{test_case['query']}'")
            
            try:
                result = await workflow.get_routing_decision(
                    query=test_case['query'],
                    user_can_wait=test_case['user_can_wait'],
                    production_incident=test_case['production_incident']
                )
                
                routing_decision = result.get('routing_decision')
                routing_reasoning = result.get('routing_reasoning', '')
                
                correct = routing_decision == test_case['expected']
                print(f"   Expected: {test_case['expected']}")
                print(f"   Got: {routing_decision}")
                print(f"   Reasoning: {routing_reasoning[:100]}...")
                print(f"   ✅ Correct: {correct}")
                
                routing_results.append({
                    'query': test_case['query'],
                    'expected': test_case['expected'],
                    'actual': routing_decision,
                    'correct': correct,
                    'reasoning': routing_reasoning
                })
                
            except Exception as e:
                print(f"   ❌ Routing failed: {e}")
                routing_results.append({
                    'query': test_case['query'],
                    'expected': test_case['expected'],
                    'actual': 'ERROR',
                    'correct': False,
                    'error': str(e)
                })
    
    # Run the async routing tests
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_routing_async())
    
    # Summary
    correct_count = sum(1 for r in routing_results if r.get('correct', False))
    print(f"\n📊 ROUTING SUMMARY:")
    print(f"   Correct routing decisions: {correct_count}/{len(routing_test_cases)}")
    
    routing_accuracy = correct_count / len(routing_test_cases) if routing_test_cases else 0
    if routing_accuracy >= 0.8:
        routing_status = "✅ EXCELLENT"
    elif routing_accuracy >= 0.6:
        routing_status = "🟡 GOOD"
    else:
        routing_status = "❌ NEEDS IMPROVEMENT"
    
    print(f"   Routing Status: {routing_status}")
    
    if summary_data is not None:
        summary_data['components_tested'].append('WebSearchRouting')
        summary_data['test_results']['WebSearchRouting'] = {
            'status': routing_status,
            'accuracy': f"{correct_count}/{len(routing_test_cases)}",
            'accuracy_percentage': f"{routing_accuracy*100:.1f}%"
        }
    
    print("\n" + "=" * 50)
    return summary_data