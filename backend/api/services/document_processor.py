# backend/api/services/document_processor.py - Document Processing with all-MiniLM-L6-v2

import logging
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
import aiofiles
import pandas as pd
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
from PyPDF2 import PdfReader
from docx import Document
import json
import time

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Process and embed various document types using sentence-transformers/all-MiniLM-L6-v2."""
    
    def __init__(self):
        # Initialize the sentence transformer model
        logger.info("🤖 Loading sentence-transformers/all-MiniLM-L6-v2 model...")
        self.embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        self.embedding_dimension = 384
        
        # Initialize FAISS index for vector similarity search
        self.faiss_index = faiss.IndexFlatIP(self.embedding_dimension)  # Inner product similarity
        
        # Storage for document metadata
        self.document_metadata = []
        self.processed_documents = {}
        
        logger.info("✅ Document processor initialized with all-MiniLM-L6-v2 model")
        
    async def process_documents(self, file_paths: List[str]) -> Dict[str, Any]:
        """Process multiple documents with optimal chunking and embedding generation."""
        results = {
            "processed": [],
            "failed": [],
            "total_chunks": 0,
            "embeddings_generated": 0
        }
        
        start_time = time.time()
        
        # Process files concurrently for better performance
        tasks = [self.process_single_document(fp) for fp in file_paths]
        documents_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(documents_results):
            if isinstance(result, Exception):
                results["failed"].append({
                    "file_path": file_paths[i],
                    "error": str(result)
                })
                logger.error(f"Failed to process {file_paths[i]}: {result}")
            else:
                results["processed"].append(result)
                results["total_chunks"] += len(result["chunks"])
                results["embeddings_generated"] += len(result["embeddings"])
                
                # Store in memory for search
                self.processed_documents[result["file_path"]] = result
                
                # Add embeddings to FAISS index
                if result["embeddings"]:
                    embeddings_array = np.array(result["embeddings"], dtype=np.float32)
                    # Normalize for cosine similarity
                    faiss.normalize_L2(embeddings_array)
                    self.faiss_index.add(embeddings_array)
                    
                    # Store metadata for each embedding
                    for j, chunk in enumerate(result["chunks"]):
                        self.document_metadata.append({
                            "file_path": result["file_path"],
                            "file_name": result["file_info"]["name"],
                            "chunk_id": chunk["id"],
                            "chunk_type": chunk["type"],
                            "chunk_content": chunk["content"][:200] + "..." if len(chunk["content"]) > 200 else chunk["content"]
                        })
        
        processing_time = time.time() - start_time
        logger.info(f"✅ Processed {len(results['processed'])} documents in {processing_time:.2f}s")
        
        return results
    
    async def process_single_document(self, file_path: str) -> Dict[str, Any]:
        """Process a single document and return chunks with embeddings."""
        try:
            file_info = await self._analyze_file(file_path)
            
            # Extract text content based on file type
            if file_info["type"] == "pdf":
                content = await self._extract_pdf_content(file_path)
            elif file_info["type"] == "docx":
                content = await self._extract_docx_content(file_path)
            elif file_info["type"] == "txt":
                content = await self._extract_text_content(file_path)
            elif file_info["type"] == "csv":
                content = await self._extract_csv_content(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_info['type']}")
            
            # Apply intelligent chunking
            chunks = self.dynamic_chunking(content, file_info["type"])
            
            # Generate embeddings in batches for efficiency
            embeddings = await self._generate_embeddings_batch(chunks)
            
            return {
                "file_path": file_path,
                "file_info": file_info,
                "content": content[:500] + "..." if len(content) > 500 else content,
                "chunks": chunks,
                "embeddings": embeddings,
                "chunk_count": len(chunks)
            }
            
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {e}")
            raise
    
    async def _analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze file to determine type and characteristics."""
        file_path_obj = Path(file_path)
        
        # Determine file type by extension
        file_extension = file_path_obj.suffix.lower()
        type_mapping = {
            ".pdf": "pdf",
            ".docx": "docx", 
            ".doc": "docx",
            ".txt": "txt",
            ".csv": "csv"
        }
        
        file_type = type_mapping.get(file_extension, "unknown")
        
        return {
            "type": file_type,
            "size": file_path_obj.stat().st_size if file_path_obj.exists() else 0,
            "name": file_path_obj.name,
            "extension": file_extension
        }
    
    async def _extract_pdf_content(self, file_path: str) -> str:
        """Extract text content from PDF file."""
        try:
            reader = PdfReader(file_path)
            content = ""
            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                content += f"[Page {page_num + 1}]\n{page_text}\n\n"
            return content.strip()
        except Exception as e:
            logger.error(f"Error extracting PDF content from {file_path}: {e}")
            raise
    
    async def _extract_docx_content(self, file_path: str) -> str:
        """Extract text content from DOCX file."""
        try:
            doc = Document(file_path)
            content = ""
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    content += paragraph.text + "\n"
            return content.strip()
        except Exception as e:
            logger.error(f"Error extracting DOCX content from {file_path}: {e}")
            raise
    
    async def _extract_text_content(self, file_path: str) -> str:
        """Extract content from plain text file."""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = await f.read()
            return content.strip()
        except Exception as e:
            logger.error(f"Error extracting text content from {file_path}: {e}")
            raise
    
    async def _extract_csv_content(self, file_path: str) -> str:
        """Extract and format CSV content as text."""
        try:
            df = pd.read_csv(file_path)
            content = f"CSV Data: {len(df)} rows, {len(df.columns)} columns\n"
            content += f"Columns: {', '.join(df.columns)}\n\n"
            
            # Add sample rows (limit to prevent huge content)
            sample_size = min(20, len(df))
            for i in range(sample_size):
                row_text = " | ".join([f"{col}: {df.iloc[i][col]}" for col in df.columns])
                content += f"Row {i+1}: {row_text}\n"
            
            if len(df) > sample_size:
                content += f"... and {len(df) - sample_size} more rows"
            
            return content
        except Exception as e:
            logger.error(f"Error extracting CSV content from {file_path}: {e}")
            raise
    
    def dynamic_chunking(self, content: str, doc_type: str) -> List[Dict[str, Any]]:
        """Intelligent chunking based on document structure and type."""
        chunks = []
        
        if doc_type == "pdf":
            chunks = self._chunk_pdf_content(content)
        elif doc_type == "docx":
            chunks = self._chunk_structured_document(content)
        elif doc_type == "txt":
            chunks = self._chunk_plain_text(content)
        elif doc_type == "csv":
            chunks = self._chunk_csv_content(content)
        else:
            chunks = self._chunk_by_sentences(content)
        
        return chunks
    
    def _chunk_pdf_content(self, content: str) -> List[Dict[str, Any]]:
        """Chunk PDF content preserving page boundaries."""
        chunks = []
        pages = content.split("[Page ")
        
        current_chunk = ""
        chunk_id = 0
        max_chunk_size = 800
        
        for page_content in pages[1:]:  # Skip first empty split
            page_text = page_content.split("]\n", 1)
            if len(page_text) > 1:
                page_num = page_text[0]
                page_body = page_text[1]
                
                # If adding this page would exceed max size, create chunk
                if len(current_chunk) + len(page_body) > max_chunk_size and current_chunk:
                    chunks.append({
                        "id": chunk_id,
                        "content": current_chunk.strip(),
                        "type": "pdf_chunk",
                        "size": len(current_chunk.strip())
                    })
                    current_chunk = f"[Page {page_num}] {page_body}"
                    chunk_id += 1
                else:
                    current_chunk += f"\n[Page {page_num}] {page_body}"
        
        # Add final chunk
        if current_chunk:
            chunks.append({
                "id": chunk_id,
                "content": current_chunk.strip(),
                "type": "pdf_chunk",
                "size": len(current_chunk.strip())
            })
        
        return chunks
    
    def _chunk_structured_document(self, content: str) -> List[Dict[str, Any]]:
        """Chunk structured documents preserving paragraph boundaries."""
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        chunks = []
        current_chunk = ""
        chunk_id = 0
        max_chunk_size = 700
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) > max_chunk_size and current_chunk:
                chunks.append({
                    "id": chunk_id,
                    "content": current_chunk.strip(),
                    "type": "paragraph_group",
                    "size": len(current_chunk.strip())
                })
                current_chunk = paragraph
                chunk_id += 1
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph
        
        if current_chunk:
            chunks.append({
                "id": chunk_id,
                "content": current_chunk.strip(),
                "type": "paragraph_group",
                "size": len(current_chunk.strip())
            })
        
        return chunks
    
    def _chunk_plain_text(self, content: str) -> List[Dict[str, Any]]:
        """Chunk plain text maintaining readability."""
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        chunks = []
        current_chunk = ""
        chunk_id = 0
        max_chunk_size = 600
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) > max_chunk_size and current_chunk:
                chunks.append({
                    "id": chunk_id,
                    "content": current_chunk.strip(),
                    "type": "text_chunk",
                    "size": len(current_chunk.strip())
                })
                current_chunk = paragraph
                chunk_id += 1
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph
        
        if current_chunk:
            chunks.append({
                "id": chunk_id,
                "content": current_chunk.strip(),
                "type": "text_chunk",
                "size": len(current_chunk.strip())
            })
        
        return chunks
    
    def _chunk_csv_content(self, content: str) -> List[Dict[str, Any]]:
        """Chunk CSV content by logical groups."""
        lines = content.split('\n')
        chunks = []
        
        # Header chunk
        header_lines = [line for line in lines[:5] if line.strip()]
        if header_lines:
            chunks.append({
                "id": 0,
                "content": "\n".join(header_lines),
                "type": "csv_header",
                "size": len("\n".join(header_lines))
            })
        
        # Data chunks  
        data_lines = [line for line in lines[5:] if line.strip()]
        chunk_id = 1
        rows_per_chunk = 15
        
        for i in range(0, len(data_lines), rows_per_chunk):
            chunk_lines = data_lines[i:i + rows_per_chunk]
            chunk_content = "\n".join(chunk_lines)
            
            chunks.append({
                "id": chunk_id,
                "content": chunk_content,
                "type": "csv_data",
                "size": len(chunk_content)
            })
            chunk_id += 1
        
        return chunks
    
    def _chunk_by_sentences(self, content: str) -> List[Dict[str, Any]]:
        """Fallback chunking method using sentence boundaries."""
        import re
        
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        chunks = []
        current_chunk = ""
        chunk_id = 0
        max_chunk_size = 500
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) > max_chunk_size and current_chunk:
                chunks.append({
                    "id": chunk_id,
                    "content": current_chunk.strip(),
                    "type": "sentence_group",
                    "size": len(current_chunk.strip())
                })
                current_chunk = sentence
                chunk_id += 1
            else:
                current_chunk += ". " + sentence if current_chunk else sentence
        
        if current_chunk:
            chunks.append({
                "id": chunk_id,
                "content": current_chunk.strip(),
                "type": "sentence_group",
                "size": len(current_chunk.strip())
            })
        
        return chunks
    
    async def _generate_embeddings_batch(self, chunks: List[Dict[str, Any]], batch_size: int = 16) -> List[List[float]]:
        """Generate embeddings using all-MiniLM-L6-v2 in batches for efficiency."""
        try:
            texts = [chunk["content"] for chunk in chunks]
            
            if not texts:
                return []
            
            # Generate embeddings in batches using all-MiniLM-L6-v2
            all_embeddings = []
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_embeddings = self.embedding_model.encode(
                    batch_texts,
                    show_progress_bar=False,
                    convert_to_numpy=True
                )
                all_embeddings.extend(batch_embeddings.tolist())
            
            logger.info(f"🤖 Generated {len(all_embeddings)} embeddings using all-MiniLM-L6-v2")
            return all_embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    def search_documents(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search documents using semantic similarity with all-MiniLM-L6-v2."""
        try:
            if self.faiss_index.ntotal == 0:
                logger.warning("No documents indexed for search")
                return []
            
            # Generate query embedding using all-MiniLM-L6-v2
            query_embedding = self.embedding_model.encode([query], convert_to_numpy=True)
            query_embedding = query_embedding.astype(np.float32)
            faiss.normalize_L2(query_embedding)
            
            # Search using FAISS
            similarities, indices = self.faiss_index.search(query_embedding, min(top_k, self.faiss_index.ntotal))
            
            results = []
            for i, (similarity, idx) in enumerate(zip(similarities[0], indices[0])):
                if idx < len(self.document_metadata):
                    metadata = self.document_metadata[idx]
                    results.append({
                        "file_name": metadata["file_name"],
                        "file_path": metadata["file_path"],
                        "chunk_id": metadata["chunk_id"],
                        "chunk_type": metadata["chunk_type"],
                        "chunk_content": metadata["chunk_content"],
                        "similarity": float(similarity),
                        "rank": i + 1
                    })
            
            logger.info(f"🔍 Found {len(results)} similar documents for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get document processing statistics."""
        return {
            "total_documents": len(self.processed_documents),
            "total_chunks": self.faiss_index.ntotal,
            "embedding_dimension": self.embedding_dimension,
            "model_name": "sentence-transformers/all-MiniLM-L6-v2",
            "faiss_index_size": self.faiss_index.ntotal * self.embedding_dimension * 4  # 4 bytes per float32
        }