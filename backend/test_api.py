#!/usr/bin/env python3
"""
Minimal test API to verify setup
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": str(datetime.now())}

@app.get("/")
async def root():
    return {"message": "Test API is working"}

if __name__ == "__main__":
    import uvicorn
    print("Starting test API...")
    uvicorn.run(app, host="0.0.0.0", port=8000)