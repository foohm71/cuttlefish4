#!/usr/bin/env python3
"""
LogSearch Agent Tests
Separate test file for LogSearch functionality that can be imported into TestAgents.ipynb
"""

import time
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_logsearch_agent(supervisor_llm, supervisor_agent, summary_data):
    """Test LogSearch Agent functionality with GCP backend."""
    print("📋 TESTING: LogSearch Agent (GCP Backend)")
    print("=" * 50)

    # Note: GCP credentials should be set in notebook environment
    # Set project if not already set
    if not os.environ.get('GOOGLE_CLOUD_PROJECT'):
        os.environ['GOOGLE_CLOUD_PROJECT'] = 'octopus-282815'

    # Initialize LogSearch agent
    try:
        from log_search_agent import LogSearchAgent
        
        # Create LogSearch agent with GCP backend
        logsearch_agent = LogSearchAgent(llm=supervisor_llm, max_searches=3)
        
        print("✅ LogSearch Agent initialized successfully")
        print(f"   Max searches: {logsearch_agent.max_searches}")
        print(f"   Backend: {logsearch_agent.backend}")
        
        # Test GCP backend connectivity with a simple search
        try:
            # Test with a simple search to verify connectivity
            test_search = logsearch_agent.search_tools.search_logs("test", max_results=1)
            print("✅ GCP backend connection successful")
            print(f"   Project: {logsearch_agent.search_tools.project_id}")
            
            # Test different types of log queries
            test_queries = [
                {
                    'query': 'find recent certificate expired errors',
                    'production_incident': True,
                    'user_can_wait': False,
                    'expected_type': 'production_issue'
                },
                {
                    'query': 'database connection timeout errors in logs',
                    'production_incident': True, 
                    'user_can_wait': False,
                    'expected_type': 'exception_search'
                },
                {
                    'query': 'application startup errors last 24 hours',
                    'production_incident': False,
                    'user_can_wait': True,
                    'expected_type': 'general_search'
                },
                {
                    'query': 'disk space exceeded exceptions',
                    'production_incident': False,
                    'user_can_wait': True,
                    'expected_type': 'exception_search'
                }
            ]
            
            logsearch_results = []
            
            for i, test_case in enumerate(test_queries, 1):
                print(f"\n🔍 Test Case {i}: {test_case['query'][:40]}...")
                
                # Create test state
                test_state = {
                    'query': test_case['query'],
                    'user_can_wait': test_case['user_can_wait'],
                    'production_incident': test_case['production_incident'],
                    'routing_decision': 'LogSearch',
                    'routing_reasoning': 'Testing LogSearch functionality',
                    'retrieved_contexts': [],
                    'retrieval_method': None,
                    'retrieval_metadata': {},
                    'final_answer': None,
                    'relevant_tickets': [],
                    'messages': []
                }
                
                # Process query
                try:
                    start_time = time.time()
                    result_state = logsearch_agent.process(test_state)
                    processing_time = time.time() - start_time
                    
                    # Extract results
                    num_results = len(result_state['retrieved_contexts'])
                    method = result_state['retrieval_method']
                    metadata = result_state['retrieval_metadata']
                    
                    print(f"   ✅ Retrieved {num_results} results")
                    print(f"   📊 Processing time: {processing_time:.2f}s")
                    print(f"   🔧 Method: {method}")
                    print(f"   📋 Backend: {metadata.get('backend', 'gcp')}")
                    print(f"   🔍 Searches performed: {metadata.get('searches_performed', 0)}")
                    
                    # Check result quality
                    if num_results > 0:
                        sample_result = result_state['retrieved_contexts'][0]
                        content_length = len(sample_result.get('content', ''))
                        has_timestamp = 'timestamp' in sample_result.get('metadata', {})
                        log_level = sample_result.get('metadata', {}).get('level', 'unknown')
                        
                        print(f"   📝 Sample result content length: {content_length}")
                        print(f"   ⏰ Has timestamp: {has_timestamp}")
                        print(f"   📊 Log level: {log_level}")
                        
                        if content_length > 50 and has_timestamp:
                            status = "✅ EXCELLENT"
                        elif content_length > 20:
                            status = "🟡 GOOD"  
                        else:
                            status = "🟠 FAIR"
                    else:
                        status = "🟠 NO RESULTS"
                    
                    logsearch_results.append({
                        'query': test_case['query'],
                        'status': status,
                        'num_results': num_results,
                        'processing_time': processing_time,
                        'method': method,
                        'backend': 'gcp'
                    })
                    
                    print(f"   {status}")
                    
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                    logsearch_results.append({
                        'query': test_case['query'],
                        'status': "❌ ERROR",
                        'error': str(e)
                    })
            
            # LogSearch agent summary
            print(f"\n📊 LOGSEARCH AGENT SUMMARY:")
            print(f"   Test cases run: {len(test_queries)}")
            
            successful_tests = sum(1 for r in logsearch_results if "ERROR" not in r['status'])
            print(f"   Successful tests: {successful_tests}/{len(test_queries)}")
            
            if successful_tests > 0:
                avg_results = sum(r.get('num_results', 0) for r in logsearch_results if 'num_results' in r) / successful_tests
                avg_time = sum(r.get('processing_time', 0) for r in logsearch_results if 'processing_time' in r) / successful_tests
                
                print(f"   Average results per query: {avg_results:.1f}")
                print(f"   Average processing time: {avg_time:.2f}s")
                print(f"   Backend used: gcp")
                
                if avg_results >= 1 and avg_time < 15:
                    logsearch_status = "✅ EXCELLENT"
                elif avg_results >= 0.5:
                    logsearch_status = "🟡 GOOD"
                else:
                    logsearch_status = "🟠 FAIR"
            else:
                logsearch_status = "❌ POOR"
                avg_results = 0
                avg_time = 0
            
            print(f"   Overall LogSearch Status: {logsearch_status}")
            
            # Test supervisor routing to LogSearch
            print(f"\n🧠 Testing Supervisor Routing to LogSearch:")
            
            # Test queries that should route to LogSearch
            routing_test_queries = [
                "investigate recent database connection errors in production logs",
                "find certificate expired errors in the logs", 
                "application timeout exceptions last hour",
                "disk space errors in production"
            ]
            
            routing_success = 0
            for query in routing_test_queries:
                try:
                    routing_result = supervisor_agent.route_query(
                        query=query,
                        user_can_wait=False, 
                        production_incident=True
                    )
                    
                    if routing_result['agent'] == 'LogSearch':
                        print(f"   ✅ '{query[:35]}...' → LogSearch")
                        routing_success += 1
                    else:
                        print(f"   🟡 '{query[:35]}...' → {routing_result['agent']} (expected LogSearch)")
                        
                except Exception as e:
                    print(f"   ❌ Routing failed for '{query[:35]}...': {e}")
            
            print(f"   Routing accuracy: {routing_success}/{len(routing_test_queries)}")
            
            # Store results for overall summary
            summary_data['components_tested'].append('LogSearchAgent')
            summary_data['test_results']['LogSearchAgent'] = {
                'status': logsearch_status,
                'successful_tests': successful_tests,
                'total_tests': len(test_queries),
                'routing_accuracy': f"{routing_success}/{len(routing_test_queries)}",
                'avg_results_per_query': avg_results,
                'avg_processing_time': avg_time,
                'backend': 'gcp'
            }
            
            if logsearch_status in ["❌ POOR", "❌ ERROR"]:
                summary_data['recommendations'].append(
                    "LogSearch Agent: Check GCP backend connectivity and authentication"
                )
            elif logsearch_status == "🟠 FAIR":
                summary_data['recommendations'].append(
                    "LogSearch Agent: Consider adding more synthetic log data for better test coverage"
                )
        
        except Exception as e:
            print(f"❌ GCP backend test failed: {e}")
            summary_data['components_tested'].append('LogSearchAgent')
            summary_data['test_results']['LogSearchAgent'] = {
                'status': "❌ GCP CONNECTION FAILED",
                'error': str(e)
            }
            summary_data['recommendations'].append(
                "LogSearch Agent: Check GCP credentials and project configuration"
            )
            
    except ImportError as e:
        print(f"❌ Failed to import LogSearchAgent: {e}")
        print("   Ensure log_search_agent.py is available")
        
        summary_data['components_tested'].append('LogSearchAgent')  
        summary_data['test_results']['LogSearchAgent'] = {
            'status': "❌ IMPORT FAILED",
            'error': str(e)
        }
        summary_data['recommendations'].append(
            "LogSearch Agent: Check LogSearchAgent import and dependencies"
        )

    except Exception as e:
        print(f"❌ LogSearch Agent testing failed: {e}")
        
        summary_data['components_tested'].append('LogSearchAgent')
        summary_data['test_results']['LogSearchAgent'] = {
            'status': "❌ TEST FAILED", 
            'error': str(e)
        }

    print("\n" + "=" * 50)
    return summary_data