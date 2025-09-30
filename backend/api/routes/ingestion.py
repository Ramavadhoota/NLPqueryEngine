# backend/api/routes/ingestion.py - Document Ingestion API Routes

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging
import tempfile
import os
import aiofiles
from ..services.document_processor import DocumentProcessor

logger = logging.getLogger(__name__)
router = APIRouter()

# Global document processor instance (in production, use dependency injection)
document_processor = DocumentProcessor()

class DocumentIngestionResponse(BaseModel):
    success: bool
    message: str
    processed_documents: List[Dict[str, Any]]
    total_chunks: int
    embeddings_generated: int

@router.post("/upload-documents", response_model=DocumentIngestionResponse)
async def upload_documents(files: List[UploadFile] = File(...)):
    """Upload and process multiple documents using sentence-transformers/all-MiniLM-L6-v2."""
    try:
        logger.info(f"📤 Uploading {len(files)} documents for processing")
        
        # Validate file types
        allowed_extensions = {'.pdf', '.docx', '.txt', '.csv'}
        temp_files = []
        
        for file in files:
            if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid file type for '{file.filename}'. Allowed: PDF, DOCX, TXT, CSV"
                )
        
        # Save files temporarily
        for file in files:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1])
            content = await file.read()
            temp_file.write(content)
            temp_file.close()
            temp_files.append((temp_file.name, file.filename))
        
        logger.info(f"🤖 Processing documents with all-MiniLM-L6-v2 model...")
        
        # Process documents using DocumentProcessor
        file_paths = [temp_path for temp_path, _ in temp_files]
        results = await document_processor.process_documents(file_paths)
        
        # Clean up temporary files
        for temp_path, _ in temp_files:
            try:
                os.unlink(temp_path)
            except:
                pass
        
        logger.info(f"✅ Successfully processed {len(results['processed'])} documents")
        
        return DocumentIngestionResponse(
            success=True,
            message=f"Successfully processed {len(results['processed'])} documents with {results['embeddings_generated']} embeddings",
            processed_documents=results['processed'],
            total_chunks=results['total_chunks'],
            embeddings_generated=results['embeddings_generated']
        )
        
    except Exception as e:
        logger.error(f"Document ingestion failed: {e}")
        # Clean up temp files on error
        for temp_path, _ in temp_files:
            try:
                os.unlink(temp_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Document ingestion failed: {str(e)}")

@router.post("/search-documents")
async def search_documents(
    query: str = Form(...),
    top_k: int = Form(5)
):
    """Search uploaded documents using semantic similarity with all-MiniLM-L6-v2."""
    try:
        logger.info(f"🔍 Searching documents for query: {query}")
        
        # Search using document processor
        results = document_processor.search_documents(query, top_k)
        
        logger.info(f"📊 Found {len(results)} relevant document chunks")
        
        return {
            "success": True,
            "query": query,
            "results": results,
            "total_results": len(results),
            "model_used": "sentence-transformers/all-MiniLM-L6-v2"
        }
        
    except Exception as e:
        logger.error(f"Document search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Document search failed: {str(e)}")

@router.post("/search-documents-json")
async def search_documents_json(request: dict):
    """Search documents with JSON request body."""
    try:
        query = request.get("query")
        top_k = request.get("top_k", 5)
        
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        results = document_processor.search_documents(query, top_k)
        
        return {
            "success": True,
            "query": query,
            "results": results,
            "total_results": len(results),
            "model_used": "sentence-transformers/all-MiniLM-L6-v2"
        }
        
    except Exception as e:
        logger.error(f"Document search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Document search failed: {str(e)}")

@router.delete("/clear-documents")
async def clear_uploaded_documents():
    """Clear all uploaded documents from the system."""
    try:
        # Reset document processor
        global document_processor
        document_processor = DocumentProcessor()
        
        logger.info("🧹 Cleared all uploaded documents")
        
        return {
            "success": True,
            "message": "All documents cleared successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to clear documents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear documents: {str(e)}")

@router.get("/document-status")
async def get_document_status():
    """Get status of uploaded documents and embeddings."""
    try:
        stats = document_processor.get_stats()
        
        return {
            "success": True,
            "status": {
                "total_documents": stats["total_documents"],
                "total_chunks": stats["total_chunks"], 
                "embedding_dimension": stats["embedding_dimension"],
                "model_name": stats["model_name"],
                "faiss_index_size_bytes": stats.get("faiss_index_size", 0)
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get document status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get document status: {str(e)}")

@router.get("/supported-formats")
async def get_supported_formats():
    """Get list of supported document formats."""
    return {
        "success": True,
        "supported_formats": [
            {
                "extension": ".pdf",
                "description": "PDF documents with text extraction"
            },
            {
                "extension": ".docx", 
                "description": "Microsoft Word documents"
            },
            {
                "extension": ".txt",
                "description": "Plain text files"
            },
            {
                "extension": ".csv",
                "description": "Comma-separated value files"
            }
        ],
        "max_file_size": "10MB",
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2"
    }

@router.get("/health")
async def ingestion_health():
    """Health check for document ingestion service."""
    stats = document_processor.get_stats()
    
    return {
        "status": "healthy", 
        "service": "document_ingestion",
        "model": stats["model_name"],
        "embedding_dimension": stats["embedding_dimension"],
        "documents_loaded": stats["total_documents"],
        "chunks_indexed": stats["total_chunks"]
    }