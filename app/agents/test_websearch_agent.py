#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
WebSearch Agent Tests
Separate test file for WebSearch functionality that can be imported into TestAgents.ipynb
"""

import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_websearch_agent(supervisor_llm, supervisor_agent, summary_data):
    """Test WebSearch Agent functionality."""
    print("🌐 TESTING: WebSearch Agent")
    print("=" * 50)

    # Initialize WebSearch agent
    try:
        from web_search_agent import WebSearchAgent
        
        # Create WebSearch agent
        websearch_agent = WebSearchAgent(llm=supervisor_llm, max_searches=3)
        
        print("✅ WebSearch Agent initialized successfully")
        print(f"   Max searches: {websearch_agent.max_searches}")
        
        # Test web search tools connectivity
        if websearch_agent.web_search_tools.test_connection():
            print("✅ Tavily API connection successful")
            
            # Test different types of queries
            test_queries = [
                {
                    'query': 'GitHub status outage',
                    'production_incident': True,
                    'user_can_wait': False,
                    'expected_type': 'status_check'
                },
                {
                    'query': 'AWS Lambda service down',
                    'production_incident': True, 
                    'user_can_wait': False,
                    'expected_type': 'status_check'
                },
                {
                    'query': 'latest security vulnerability Java Spring',
                    'production_incident': False,
                    'user_can_wait': True,
                    'expected_type': 'general_research'
                }
            ]
            
            websearch_results = []
            
            for i, test_case in enumerate(test_queries, 1):
                print(f"\n🔍 Test Case {i}: {test_case['query'][:40]}...")
                
                # Create test state
                test_state = {
                    'query': test_case['query'],
                    'user_can_wait': test_case['user_can_wait'],
                    'production_incident': test_case['production_incident'],
                    'routing_decision': 'WebSearch',
                    'routing_reasoning': 'Testing WebSearch functionality',
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
                    result_state = websearch_agent.process(test_state)
                    processing_time = time.time() - start_time
                    
                    # Extract results
                    num_results = len(result_state['retrieved_contexts'])
                    method = result_state['retrieval_method']
                    metadata = result_state['retrieval_metadata']
                    
                    print(f"   ✅ Retrieved {num_results} results")
                    print(f"   📊 Processing time: {processing_time:.2f}s")
                    print(f"   🔧 Method: {method}")
                    print(f"   🔍 Searches performed: {metadata.get('searches_performed', 0)}")
                    
                    # Check result quality
                    if num_results > 0:
                        sample_result = result_state['retrieved_contexts'][0]
                        content_length = len(sample_result.get('content', ''))
                        has_url = 'url' in sample_result.get('metadata', {})
                        
                        print(f"   📝 Sample result content length: {content_length}")
                        print(f"   🔗 Has URL: {has_url}")
                        
                        if content_length > 50 and has_url:
                            status = "✅ EXCELLENT"
                        elif content_length > 20:
                            status = "🟡 GOOD"  
                        else:
                            status = "🟠 FAIR"
                    else:
                        status = "❌ POOR"
                    
                    websearch_results.append({
                        'query': test_case['query'],
                        'status': status,
                        'num_results': num_results,
                        'processing_time': processing_time,
                        'method': method
                    })
                    
                    print(f"   {status}")
                    
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                    websearch_results.append({
                        'query': test_case['query'],
                        'status': "❌ ERROR",
                        'error': str(e)
                    })
            
            # WebSearch agent summary
            print(f"\n📊 WEBSEARCH AGENT SUMMARY:")
            print(f"   Test cases run: {len(test_queries)}")
            
            successful_tests = sum(1 for r in websearch_results if "ERROR" not in r['status'])
            print(f"   Successful tests: {successful_tests}/{len(test_queries)}")
            
            if successful_tests > 0:
                avg_results = sum(r.get('num_results', 0) for r in websearch_results if 'num_results' in r) / successful_tests
                avg_time = sum(r.get('processing_time', 0) for r in websearch_results if 'processing_time' in r) / successful_tests
                
                print(f"   Average results per query: {avg_results:.1f}")
                print(f"   Average processing time: {avg_time:.2f}s")
                
                if avg_results >= 3 and avg_time < 10:
                    websearch_status = "✅ EXCELLENT"
                elif avg_results >= 2:
                    websearch_status = "🟡 GOOD"
                else:
                    websearch_status = "🟠 FAIR"
            else:
                websearch_status = "❌ POOR"
                avg_results = 0
                avg_time = 0
            
            print(f"   Overall WebSearch Status: {websearch_status}")
            
            # Test supervisor routing to WebSearch
            print(f"\n🧠 Testing Supervisor Routing to WebSearch:")
            
            # Test queries that should route to WebSearch
            routing_test_queries = [
                "Is GitHub down right now?",
                "AWS outage status",
                "Docker Hub service status"
            ]
            
            routing_success = 0
            for query in routing_test_queries:
                try:
                    routing_result = supervisor_agent.route_query(
                        query=query,
                        user_can_wait=False, 
                        production_incident=True
                    )
                    
                    if routing_result['agent'] == 'WebSearch':
                        print(f"   ✅ '{query[:30]}...' → WebSearch")
                        routing_success += 1
                    else:
                        print(f"   🟡 '{query[:30]}...' → {routing_result['agent']} (expected WebSearch)")
                        
                except Exception as e:
                    print(f"   ❌ Routing failed for '{query[:30]}...': {e}")
            
            print(f"   Routing accuracy: {routing_success}/{len(routing_test_queries)}")
            
            # Store results for overall summary
            summary_data['components_tested'].append('WebSearchAgent')
            summary_data['test_results']['WebSearchAgent'] = {
                'status': websearch_status,
                'successful_tests': successful_tests,
                'total_tests': len(test_queries),
                'routing_accuracy': f"{routing_success}/{len(routing_test_queries)}",
                'avg_results_per_query': avg_results,
                'avg_processing_time': avg_time
            }
            
            if websearch_status in ["❌ POOR", "❌ ERROR"]:
                summary_data['recommendations'].append(
                    "WebSearch Agent: Check Tavily API key and internet connectivity"
                )
            elif websearch_status == "🟠 FAIR":
                summary_data['recommendations'].append(
                    "WebSearch Agent: Consider optimizing query strategies for better results"
                )
        
        else:
            print("❌ Tavily API connection failed")
            print("   Check TAVILY_API_KEY environment variable")
            
            summary_data['components_tested'].append('WebSearchAgent')
            summary_data['test_results']['WebSearchAgent'] = {
                'status': "❌ API CONNECTION FAILED",
                'error': 'Tavily API key not configured or invalid'
            }
            summary_data['recommendations'].append(
                "WebSearch Agent: Set TAVILY_API_KEY environment variable"
            )
            
    except ImportError as e:
        print(f"❌ Failed to import WebSearchAgent: {e}")
        print("   Ensure web_search_agent.py is available")
        
        summary_data['components_tested'].append('WebSearchAgent')  
        summary_data['test_results']['WebSearchAgent'] = {
            'status': "❌ IMPORT FAILED",
            'error': str(e)
        }
        summary_data['recommendations'].append(
            "WebSearch Agent: Check WebSearchAgent import and dependencies"
        )

    except Exception as e:
        print(f"❌ WebSearch Agent testing failed: {e}")
        
        summary_data['components_tested'].append('WebSearchAgent')
        summary_data['test_results']['WebSearchAgent'] = {
            'status': "❌ TEST FAILED", 
            'error': str(e)
        }

    print("\n" + "=" * 50)
    return summary_data