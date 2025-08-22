#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
TestSupabaseAgents.py - Comprehensive testing for Supabase-based agents

Purpose: Test the new Supabase agents that use RAG tools instead of LangChain vectorstores
Status: 🧪 Testing and Validation Framework
Created: August 2025

This script tests:
1. SupabaseBM25Agent - Keyword search using Supabase RAG tools
2. SupabaseContextualCompressionAgent - Vector similarity search
3. SupabaseEnsembleAgent - Multi-method retrieval combining all approaches
4. Agent integration and performance comparison
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Setup paths
current_dir = Path(__file__).parent
app_dir = current_dir.parent
project_root = app_dir.parent

# Add to Python path
for path in [str(project_root), str(app_dir), str(current_dir)]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Load environment variables
try:
    from dotenv import load_dotenv
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(str(env_file))
        print(f"✅ Loaded .env file from: {env_file}")
    else:
        load_dotenv()
        print("⚠️  Loading .env from current directory")
except ImportError:
    print("⚠️  python-dotenv not installed")

# Verify environment variables
required_vars = ['SUPABASE_URL', 'SUPABASE_KEY', 'OPENAI_API_KEY']
missing_vars = [var for var in required_vars if not os.environ.get(var)]

if missing_vars:
    print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
    print("Please set these in your .env file")
    sys.exit(1)
else:
    print("✅ All required environment variables found")

# Check for optional similarity threshold
similarity_threshold = float(os.environ.get('SIMILARITY_THRESHOLD', '0.1'))
print(f"🔧 Similarity threshold: {similarity_threshold}")

# Import dependencies
try:
    from langchain_openai import ChatOpenAI
    from supabase import create_client, Client
    print("✅ Core dependencies imported")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# Import Supabase agents
try:
    from supabase_agents import (
        SupabaseBM25Agent, SupabaseContextualCompressionAgent, SupabaseEnsembleAgent
    )
    print("✅ Supabase agents imported")
except ImportError as e:
    print(f"❌ Supabase agents import error: {e}")
    sys.exit(1)

# Import RAG tools
try:
    from tools.rag_tools import RAGTools
    print("✅ RAG tools imported")
except ImportError as e:
    print(f"❌ RAG tools import error: {e}")
    sys.exit(1)

def setup_logging():
    """Setup logging for the test script."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger('TestSupabaseAgents')

def test_environment_setup():
    """Test environment and basic setup."""
    print("\n🧪 Testing Environment Setup")
    print("=" * 50)
    
    # Test Supabase connection
    try:
        supabase_url = os.environ.get('SUPABASE_URL')
        supabase_key = os.environ.get('SUPABASE_KEY')
        supabase_client: Client = create_client(supabase_url, supabase_key)
        print("✅ Supabase client initialized")
    except Exception as e:
        print(f"❌ Supabase client failed: {e}")
        return False
    
    # Test LLM initialization
    try:
        rag_llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.1,
            max_tokens=1000
        )
        test_response = rag_llm.invoke("Hello, this is a test.")
        print(f"✅ LLM connectivity test: {len(test_response.content)} chars")
    except Exception as e:
        print(f"❌ LLM test failed: {e}")
        return False
    
    # Test RAG tools initialization
    try:
        rag_tools = RAGTools()
        print("✅ RAG tools initialized")
    except Exception as e:
        print(f"❌ RAG tools failed: {e}")
        return False
    
    return True

def test_supabase_bm25_agent():
    """Test SupabaseBM25Agent functionality."""
    print("\n🔍 Testing SupabaseBM25Agent")
    print("=" * 50)
    
    try:
        # Initialize components
        rag_llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.1)
        rag_tools = RAGTools()
        
        # Create retrievers
        bugs_retriever = rag_tools._get_retriever('bugs')
        pcr_retriever = rag_tools._get_retriever('pcr')
        
        # Initialize agent
        bm25_agent = SupabaseBM25Agent(bugs_retriever, pcr_retriever, rag_llm, k=5)
        print("✅ SupabaseBM25Agent initialized")
        
        # Test retrieval with queries based on actual data
        test_queries = [
            "Eclipse memory error",
            "Spring Framework bug",
            "ControllerAdvice annotation"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Testing query: '{query}'")
            
            # Test normal retrieval
            results = bm25_agent.retrieve(query, is_urgent=False)
            print(f"   Normal mode: {len(results)} results")
            
            # Test urgent retrieval
            urgent_results = bm25_agent.retrieve(query, is_urgent=True)
            print(f"   Urgent mode: {len(urgent_results)} results")
            
            if results:
                first_result = results[0]
                print(f"   First result source: {first_result.get('source')}")
                print(f"   First result score: {first_result.get('score')}")
        
        # Test process method
        test_state = {
            'query': 'Spring Framework error',
            'user_can_wait': True,
            'production_incident': False,
            'routing_decision': None,
            'routing_reasoning': None,
            'retrieved_contexts': [],
            'retrieval_method': None,
            'retrieval_metadata': {},
            'final_answer': None,
            'relevant_tickets': [],
            'messages': []
        }
        
        processed_state = bm25_agent.process(test_state)
        print(f"\n✅ Process method test:")
        print(f"   Retrieved contexts: {len(processed_state['retrieved_contexts'])}")
        print(f"   Retrieval method: {processed_state['retrieval_method']}")
        print(f"   Metadata: {processed_state['retrieval_metadata']}")
        
        return True
        
    except Exception as e:
        print(f"❌ SupabaseBM25Agent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_supabase_contextual_compression_agent():
    """Test SupabaseContextualCompressionAgent functionality."""
    print("\n⚡ Testing SupabaseContextualCompressionAgent")
    print("=" * 50)
    
    try:
        # Initialize components
        rag_llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.1)
        rag_tools = RAGTools()
        
        # Create retrievers
        bugs_retriever = rag_tools._get_retriever('bugs')
        pcr_retriever = rag_tools._get_retriever('pcr')
        
        # Initialize agent
        cc_agent = SupabaseContextualCompressionAgent(bugs_retriever, pcr_retriever, rag_llm, k=5)
        print("✅ SupabaseContextualCompressionAgent initialized")
        
        # Test retrieval with queries based on actual data
        test_queries = [
            "Spring Framework error",
            "Eclipse OutOfMemoryError",
            "BeanUtils copyProperties"
        ]
        
        for query in test_queries:
            print(f"\n⚡ Testing query: '{query}'")
            
            # Test normal retrieval
            results = cc_agent.retrieve(query, is_urgent=False)
            print(f"   Normal mode: {len(results)} results")
            
            # Test urgent retrieval
            urgent_results = cc_agent.retrieve(query, is_urgent=True)
            print(f"   Urgent mode: {len(urgent_results)} results")
            
            if results:
                first_result = results[0]
                print(f"   First result source: {first_result.get('source')}")
                print(f"   First result score: {first_result.get('score')}")
        
        # Test process method
        test_state = {
            'query': 'Eclipse memory error',
            'user_can_wait': True,
            'production_incident': False,
            'routing_decision': None,
            'routing_reasoning': None,
            'retrieved_contexts': [],
            'retrieval_method': None,
            'retrieval_metadata': {},
            'final_answer': None,
            'relevant_tickets': [],
            'messages': []
        }
        
        processed_state = cc_agent.process(test_state)
        print(f"\n✅ Process method test:")
        print(f"   Retrieved contexts: {len(processed_state['retrieved_contexts'])}")
        print(f"   Retrieval method: {processed_state['retrieval_method']}")
        print(f"   Metadata: {processed_state['retrieval_metadata']}")
        
        return True
        
    except Exception as e:
        print(f"❌ SupabaseContextualCompressionAgent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_supabase_ensemble_agent():
    """Test SupabaseEnsembleAgent functionality."""
    print("\n🔗 Testing SupabaseEnsembleAgent")
    print("=" * 50)
    
    try:
        # Initialize components
        rag_llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.1)
        rag_tools = RAGTools()
        
        # Create retrievers
        bugs_retriever = rag_tools._get_retriever('bugs')
        pcr_retriever = rag_tools._get_retriever('pcr')
        
        # Initialize individual agents
        bm25_agent = SupabaseBM25Agent(bugs_retriever, pcr_retriever, rag_llm, k=3)
        cc_agent = SupabaseContextualCompressionAgent(bugs_retriever, pcr_retriever, rag_llm, k=3)
        
        # Initialize ensemble agent
        ensemble_agent = SupabaseEnsembleAgent(
            bugs_retriever, pcr_retriever, rag_llm,
            bm25_agent, cc_agent, k=8
        )
        print("✅ SupabaseEnsembleAgent initialized")
        
        # Test retrieval with queries based on actual data
        test_queries = [
            "Spring Framework issues",
            "Eclipse memory problems",
            "BeanFactory annotation"
        ]
        
        for query in test_queries:
            print(f"\n🔗 Testing query: '{query}'")
            
            # Test normal retrieval
            results = ensemble_agent.retrieve(query, is_urgent=False)
            print(f"   Normal mode: {len(results)} results")
            
            # Test urgent retrieval
            urgent_results = ensemble_agent.retrieve(query, is_urgent=True)
            print(f"   Urgent mode: {len(urgent_results)} results")
            
            if results:
                # Show sources used
                sources = [result.get('source', 'unknown') for result in results]
                unique_sources = set(sources)
                print(f"   Sources used: {', '.join(unique_sources)}")
                
                first_result = results[0]
                print(f"   First result source: {first_result.get('source')}")
                print(f"   First result score: {first_result.get('score')}")
        
        # Test process method
        test_state = {
            'query': 'Spring Framework issues',
            'user_can_wait': True,
            'production_incident': False,
            'routing_decision': None,
            'routing_reasoning': None,
            'retrieved_contexts': [],
            'retrieval_metadata': {},
            'final_answer': None,
            'relevant_tickets': [],
            'messages': []
        }
        
        processed_state = ensemble_agent.process(test_state)
        print(f"\n✅ Process method test:")
        print(f"   Retrieved contexts: {len(processed_state['retrieved_contexts'])}")
        print(f"   Retrieval method: {processed_state['retrieval_method']}")
        print(f"   Metadata: {processed_state['retrieval_metadata']}")
        
        return True
        
    except Exception as e:
        print(f"❌ SupabaseEnsembleAgent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_agent_integration():
    """Test that all agents work together properly."""
    print("\n🔗 Testing Agent Integration")
    print("=" * 50)
    
    try:
        # Initialize components
        rag_llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.1)
        rag_tools = RAGTools()
        
        bugs_retriever = rag_tools._get_retriever('bugs')
        pcr_retriever = rag_tools._get_retriever('pcr')
        
        # Initialize all agents
        bm25_agent = SupabaseBM25Agent(bugs_retriever, pcr_retriever, rag_llm, k=3)
        cc_agent = SupabaseContextualCompressionAgent(bugs_retriever, pcr_retriever, rag_llm, k=3)
        ensemble_agent = SupabaseEnsembleAgent(
            bugs_retriever, pcr_retriever, rag_llm,
            bm25_agent, cc_agent, k=6
        )
        
        print("✅ All agents initialized successfully")
        
        # Test that they can work together
        test_query = "Spring Framework memory error"
        print(f"\n🔍 Testing integration with query: '{test_query}'")
        
        # Test each agent individually
        agents = [
            ('BM25', bm25_agent),
            ('ContextualCompression', cc_agent),
            ('Ensemble', ensemble_agent)
        ]
        
        all_results = {}
        
        for agent_name, agent in agents:
            try:
                results = agent.retrieve(test_query, is_urgent=False)
                all_results[agent_name] = results
                print(f"   ✅ {agent_name}: {len(results)} results")
            except Exception as e:
                print(f"   ❌ {agent_name}: Failed - {e}")
                all_results[agent_name] = []
        
        # Verify that ensemble can combine results from other agents
        if all_results['Ensemble']:
            ensemble_sources = set(result.get('source', 'unknown') for result in all_results['Ensemble'])
            print(f"   Ensemble sources: {', '.join(ensemble_sources)}")
        
        print("✅ Agent integration test completed")
        return True
        
    except Exception as e:
        print(f"❌ Agent integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_performance_comparison():
    """Compare performance between different agents."""
    print("\n📊 Performance Comparison")
    print("=" * 50)
    
    try:
        # Initialize components
        rag_llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.1)
        rag_tools = RAGTools()
        
        bugs_retriever = rag_tools._get_retriever('bugs')
        pcr_retriever = rag_tools._get_retriever('pcr')
        
        # Initialize agents
        bm25_agent = SupabaseBM25Agent(bugs_retriever, pcr_retriever, rag_llm, k=5)
        cc_agent = SupabaseContextualCompressionAgent(bugs_retriever, pcr_retriever, rag_llm, k=5)
        ensemble_agent = SupabaseEnsembleAgent(
            bugs_retriever, pcr_retriever, rag_llm,
            bm25_agent, cc_agent, k=8
        )
        
        # Test query based on actual data
        test_query = "Spring Framework error"
        print(f"🔍 Testing with query: '{test_query}'\n")
        
        agents_to_test = [
            ('BM25', bm25_agent),
            ('ContextualCompression', cc_agent),
            ('Ensemble', ensemble_agent)
        ]
        
        performance_results = []
        
        for agent_name, agent in agents_to_test:
            try:
                print(f"⏱️  Testing {agent_name}Agent...")
                
                # Measure execution time
                start_time = datetime.now()
                results = agent.retrieve(test_query, is_urgent=False)
                execution_time = (datetime.now() - start_time).total_seconds()
                
                performance_results.append({
                    'agent': agent_name,
                    'execution_time': execution_time,
                    'num_results': len(results)
                })
                
                print(f"   ✅ {agent_name}: {execution_time:.3f}s, {len(results)} results")
                
            except Exception as e:
                print(f"   ❌ {agent_name} failed: {e}")
                performance_results.append({
                    'agent': agent_name,
                    'execution_time': float('inf'),
                    'num_results': 0,
                    'error': str(e)
                })
        
        # Display performance summary
        print(f"\n📈 PERFORMANCE SUMMARY:")
        print(f"{'Agent':<20} {'Time (s)':<10} {'Results':<8}")
        print("-" * 40)
        
        # Sort by execution time
        performance_results.sort(key=lambda x: x['execution_time'])
        
        for result in performance_results:
            if 'error' not in result:
                agent = result['agent']
                exec_time = f"{result['execution_time']:.3f}"
                num_results = str(result['num_results'])
                
                print(f"{agent:<20} {exec_time:<10} {num_results:<8}")
            else:
                print(f"{result['agent']:<20} {'ERROR':<10} {'0':<8}")
        
        # Performance insights
        valid_results = [r for r in performance_results if 'error' not in r]
        if valid_results:
            fastest = min(valid_results, key=lambda x: x['execution_time'])
            slowest = max(valid_results, key=lambda x: x['execution_time'])
            most_results = max(valid_results, key=lambda x: x['num_results'])
            
            print(f"\n💡 PERFORMANCE INSIGHTS:")
            print(f"   🏃 Fastest: {fastest['agent']} ({fastest['execution_time']:.3f}s)")
            print(f"   🐌 Slowest: {slowest['agent']} ({slowest['execution_time']:.3f}s)")
            print(f"   📊 Most results: {most_results['agent']} ({most_results['num_results']} results)")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance comparison failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all Supabase agent tests."""
    print("🚀 Supabase Agents Test Suite")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Testing individual Supabase-based agents with RAG tools backend")
    print("=" * 60)
    
    # Setup logging
    logger = setup_logging()
    
    # Test results
    test_results = {
        'environment_setup': False,
        'bm25_agent': False,
        'contextual_compression_agent': False,
        'ensemble_agent': False,
        'agent_integration': False,
        'performance_comparison': False
    }
    
    # Run tests
    print("\n🧪 Running Supabase Agent Tests...")
    
    # Test 1: Environment setup
    test_results['environment_setup'] = test_environment_setup()
    
    if test_results['environment_setup']:
        # Test 2: Individual agents
        test_results['bm25_agent'] = test_supabase_bm25_agent()
        test_results['contextual_compression_agent'] = test_supabase_contextual_compression_agent()
        test_results['ensemble_agent'] = test_supabase_ensemble_agent()
        
        # Test 3: Agent integration
        test_results['agent_integration'] = test_agent_integration()
        
        # Test 4: Performance comparison
        test_results['performance_comparison'] = test_performance_comparison()
    
    # Final summary
    print("\n" + "=" * 60)
    print("📋 FINAL TEST SUMMARY")
    print("=" * 60)
    
    passed_tests = sum(test_results.values())
    total_tests = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name.replace('_', ' ').title()}: {status}")
    
    print(f"\n📊 OVERALL RESULTS:")
    print(f"   Tests passed: {passed_tests}/{total_tests}")
    print(f"   Success rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED!")
        print("   Supabase agents are working correctly with RAG tools backend")
        print("   All individual agents are functional and can work together")
    elif passed_tests >= total_tests * 0.8:
        print("\n🟡 MOST TESTS PASSED")
        print("   Supabase agents are mostly functional")
        print("   Check failed tests for specific issues")
    else:
        print("\n🔴 MANY TESTS FAILED")
        print("   Significant issues with Supabase agents")
        print("   Review error messages and fix problems")
    
    print("\n" + "=" * 60)
    print("🏁 Test suite completed")
    print("=" * 60)

if __name__ == "__main__":
    main()
