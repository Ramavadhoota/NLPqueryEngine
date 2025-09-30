# backend/api/routes/query.py - Natural Language Query API Routes

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging
from ..services.query_engine import NaturalLanguageQueryEngine

logger = logging.getLogger(__name__)
router = APIRouter()

class QueryRequest(BaseModel):
    query: str
    database_path: str
    include_documents: bool = True

class QueryResponse(BaseModel):
    success: bool
    query: str
    sql_query: Optional[str] = None
    results: Optional[List[Dict[str, Any]]] = None
    document_results: Optional[List[Dict[str, Any]]] = None
    execution_time: float
    confidence: float
    message: str

@router.post("/execute", response_model=QueryResponse)
async def execute_natural_language_query(request: QueryRequest):
    """Execute natural language query against database and documents."""
    try:
        logger.info(f"🚀 Executing natural language query: {request.query}")
        
        # Initialize query engine
        query_engine = NaturalLanguageQueryEngine(request.database_path)
        
        if not query_engine.connect():
            raise HTTPException(status_code=400, detail="Failed to connect to database")
        
        # Execute the query
        result = await query_engine.execute_query(
            request.query, 
            include_documents=request.include_documents
        )
        
        query_engine.disconnect()
        
        logger.info(f"✅ Query executed successfully in {result.get('execution_time', 0):.2f}s")
        
        return QueryResponse(
            success=True,
            query=request.query,
            sql_query=result.get("sql_query"),
            results=result.get("database_results"),
            document_results=result.get("document_results"),
            execution_time=result.get("execution_time", 0),
            confidence=result.get("confidence", 0),
            message=result.get("message", "Query executed successfully")
        )
        
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")

@router.post("/explain")
async def explain_query(request: QueryRequest):
    """Explain how the natural language query will be processed."""
    try:
        logger.info(f"💡 Explaining query: {request.query}")
        
        query_engine = NaturalLanguageQueryEngine(request.database_path)
        
        if not query_engine.connect():
            raise HTTPException(status_code=400, detail="Failed to connect to database")
        
        explanation = await query_engine.explain_query(request.query)
        query_engine.disconnect()
        
        return {
            "success": True,
            "query": request.query,
            "explanation": explanation
        }
        
    except Exception as e:
        logger.error(f"Query explanation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query explanation failed: {str(e)}")

@router.get("/suggestions")
async def get_query_suggestions(database_path: str):
    """Get sample queries based on database schema."""
    try:
        logger.info(f"💭 Generating query suggestions for database: {database_path}")
        
        query_engine = NaturalLanguageQueryEngine(database_path)
        
        if not query_engine.connect():
            raise HTTPException(status_code=400, detail="Failed to connect to database")
        
        suggestions = await query_engine.generate_query_suggestions()
        query_engine.disconnect()
        
        return {
            "success": True,
            "suggestions": suggestions,
            "total_suggestions": len(suggestions)
        }
        
    except Exception as e:
        logger.error(f"Failed to generate suggestions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate suggestions: {str(e)}")

@router.post("/validate")
async def validate_query(request: QueryRequest):
    """Validate natural language query without executing it."""
    try:
        query_engine = NaturalLanguageQueryEngine(request.database_path)
        
        if not query_engine.connect():
            raise HTTPException(status_code=400, detail="Failed to connect to database")
        
        # Get schema mapping without execution
        mapping = query_engine.schema_discovery.map_natural_language_to_schema(
            request.query, 
            query_engine.schema_info
        )
        
        # Generate SQL without executing
        sql_query = query_engine._generate_sql_query(request.query, mapping)
        
        query_engine.disconnect()
        
        is_valid = sql_query is not None and len(mapping.get("suggested_tables", [])) > 0
        confidence = mapping.get("confidence", 0)
        
        return {
            "success": True,
            "query": request.query,
            "is_valid": is_valid,
            "confidence": confidence,
            "sql_query": sql_query,
            "mapping": mapping,
            "validation_message": f"Query validation complete with {confidence:.1%} confidence"
        }
        
    except Exception as e:
        logger.error(f"Query validation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query validation failed: {str(e)}")

@router.get("/health")
async def query_health():
    """Health check for query processing service."""
    return {
        "status": "healthy", 
        "service": "natural_language_query_engine",
        "capabilities": [
            "Natural language to SQL conversion",
            "Query type classification",
            "Automatic JOIN generation",
            "WHERE condition extraction",
            "Aggregation and ranking queries"
        ]
    }