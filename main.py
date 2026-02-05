"""
Production FastAPI Application - Final Hardened Version
Features:
- Proper async status flow
- Split table architecture
- Guaranteed persistence
- Single Gemini call per repo
- Zero Gemini calls in /api/ask
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from db.database import init_db
from routes.api import router

# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager with proper database initialization."""
    # Startup
    print("=" * 80)
    print("🚀 GitHub Repository Analyzer - Production")
    print("=" * 80)
    
    print("\n📊 Initializing database...")
    await init_db()
    print("✅ Database initialized successfully")
    
    # Print configuration
    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL", "flash")
    
    print("\n🤖 AI Configuration:")
    if api_key:
        model_name = "Gemini 3 Pro" if model.lower() == "pro" else "Gemini 3 Flash"
        print(f"  ✅ {model_name} configured")
        print(f"  ✅ API Key: {'*' * 20}{api_key[-8:]}")
    else:
        print("  ⚠️  No GEMINI_API_KEY - using mock mode")
        print("  💡 Set GEMINI_API_KEY in .env for AI analysis")
    
    print("\n⚡ Architecture:")
    print("  ✅ Status-based async flow (Option A)")
    print("  ✅ Split table storage (normalized)")
    print("  ✅ Single Gemini call per repository")
    print("  ✅ Zero Gemini calls in /api/ask")
    print("  ✅ Proper SQLite persistence")
    print("  ✅ Idempotent Q&A operations")
    
    print("\n🌐 Endpoints:")
    print("  POST   /api/analyze-repo     - Start analysis")
    print("  GET    /api/status/{id}      - Check status")
    print("  GET    /api/analysis/{id}    - Get results")
    print("  POST   /api/ask              - Ask questions")
    print("  GET    /api/health           - Health check")
    
    print("\n" + "=" * 80)
    print("✅ Application started successfully")
    print("=" * 80 + "\n")
    
    yield
    
    # Shutdown
    print("\n👋 Application shutting down...")


# Create FastAPI app
app = FastAPI(
    title="GitHub Repository Analyzer - Production",
    description="Hardened system with proper async flow and guaranteed persistence",
    version="3.0.0-final",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api", tags=["analysis"])


@app.get("/")
async def root():
    """Root endpoint with system information."""
    return {
        "service": "GitHub Repository Analyzer",
        "version": "3.0.0-final",
        "status": "production",
        "architecture": {
            "async_flow": "status-based (Option A)",
            "storage": "split tables (normalized)",
            "gemini_calls": {
                "per_repository": 1,
                "per_question": 0
            },
            "persistence": "guaranteed (proper session management)"
        },
        "endpoints": {
            "analyze": "POST /api/analyze-repo",
            "status": "GET /api/status/{repo_id}",
            "results": "GET /api/analysis/{repo_id}",
            "ask": "POST /api/ask",
            "health": "GET /api/health"
        },
        "guarantees": [
            "Exactly 1 Gemini call per repository",
            "Zero Gemini calls for questions",
            "Data persists across restarts",
            "Idempotent operations",
            "Proper error handling"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )