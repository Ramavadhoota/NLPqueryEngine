# backend/models/__init__.py - Pydantic Models and Schemas

from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime

class DatabaseConnectionRequest(BaseModel):
    database_path: str

class DatabaseConnectionResponse(BaseModel):
    success: bool
    message: str
    schema_info: Optional[Dict[str, Any]] = None

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

class DocumentIngestionResponse(BaseModel):
    success: bool
    message: str
    processed_documents: List[Dict[str, Any]]
    total_chunks: int
    embeddings_generated: int

class QueryMappingRequest(BaseModel):
    query: str
    database_path: str

class ColumnInfo(BaseModel):
    name: str
    type: str
    not_null: bool = False
    default_value: Optional[str] = None
    primary_key: bool = False

class TableInfo(BaseModel):
    columns: List[ColumnInfo]
    primary_keys: List[str]
    foreign_keys: List[Dict[str, Any]]
    sample_data: List[Dict[str, Any]]
    row_count: int
    column_purposes: Dict[str, str]
    purpose: str = "unknown"

class SchemaInfo(BaseModel):
    tables: Dict[str, TableInfo]
    relationships: Dict[str, List[Dict[str, Any]]]
    statistics: Dict[str, Any]
    naming_patterns: Dict[str, Dict]
    database_type: str = "sqlite"

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    details: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    message: str
    model: str
    timestamp: datetime = datetime.now()