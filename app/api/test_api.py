#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
Simple test script to verify the Cuttlefish4 API endpoints.
Run this script to test all API functionality.
"""

import requests
import json
import time
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000"
TIMEOUT = 30  # 30 seconds timeout for API calls

def test_health_check() -> bool:
    """Test the health check endpoint."""
    print("🔍 Testing Health Check...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health Check: {data['status']}")
            print(f"   Service: {data['service']}")
            print(f"   Version: {data['version']}")
            return True
        else:
            print(f"❌ Health Check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health Check error: {e}")
        return False

def test_debug_routing() -> bool:
    """Test the debug routing endpoint."""
    print("\n🔍 Testing Debug Routing...")
    
    test_cases = [
        {
            "name": "Production Incident",
            "data": {
                "query": "database connection timeout causing login failures",
                "user_can_wait": False,
                "production_incident": True
            }
        },
        {
            "name": "Comprehensive Analysis",
            "data": {
                "query": "authentication error patterns in recent tickets",
                "user_can_wait": True,
                "production_incident": False
            }
        },
        {
            "name": "Specific Ticket",
            "data": {
                "query": "HBASE-12345 connection timeout issue details",
                "user_can_wait": False,
                "production_incident": False
            }
        }
    ]
    
    success_count = 0
    for test_case in test_cases:
        try:
            print(f"   Testing: {test_case['name']}")
            response = requests.post(
                f"{BASE_URL}/debug/routing",
                json=test_case['data'],
                timeout=TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ {test_case['name']}: {data['routing_decision']}")
                print(f"      Reasoning: {data['routing_reasoning'][:100]}...")
                success_count += 1
            else:
                print(f"   ❌ {test_case['name']}: {response.status_code}")
                print(f"      Error: {response.text}")
                
        except Exception as e:
            print(f"   ❌ {test_case['name']} error: {e}")
    
    return success_count == len(test_cases)

def test_multiagent_rag() -> bool:
    """Test the main multi-agent RAG endpoint."""
    print("\n🔍 Testing Multi-Agent RAG...")
    
    test_cases = [
        {
            "name": "General Query",
            "data": {
                "query": "authentication error in login system",
                "user_can_wait": False,
                "production_incident": False,
                "openai_api_key": None
            }
        }
    ]
    
    success_count = 0
    for test_case in test_cases:
        try:
            print(f"   Testing: {test_case['name']}")
            start_time = time.time()
            
            response = requests.post(
                f"{BASE_URL}/multiagent-rag",
                json=test_case['data'],
                timeout=TIMEOUT
            )
            
            processing_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ {test_case['name']}: {data['routing_decision']}")
                print(f"      Processing time: {processing_time:.2f}s")
                print(f"      Retrieved contexts: {len(data['retrieved_contexts'])}")
                print(f"      Answer length: {len(data['final_answer'])} chars")
                success_count += 1
            else:
                print(f"   ❌ {test_case['name']}: {response.status_code}")
                print(f"      Error: {response.text}")
                
        except Exception as e:
            print(f"   ❌ {test_case['name']} error: {e}")
    
    return success_count == len(test_cases)

def test_interactive_interface() -> bool:
    """Test the interactive test interface."""
    print("\n🔍 Testing Interactive Interface...")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=TIMEOUT)
        if response.status_code == 200:
            print("✅ Interactive Interface: Accessible")
            print(f"   Content length: {len(response.text)} chars")
            return True
        else:
            print(f"❌ Interactive Interface failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Interactive Interface error: {e}")
        return False

def test_api_documentation() -> bool:
    """Test the API documentation endpoints."""
    print("\n🔍 Testing API Documentation...")
    
    endpoints = [
        ("Swagger UI", "/docs"),
        ("ReDoc", "/redoc")
    ]
    
    success_count = 0
    for name, endpoint in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=TIMEOUT)
            if response.status_code == 200:
                print(f"✅ {name}: Accessible")
                success_count += 1
            else:
                print(f"❌ {name}: {response.status_code}")
        except Exception as e:
            print(f"❌ {name} error: {e}")
    
    return success_count == len(endpoints)

def main():
    """Run all API tests."""
    print("🚀 Cuttlefish4 API Test Suite")
    print("=" * 50)
    
    # Check if server is running
    print("🔍 Checking if server is running...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ Server is not responding properly")
            print("   Make sure the server is running on http://localhost:8000")
            return
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server")
        print("   Make sure the server is running on http://localhost:8000")
        print("   Start with: cd app/api && python main.py")
        return
    
    print("✅ Server is running")
    
    # Run tests
    tests = [
        ("Health Check", test_health_check),
        ("Debug Routing", test_debug_routing),
        ("Multi-Agent RAG", test_multiagent_rag),
        ("Interactive Interface", test_interactive_interface),
        ("API Documentation", test_api_documentation)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n📊 Test Results Summary")
    print("=" * 30)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! API is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    # Additional information
    print(f"\n📚 API Documentation:")
    print(f"   Swagger UI: {BASE_URL}/docs")
    print(f"   ReDoc: {BASE_URL}/redoc")
    print(f"   Interactive Test: {BASE_URL}/")
    
    print(f"\n🔧 Next Steps:")
    print(f"   1. Import the Postman collection: Cuttlefish4_API.postman_collection.json")
    print(f"   2. Run the notebook tests: TestAgentWorkflow.ipynb")
    print(f"   3. Check the README.md for detailed usage instructions")

if __name__ == "__main__":
    main()

