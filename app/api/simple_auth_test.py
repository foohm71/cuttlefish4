#!/usr/bin/env python3
"""
Ultra simple auth test - just validates frontend can talk to backend.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Simple Auth Test")

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

@app.get("/health")
async def health():
    return {"status": "ok", "message": "Simple auth test backend running"}

@app.post("/test-auth")
async def test_auth(request: TestRequest):
    return TestResponse(
        message=f"Backend received: {request.message}",
        success=True
    )

if __name__ == "__main__":
    uvicorn.run("app.api.simple_auth_test:app", host="127.0.0.1", port=8000, reload=True)