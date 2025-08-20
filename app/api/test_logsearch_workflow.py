#!/usr/bin/env python3
"""
LogSearch Workflow Integration Tests
Tests for LogSearch agent integration within the full multi-agent workflow
"""

import time
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_logsearch_workflow_integration(workflow, summary_data=None):
    """Test LogSearch integration within the full multi-agent workflow."""
    print("📋 TESTING: LogSearch Workflow Integration")
    print("=" * 60)
    
    # Test cases that should route to and use LogSearch
    logsearch_workflow_tests = [
        {
            'query': 'investigate recent certificate expired errors in production logs',
            'production_incident': True,
            'user_can_wait': False,
            'expected_routing': 'LogSearch',
            'test_type': 'certificate_error',
            'description': 'Certificate expiration error investigation'
        },
        {
            'query': 'find database connection timeout errors in application logs',
            'production_incident': True,
            'user_can_wait': False,
            'expected_routing': 'LogSearch', 
            'test_type': 'connection_error',
            'description': 'Database connection timeout analysis'
        },
        {
            'query': 'application startup errors in the last 24 hours',
            'production_incident': False,
            'user_can_wait': True,
            'expected_routing': 'LogSearch',
            'test_type': 'startup_error',
            'description': 'Application startup error analysis'
        },
        {
            'query': 'disk space exceeded exceptions in production',
            'production_incident': True,
            'user_can_wait': False,
            'expected_routing': 'LogSearch',
            'test_type': 'disk_space_error',
            'description': 'Disk space exception investigation'
        }
    ]
    
    workflow_results = []
    
    print(f"🧪 Running {len(logsearch_workflow_tests)} LogSearch workflow integration tests...")
    
    for i, test_case in enumerate(logsearch_workflow_tests, 1):
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
            retrieval_metadata = result.get('retrieval_metadata', {})
            
            print(f"   📍 Actual routing: {routing_decision}")
            print(f"   🔧 Retrieval method: {retrieval_method}")
            print(f"   📊 Retrieved contexts: {len(retrieved_contexts)}") 
            print(f"   📝 Answer length: {len(final_answer)} chars")
            print(f"   ⏱️  Processing time: {processing_time:.2f}s")
            print(f"   📋 Backend: {retrieval_metadata.get('backend', 'unknown')}")
            
            # Verify routing accuracy
            routing_correct = routing_decision == test_case['expected_routing']
            
            # Check if LogSearch was actually used (for LogSearch-routed queries)
            logsearch_used = 'LogSearch' in str(retrieval_method) or retrieval_metadata.get('backend') == 'gcp'
            
            # Quality assessment
            has_good_contexts = len(retrieved_contexts) >= 1  # LogSearch may have fewer results than WebSearch
            has_substantial_answer = len(final_answer) > 100
            reasonable_time = processing_time < 15
            
            # Check for log-specific indicators in contexts
            log_indicators = 0
            for ctx in retrieved_contexts[:3]:  # Check first 3 contexts
                metadata = ctx.get('metadata', {})
                content = ctx.get('content', '')
                if (metadata.get('level') in ['ERROR', 'WARN'] or 
                    metadata.get('timestamp') or 
                    'ERROR' in content or 
                    'Exception' in content):
                    log_indicators += 1
            
            has_log_sources = log_indicators > 0
            
            print(f"   ✅ Routing correct: {routing_correct}")
            print(f"   📋 LogSearch used: {logsearch_used}")
            print(f"   📝 Log sources found: {has_log_sources} ({log_indicators} log entries)")
            print(f"   📊 Quality metrics: Contexts={has_good_contexts}, Answer={has_substantial_answer}, Time={reasonable_time}")
            
            # Overall assessment
            if routing_correct and logsearch_used and has_log_sources and has_good_contexts and has_substantial_answer:
                status = "✅ EXCELLENT"
            elif routing_correct and (logsearch_used or has_log_sources) and has_good_contexts:
                status = "🟡 GOOD"
            elif routing_correct:
                status = "🟠 FAIR"
            else:
                status = "❌ POOR"
            
            workflow_results.append({
                'query': test_case['query'],
                'test_type': test_case['test_type'],
                'routing_correct': routing_correct,
                'logsearch_used': logsearch_used,
                'has_log_sources': has_log_sources,
                'num_contexts': len(retrieved_contexts),
                'answer_length': len(final_answer),
                'processing_time': processing_time,
                'status': status,
                'routing_decision': routing_decision,
                'retrieval_method': retrieval_method,
                'backend': retrieval_metadata.get('backend', 'unknown'),
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
                'logsearch_used': False
            })
    
    # Workflow integration summary
    print(f"\n📊 LOGSEARCH WORKFLOW INTEGRATION SUMMARY:")
    print(f"   Total tests: {len(logsearch_workflow_tests)}")
    
    successful_tests = sum(1 for r in workflow_results if "ERROR" not in r['status'])
    routing_correct_count = sum(1 for r in workflow_results if r.get('routing_correct', False))
    logsearch_used_count = sum(1 for r in workflow_results if r.get('logsearch_used', False))
    excellent_count = sum(1 for r in workflow_results if r.get('status', '').startswith('✅'))
    
    print(f"   Successful tests: {successful_tests}/{len(logsearch_workflow_tests)}")
    print(f"   Correct routing: {routing_correct_count}/{len(logsearch_workflow_tests)}")
    print(f"   LogSearch actually used: {logsearch_used_count}/{len(logsearch_workflow_tests)}")
    print(f"   Excellent results: {excellent_count}/{len(logsearch_workflow_tests)}")
    
    # Calculate averages for successful tests
    successful_results = [r for r in workflow_results if 'processing_time' in r]
    if successful_results:
        avg_contexts = sum(r.get('num_contexts', 0) for r in successful_results) / len(successful_results)
        avg_time = sum(r.get('processing_time', 0) for r in successful_results) / len(successful_results)
        avg_answer_length = sum(r.get('answer_length', 0) for r in successful_results) / len(successful_results)
        
        print(f"   Average contexts per query: {avg_contexts:.1f}")
        print(f"   Average processing time: {avg_time:.2f}s")
        print(f"   Average answer length: {avg_answer_length:.0f} chars")
        print(f"   Backend used: {workflow_results[0].get('backend', 'gcp') if workflow_results else 'gcp'}")
    
    # Overall integration status
    if excellent_count >= 3 and routing_correct_count >= 3 and logsearch_used_count >= 3:
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
        summary_data['components_tested'].append('LogSearchWorkflowIntegration')
        summary_data['test_results']['LogSearchWorkflowIntegration'] = {
            'status': integration_status,
            'successful_tests': successful_tests,
            'total_tests': len(logsearch_workflow_tests),
            'routing_accuracy': f"{routing_correct_count}/{len(logsearch_workflow_tests)}",
            'logsearch_usage': f"{logsearch_used_count}/{len(logsearch_workflow_tests)}",
            'excellent_results': excellent_count,
            'avg_processing_time': avg_time if 'avg_time' in locals() else 0,
            'backend': 'gcp',
            'test_breakdown': {test_type: len(results) for test_type, results in test_types.items()}
        }
        
        # Add recommendations based on results
        if integration_status == "❌ POOR":
            summary_data['recommendations'].append(
                "LogSearch Workflow: Check routing logic and LogSearch agent integration"
            )
        elif integration_status == "🟠 FAIR":
            summary_data['recommendations'].append(
                "LogSearch Workflow: Improve LogSearch result quality and response generation"
            )
        elif routing_correct_count < len(logsearch_workflow_tests):
            summary_data['recommendations'].append(
                "LogSearch Workflow: Review supervisor routing logic for better LogSearch detection"
            )
        elif logsearch_used_count < routing_correct_count:
            summary_data['recommendations'].append(
                "LogSearch Workflow: Verify LogSearch agent is properly processing routed queries"
            )
    
    print("\n" + "=" * 60)
    return summary_data

def test_logsearch_routing_only(workflow, summary_data=None):
    """Test just the routing decisions for LogSearch queries (synchronous)."""
    print("🧠 TESTING: LogSearch Routing Decisions")
    print("=" * 50)
    
    routing_test_cases = [
        {
            'query': 'investigate database connection errors in production logs',
            'production_incident': True,
            'user_can_wait': False,
            'expected': 'LogSearch'
        },
        {
            'query': 'certificate expired errors in the logs',
            'production_incident': True, 
            'user_can_wait': False,
            'expected': 'LogSearch'
        },
        {
            'query': 'application timeout exceptions last hour',
            'production_incident': True,
            'user_can_wait': False,
            'expected': 'LogSearch'
        },
        {
            'query': 'How to configure HBase cluster timeout settings',
            'production_incident': False,
            'user_can_wait': True,
            'expected': 'BM25'  # Should route to internal knowledge, not log search
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
        summary_data['components_tested'].append('LogSearchRouting')
        summary_data['test_results']['LogSearchRouting'] = {
            'status': routing_status,
            'accuracy': f"{correct_count}/{len(routing_test_cases)}",
            'accuracy_percentage': f"{routing_accuracy*100:.1f}%"
        }
    
    print("\n" + "=" * 50)
    return summary_data