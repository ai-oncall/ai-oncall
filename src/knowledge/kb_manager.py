"""Knowledge Base Manager using ChromaDB for vector search."""
import os
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional

import chromadb
from chromadb.utils import embedding_functions

from src.utils.logging import get_logger

logger = get_logger(__name__)


class KnowledgeBaseManager:
    """Manages ChromaDB operations for knowledge base search."""
    
    def __init__(self, persist_directory: str = "chroma_db", collection_name: str = "knowledge_base"):
        """Initialize ChromaDB client and collection."""
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        
        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Initialize embedding function - using default for simplicity
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
        
        # Create or get the collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_function,
            metadata={"description": "AI OnCall knowledge base documents"}
        )
        
        logger.info("ChromaDB initialized", 
                   persist_directory=persist_directory,
                   collection_name=collection_name)
    
    def add_document(self, text: str, source: str, filepath: Optional[str] = None) -> str:
        """Add a single document to the knowledge base."""
        document_id = str(uuid.uuid4())
        metadata = {
            "source": source,
            "filepath": filepath or source
        }
        
        try:
            self.collection.add(
                documents=[text],
                metadatas=[metadata],
                ids=[document_id]
            )
            
            logger.info("Document added to knowledge base", 
                       document_id=document_id,
                       source=source,
                       content_length=len(text))
            return document_id
            
        except Exception as e:
            logger.error("Failed to add document to knowledge base", 
                        source=source, 
                        error=str(e))
            raise
    
    def bulk_add_from_directory(
        self, 
        directory_path: str,
        extensions: List[str] = [".md", ".txt"],
        recursive: bool = False
    ) -> int:
        """Add all documents from a directory to the knowledge base."""
        directory = Path(directory_path)
        
        if not directory.exists() or not directory.is_dir():
            logger.error("Directory not found", directory_path=directory_path)
            raise ValueError(f"Directory {directory_path} not found or is not a directory")
        
        files_processed = 0
        
        try:
            # Find all matching files
            if recursive:
                pattern = "**/*"
            else:
                pattern = "*"
                
            for filepath in directory.glob(pattern):
                if filepath.is_file() and any(str(filepath).endswith(ext) for ext in extensions):
                    if self._process_file(filepath):
                        files_processed += 1
            
            logger.info("Bulk document processing completed", 
                       directory=directory_path,
                       files_processed=files_processed)
            return files_processed
            
        except Exception as e:
            logger.error("Error during bulk document processing", 
                        directory=directory_path, 
                        error=str(e))
            raise
    
    def _process_file(self, filepath: Path) -> bool:
        """Process a single file and add it to the knowledge base."""
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                content = file.read().strip()
            
            if not content:
                logger.warning("Empty file skipped", filepath=str(filepath))
                return False
            
            # Use filename as source
            source = filepath.name
            
            self.add_document(
                text=content,
                source=source,
                filepath=str(filepath)
            )
            
            return True
            
        except Exception as e:
            logger.error("Error processing file", 
                        filepath=str(filepath), 
                        error=str(e))
            return False
    
    def search(self, query: str, max_results: int = 3, similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Search for similar documents in the knowledge base."""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=max_results
            )
            
            if not results["documents"][0]:
                logger.info("No matching documents found", query=query)
                return []
            
            # Format results
            formatted_results = []
            
            for i, (doc_id, document, distance) in enumerate(zip(
                results["ids"][0],
                results["documents"][0], 
                results["distances"][0]
            )):
                # Convert distance to similarity (lower distance = higher similarity)
                similarity_score = 1 - distance  # Convert distance to similarity
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                
                # Include all results, let the caller decide on filtering
                if similarity_score >= similarity_threshold:
                    formatted_results.append({
                        "id": doc_id,
                        "content": document,
                        "source": metadata.get("source", "Unknown"),
                        "filepath": metadata.get("filepath", ""),
                        "similarity": round(similarity_score, 4),
                        "distance": round(distance, 4)
                    })
            
            logger.info("Knowledge base search completed", 
                       query=query,
                       total_results=len(results["documents"][0]),
                       filtered_results=len(formatted_results),
                       threshold=similarity_threshold)
            
            return formatted_results
            
        except Exception as e:
            logger.error("Error searching knowledge base", 
                        query=query, 
                        error=str(e))
            return []
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the knowledge base collection."""
        try:
            count = self.collection.count()
            return {
                "name": self.collection_name,
                "document_count": count,
                "persist_directory": self.persist_directory
            }
        except Exception as e:
            logger.error("Error getting collection info", error=str(e))
            return {}
    
    def clear_collection(self):
        """Clear all documents from the knowledge base."""
        try:
            # Delete the collection and recreate it
            self.client.delete_collection(name=self.collection_name)
            
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
                metadata={"description": "AI OnCall knowledge base documents"}
            )
            
            logger.info("Knowledge base cleared", collection=self.collection_name)
            
        except Exception as e:
            logger.error("Error clearing knowledge base", error=str(e))
            raise 