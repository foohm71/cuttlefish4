#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
Startup script for the Cuttlefish4 API server.
This script sets up the proper Python paths before starting the server.
"""

import os
import sys
from pathlib import Path

def setup_environment():
    """Setup the environment for running the API server."""
    
    # Get the current directory (should be app/api)
    current_dir = Path(__file__).parent
    app_dir = current_dir.parent
    project_root = app_dir.parent
    
    print(f"📁 Setting up environment:")
    print(f"   Current Directory: {current_dir}")
    print(f"   App Directory: {app_dir}")
    print(f"   Project Root: {project_root}")
    
    # Add necessary paths to Python path
    paths_to_add = [
        str(project_root),  # Project root
        str(app_dir),       # App directory
        str(current_dir),   # API directory
    ]
    
    for path in paths_to_add:
        if path not in sys.path:
            sys.path.insert(0, path)
            print(f"📎 Added to path: {path}")
    
    # Load environment variables from .env file
    try:
        from dotenv import load_dotenv
        # Try multiple locations for .env file
        env_locations = [
            current_dir / ".env",      # app/api/.env
            app_dir / ".env",          # app/.env
            project_root / ".env",     # project root .env
        ]
        
        env_loaded = False
        for env_file in env_locations:
            if env_file.exists():
                load_dotenv(str(env_file))
                print(f"✅ Environment loaded from: {env_file}")
                env_loaded = True
                break
        
        if not env_loaded:
            load_dotenv()
            print("⚠️  .env file not found, using system environment")
    except ImportError:
        print("⚠️  python-dotenv not installed, using system environment variables")
    
    # Set environment variables
    if 'CUTTLEFISH_HOME' not in os.environ:
        os.environ['CUTTLEFISH_HOME'] = str(project_root)
        print(f"🏠 Set CUTTLEFISH_HOME to: {project_root}")
    
    # Verify required environment variables
    required_vars = ['OPENAI_API_KEY', 'SUPABASE_URL', 'SUPABASE_KEY']
    missing_vars = []
    
    for var in required_vars:
        if os.environ.get(var):
            print(f"✅ {var}: {'*' * 10}...{os.environ.get(var)[-4:]}")
        else:
            missing_vars.append(var)
            print(f"❌ {var}: Missing")
    
    if missing_vars:
        print(f"⚠️  Missing required variables: {', '.join(missing_vars)}")
        print("   The API may not work correctly without these variables")
    else:
        print("✅ All required environment variables found")
    
    print("✅ Environment setup complete")

def main():
    """Start the API server."""
    print("🚀 Starting Cuttlefish4 API Server")
    print("=" * 50)
    
    # Setup environment
    setup_environment()
    
    # Import and run the server
    try:
        import uvicorn
        from main import app
        
        print("✅ Server imported successfully")
        print("🌐 Starting server on http://127.0.0.1:8000")
        print("📚 API Documentation: http://127.0.0.1:8000/docs")
        print("🔧 Interactive Test: http://127.0.0.1:8000/")
        print("=" * 50)
        
        # Start the server
        uvicorn.run(
            "main:app",
            host="127.0.0.1",
            port=8000,
            reload=True,
            log_level="info"
        )
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure all dependencies are installed:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Server startup error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
