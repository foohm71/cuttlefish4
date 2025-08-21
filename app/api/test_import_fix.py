#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
Test script to verify the import fix works correctly.
This simulates what the notebook should do.
"""

import os
import sys
from pathlib import Path

# Setup paths (same as notebook)
current_path = Path.cwd()
app_dir = current_path.parent
project_root = app_dir.parent

print(f"📁 Current Directory: {current_path}")
print(f"📁 App Directory: {app_dir}")
print(f"📁 Project Root: {project_root}")

# Add necessary paths to Python path
for path in [str(project_root), str(app_dir), str(current_path)]:
    if path not in sys.path:
        sys.path.insert(0, path)
        print(f"📎 Added to path: {path}")

print("✅ Python paths configured")

# Load environment variables
try:
    from dotenv import load_dotenv
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(str(env_file))
        print(f"✅ Environment loaded from: {env_file}")
    else:
        load_dotenv()
        print("⚠️  .env file not found in project root, using system environment")
except ImportError:
    print("⚠️  python-dotenv not installed, using system environment variables")

# Test the import fix
print("\n📦 TESTING IMPORT FIX")
print("=" * 50)

try:
    from import_fix import import_workflow, import_models
    print("✅ Import fix loaded")
    
    # Import workflow using the fix
    MultiAgentWorkflow = import_workflow()
    print("✅ MultiAgentWorkflow imported successfully")
    
    # Import models using the fix
    models = import_models()
    print("✅ Models imported successfully")
    
    # Test creating a workflow instance
    print("\n🧪 Testing workflow initialization...")
    workflow = MultiAgentWorkflow()
    print("✅ Workflow instance created successfully")
    
    # Test basic workflow properties
    print(f"   Supervisor LLM: {workflow.supervisor_llm.model_name if hasattr(workflow, 'supervisor_llm') else 'Not found'}")
    print(f"   RAG LLM: {workflow.rag_llm.model_name if hasattr(workflow, 'rag_llm') else 'Not found'}")
    print(f"   Response Writer LLM: {workflow.response_writer_llm.model_name if hasattr(workflow, 'response_writer_llm') else 'Not found'}")
    
    print("\n🎉 All imports and initialization tests passed!")
    
except Exception as e:
    print(f"❌ Import test failed: {e}")
    import traceback
    traceback.print_exc()

