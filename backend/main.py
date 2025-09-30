# backend/main.py - FastAPI Application Entry Point

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
import logging
from contextlib import asynccontextmanager
import os

# Import routes
from api.routes import ingestion, query, schema

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("🚀 NLP Query Engine starting up...")
    # Initialize services here if needed
    yield
    logger.info("🛑 NLP Query Engine shutting down...")

# Create FastAPI application
app = FastAPI(
    title="NLP Query Engine",
    description="AI-powered natural language database query system with sentence-transformers/all-MiniLM-L6-v2",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware - Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(schema.router, prefix="/api/v1/schema", tags=["schema"])
app.include_router(ingestion.router, prefix="/api/v1/ingestion", tags=["ingestion"])
app.include_router(query.router, prefix="/api/v1/query", tags=["query"])

# Serve static files (frontend)
try:
    frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "public")
    if os.path.exists(frontend_path):
        app.mount("/static", StaticFiles(directory=frontend_path), name="static")
except Exception as e:
    logger.warning(f"Could not mount static files: {e}")

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "message": "NLP Query Engine is running",
        "model": "sentence-transformers/all-MiniLM-L6-v2"
    }

@app.get("/")
async def root():
    """Serve frontend or API info"""
    try:
        # Try to serve the frontend HTML
        frontend_file = os.path.join(os.path.dirname(__file__), "..", "frontend", "public", "index.html")
        if os.path.exists(frontend_file):
            with open(frontend_file, "r") as f:
                return HTMLResponse(content=f.read())
    except Exception as e:
        logger.warning(f"Could not serve frontend: {e}")
    
    # Fallback to API info
    return {
        "message": "Welcome to NLP Query Engine API",
        "docs": "/docs",
        "health": "/health",
        "frontend": "Place your frontend files in ../frontend/public/",
        "model": "sentence-transformers/all-MiniLM-L6-v2"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )