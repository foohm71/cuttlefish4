#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
Debug script to test integration components individually.
Run this from the agents directory to diagnose issues.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

print("🔧 INTEGRATION DEBUGGING SCRIPT")
print("=" * 50)

# Setup paths
current_path = Path.cwd()
project_root = current_path.parent.parent
app_dir = project_root / "app"
agents_dir = app_dir / "agents"  
tools_dir = app_dir / "tools"
rag_dir = app_dir / "rag"

# Add to Python path
for path in [str(project_root), str(app_dir), str(agents_dir), str(tools_dir), str(rag_dir)]:
    if path not in sys.path:
        sys.path.insert(0, path)

print(f"📁 Working Directory: {current_path}")
print(f"📁 Project Root: {project_root}")

# Load environment
try:
    from dotenv import load_dotenv
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(str(env_file))
        print("✅ Environment loaded from .env file")
    else:
        load_dotenv()
        print("⚠️  .env file not found, using system environment")
except ImportError:
    print("⚠️  python-dotenv not installed, using system environment variables")
    # We can still proceed if environment variables are set in the system

print("\n" + "=" * 50)
print("TEST 1: LLM CONNECTIVITY")
print("=" * 50)

try:
    from langchain_openai import ChatOpenAI
    
    rag_llm = ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0.1,
        max_tokens=50
    )
    print("✅ LLM object created")
    
    # Test LLM invoke
    print("🔄 Testing LLM invoke...")
    response = rag_llm.invoke("Hello, respond with just 'test successful'")
    print(f"✅ LLM Response: {response}")
    print(f"   Content: {response.content}")
    print(f"   Type: {type(response)}")
    
except Exception as e:
    print(f"❌ LLM test failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 50)
print("TEST 2: VECTORSTORE SEARCH")
print("=" * 50)

try:
    from supabase import create_client
    from supabase_retriever import create_bugs_retriever
    from langchain_core.documents import Document
    
    # Test Supabase retriever directly
    print("🔄 Testing SupabaseRetriever directly...")
    supabase_retriever = create_bugs_retriever()
    print("✅ SupabaseRetriever created")
    
    # Test connection
    connection_test = supabase_retriever.test_connection()
    print(f"✅ Connection test: {connection_test}")
    
    # Test vector search
    print("🔄 Testing vector search...")
    try:
        results = supabase_retriever.vector_search("authentication error", k=2)
        print(f"✅ Vector search results: {len(results)}")
        if results:
            print(f"   First result keys: {list(results[0].keys())}")
            print(f"   Content preview: {results[0].get('content', '')[:100]}...")
    except Exception as vector_error:
        print(f"⚠️  Vector search failed: {vector_error}")
        print("   Trying fallback search...")
        try:
            # Try basic table query as fallback
            from supabase import create_client
            supabase_url = os.environ.get('SUPABASE_URL')
            supabase_key = os.environ.get('SUPABASE_KEY')
            client = create_client(supabase_url, supabase_key)
            basic_result = client.table('bugs').select('*').limit(1).execute()
            print(f"✅ Basic table query: {len(basic_result.data)} records")
        except Exception as fallback_error:
            print(f"❌ Fallback also failed: {fallback_error}")
    
    # Test wrapper functionality
    print("🔄 Testing vectorstore wrapper...")
    
    class TestVectorStoreWrapper:
        def __init__(self, retriever):
            self.retriever = retriever
            
        def similarity_search(self, query, k=4):
            try:
                results = self.retriever.vector_search(query, k=k)
                documents = []
                for result in results:
                    doc = Document(
                        page_content=result.get('content', ''),
                        metadata=result.get('metadata', {})
                    )
                    documents.append(doc)
                return documents
            except Exception as e:
                print(f"⚠️  Similarity search error: {e}")
                # Return mock documents for testing
                return [Document(page_content="Mock document", metadata={"test": True})]
    
    wrapper = TestVectorStoreWrapper(supabase_retriever)
    search_results = wrapper.similarity_search("test query", k=1)
    print(f"✅ Wrapper search: {len(search_results)} documents")
    if search_results:
        print(f"   Document type: {type(search_results[0])}")
        print(f"   Content: {search_results[0].page_content[:50]}...")
    
except Exception as e:
    print(f"❌ Vectorstore test failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 50)
print("TEST 3: AGENT STATE AND NODE FUNCTIONS")
print("=" * 50)

try:
    # Import agent components
    from common import AgentState
    from supervisor_agent import SupervisorAgent
    from langchain_openai import ChatOpenAI
    
    print("✅ Agent imports successful")
    
    # Test AgentState creation
    test_state = {
        'query': 'test integration',
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
    print("✅ AgentState created")
    
    # Test SupervisorAgent
    supervisor_llm = ChatOpenAI(model="gpt-4o", temperature=0.1, max_tokens=100)
    supervisor_agent = SupervisorAgent(supervisor_llm)
    print("✅ SupervisorAgent created")
    
    # Test supervisor processing
    print("🔄 Testing supervisor processing...")
    processed_state = supervisor_agent.process(test_state.copy())
    print(f"✅ Supervisor processing completed")
    print(f"   Routing decision: {processed_state.get('routing_decision')}")
    print(f"   Routing reasoning: {processed_state.get('routing_reasoning')}")
    print(f"   Messages: {len(processed_state.get('messages', []))}")
    
    # Test node function wrapper
    def supervisor_node(state):
        return supervisor_agent.process(state)
    
    print("🔄 Testing node function...")
    node_result = supervisor_node(test_state.copy())
    print(f"✅ Node function executed successfully")
    print(f"   Result type: {type(node_result)}")
    print(f"   Has routing_decision: {'routing_decision' in node_result}")
    
except Exception as e:
    print(f"❌ Agent/Node test failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 50)
print("TEST 4: INTEGRATION SIMULATION")
print("=" * 50)

try:
    print("🔄 Simulating full integration test...")
    
    # Test what the health check is actually testing
    def test_vectorstore_search():
        if 'wrapper' in locals():
            return wrapper.similarity_search("test", k=1)
        return None
    
    def test_llm_connectivity():
        if 'rag_llm' in locals():
            return rag_llm.invoke("test")
        return None
    
    def test_node_function():
        if 'supervisor_node' in locals():
            return supervisor_node({
                'query': 'test integration',
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
            })
        return None
    
    # Run tests
    vectorstore_result = test_vectorstore_search()
    print(f"Vectorstore test result: {type(vectorstore_result)} - {vectorstore_result is not None}")
    
    llm_result = test_llm_connectivity()
    print(f"LLM test result: {type(llm_result)} - {llm_result is not None}")
    
    node_result = test_node_function()
    print(f"Node test result: {type(node_result)} - {node_result is not None}")
    
    if vectorstore_result:
        print(f"   Vectorstore returned: {len(vectorstore_result)} items")
    if llm_result:
        print(f"   LLM returned: {llm_result.content[:50]}...")
    if node_result:
        print(f"   Node returned keys: {list(node_result.keys())}")

except Exception as e:
    print(f"❌ Integration simulation failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 50)
print("SUMMARY")
print("=" * 50)

print("🔍 This script tested:")
print("   1. LLM connectivity and response generation")
print("   2. Supabase retriever and vectorstore wrapper")  
print("   3. Agent state creation and supervisor processing")
print("   4. Node function execution simulation")
print("\n📋 Check the results above to identify which component is failing.")
print("   Look for ❌ errors and ⚠️  warnings to pinpoint issues.")