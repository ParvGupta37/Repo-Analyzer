"""
Main FastAPI application.
Entry point for the GitHub Repository Analyzer backend.
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
    """Lifecycle manager for application startup and shutdown."""
    # Startup
    print("Initializing database...")
    await init_db()
    print("Database initialized successfully")
    
    # Print Gemini configuration
    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL", "flash")
    
    if api_key:
        model_name = "Gemini 3 Pro" if model.lower() == "pro" else "Gemini 3 Flash"
        print(f"✓ {model_name} configured and ready")
    else:
        print("⚠ Running in mock mode (no GEMINI_API_KEY)")
        print("  Add GEMINI_API_KEY to .env for AI-powered analysis")
    
    print("Application started successfully")
    
    yield
    
    # Shutdown
    print("Application shutting down")


# Create FastAPI app
app = FastAPI(
    title="GitHub Repository Analyzer",
    description="Backend system for analyzing GitHub repositories and helping new contributors",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api", tags=["analysis"])


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "GitHub Repository Analyzer",
        "version": "1.0.0",
        "endpoints": {
            "analyze_repo": "POST /api/analyze-repo",
            "ask_question": "POST /api/ask",
            "health_check": "GET /api/health"
        },
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )