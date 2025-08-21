#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
Cuttlefish Multi-Agent RAG Server Launcher

Simple script to start the FastAPI server with proper configuration.
"""

import os
import sys
import uvicorn
from pathlib import Path

# Add the app directory to Python path
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

def main():
    """Launch the FastAPI server."""
    
    # Configuration from environment or defaults
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 8000))
    log_level = os.environ.get("LOG_LEVEL", "info").lower()
    
    # Development vs production mode
    reload = os.environ.get("ENVIRONMENT", "development") == "development"
    
    print("🐙 Starting Cuttlefish Multi-Agent RAG Server")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Log Level: {log_level}")
    print(f"   Reload: {reload}")
    print(f"   API Docs: http://{host}:{port}/docs")
    print(f"   Test Interface: http://{host}:{port}/")
    print()
    
    # Check for required environment variables
    required_vars = ["OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_KEY"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these in your .env file or environment")
        sys.exit(1)
    
    try:
        uvicorn.run(
            "app.api.main:app",
            host=host,
            port=port,
            reload=reload,
            log_level=log_level,
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()