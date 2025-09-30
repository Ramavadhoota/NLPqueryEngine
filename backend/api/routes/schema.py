# backend/api/routes/schema.py - Schema Discovery API Routes

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging
import tempfile
import os
from ..services.schema_discovery import SQLiteSchemaDiscovery

logger = logging.getLogger(__name__)
router = APIRouter()

class DatabaseConnectionRequest(BaseModel):
    database_path: str

class DatabaseConnectionResponse(BaseModel):
    success: bool
    message: str
    schema_info: Optional[Dict[str, Any]] = None

class QueryMappingRequest(BaseModel):
    query: str
    database_path: str

@router.post("/connect", response_model=DatabaseConnectionResponse)
async def connect_database(request: DatabaseConnectionRequest):
    """Connect to SQLite database and analyze schema automatically."""
    try:
        logger.info(f"🔌 Attempting to connect to database: {request.database_path}")
        
        # Initialize schema discovery service
        discovery = SQLiteSchemaDiscovery(request.database_path)
        
        # Test connection
        if not discovery.connect():
            raise HTTPException(status_code=400, detail="Failed to connect to database - check file path")
        
        # Analyze database schema automatically
        schema_info = discovery.analyze_database()
        discovery.disconnect()
        
        logger.info(f"✅ Successfully analyzed database: {len(schema_info['tables'])} tables discovered")
        
        return DatabaseConnectionResponse(
            success=True,
            message=f"Successfully connected and analyzed database with {len(schema_info['tables'])} tables",
            schema_info=schema_info
        )
        
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Database analysis failed: {str(e)}")

@router.post("/upload-db")
async def upload_database(file: UploadFile = File(...)):
    """Upload SQLite database file and analyze schema."""
    try:
        logger.info(f"📤 Uploading database file: {file.filename}")
        
        # Validate file type
        if not file.filename.endswith(('.db', '.sqlite', '.sqlite3')):
            raise HTTPException(status_code=400, detail="Invalid file type. Please upload a SQLite database file (.db, .sqlite, .sqlite3)")
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        # Analyze the uploaded database
        discovery = SQLiteSchemaDiscovery(temp_path)
        
        if not discovery.connect():
            os.unlink(temp_path)  # Clean up temp file
            raise HTTPException(status_code=400, detail="Invalid SQLite database file")
        
        schema_info = discovery.analyze_database()
        discovery.disconnect()
        
        logger.info(f"✅ Successfully analyzed uploaded database: {file.filename}")
        
        return {
            "success": True,
            "message": f"Database '{file.filename}' uploaded and analyzed successfully",
            "schema_info": schema_info,
            "temp_path": temp_path,  # Return path for subsequent operations
            "filename": file.filename
        }
        
    except Exception as e:
        logger.error(f"Database upload failed: {e}")
        # Clean up temp file on error
        if 'temp_path' in locals():
            try:
                os.unlink(temp_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Database upload failed: {str(e)}")

@router.post("/map-query")
async def map_natural_language_query(request: QueryMappingRequest):
    """Map natural language query to database schema - CORE NLP FEATURE."""
    try:
        logger.info(f"🧠 Mapping natural language query: {request.query}")
        
        # Initialize schema discovery service
        discovery = SQLiteSchemaDiscovery(request.database_path)
        
        if not discovery.connect():
            raise HTTPException(status_code=400, detail="Failed to connect to database")
        
        # Get schema info
        schema_info = discovery.analyze_database()
        
        # Map query to schema using NLP
        mapping = discovery.map_natural_language_to_schema(request.query, schema_info)
        
        discovery.disconnect()
        
        logger.info(f"🎯 Query mapped with confidence: {mapping.get('confidence', 0):.2%}")
        
        return {
            "success": True,
            "query": request.query,
            "mapping": mapping,
            "schema_info": schema_info
        }
        
    except Exception as e:
        logger.error(f"Query mapping failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query mapping failed: {str(e)}")

@router.get("/tables/{database_path:path}")
async def get_database_tables(database_path: str):
    """Get list of tables in the database."""
    try:
        discovery = SQLiteSchemaDiscovery(database_path)
        
        if not discovery.connect():
            raise HTTPException(status_code=400, detail="Failed to connect to database")
        
        schema_info = discovery.analyze_database()
        discovery.disconnect()
        
        tables = []
        for table_name, table_info in schema_info.get("tables", {}).items():
            tables.append({
                "name": table_name,
                "purpose": table_info.get("purpose", "unknown"),
                "row_count": table_info.get("row_count", 0),
                "columns": len(table_info.get("columns", []))
            })
        
        return {
            "success": True,
            "tables": tables,
            "total_tables": len(tables)
        }
        
    except Exception as e:
        logger.error(f"Failed to get tables: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get tables: {str(e)}")

@router.get("/health")
async def schema_health():
    """Health check for schema discovery service."""
    return {
        "status": "healthy", 
        "service": "schema_discovery",
        "features": [
            "Automatic table discovery",
            "Column purpose detection", 
            "Relationship analysis",
            "Natural language mapping"
        ]
    }