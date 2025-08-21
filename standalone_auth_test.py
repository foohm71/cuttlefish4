#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
Standalone auth test server - no imports from app package.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Standalone Auth Test")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TestRequest(BaseModel):
    message: str

class TestResponse(BaseModel):
    message: str
    success: bool
    user: str = "foohm71@gmail.com"

@app.get("/health")
async def health():
    return {"status": "ok", "message": "Standalone auth test backend running"}

@app.post("/test-auth")
async def test_auth(request: TestRequest):
    return TestResponse(
        message=f"✅ Auth test successful! Backend received: '{request.message}'",
        success=True,
        user="foohm71@gmail.com"
    )

if __name__ == "__main__":
    print("🚀 Starting standalone auth test server...")
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)