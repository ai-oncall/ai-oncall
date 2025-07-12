"""LangChain-enhanced Knowledge Base Manager with retrieval chains."""
import os
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
import importlib.util

from pydantic import SecretStr
from src.utils.config import config
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Check if all required packages are available
REQUIRED_PACKAGES = [
    "langchain_community.vectorstores",
    "langchain_openai",
    "langchain_core.documents",
    "langchain.text_splitter",
    "langchain_core.prompts",
    "langchain.chains",
    "langchain_core.runnables",
    "langchain_core.output_parsers"
]

def check_package(package: str) -> bool:
    """Check if a package is available."""
    try:
        spec = importlib.util.find_spec(package.split(".")[0])
        return spec is not None
    except ModuleNotFoundError:
        return False

LANGCHAIN_AVAILABLE = all(check_package(pkg) for pkg in REQUIRED_PACKAGES)

if LANGCHAIN_AVAILABLE:
    from langchain_community.vectorstores import Chroma
    from langchain_openai import OpenAIEmbeddings, ChatOpenAI
    from langchain_core.documents import Document
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_core.prompts import ChatPromptTemplate
    from langchain.chains import RetrievalQA
    from langchain_core.runnables import RunnablePassthrough
    from langchain_core.output_parsers import StrOutputParser
else:
    logger.warning(
        "LangChain dependencies not available. Please ensure all required packages are installed: "
        + ", ".join(REQUIRED_PACKAGES)
    )


class LangChainKnowledgeManager:
    """Enhanced Knowledge Base Manager using LangChain's retrieval chains."""
    
    def __init__(self, persist_directory: str = "chroma_db", collection_name: str = "langchain_knowledge"):
        """Initialize LangChain-based knowledge manager."""
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        
        if not LANGCHAIN_AVAILABLE:
            error_msg = (
                "LangChain components not available. Please install required packages: "
                + ", ".join(REQUIRED_PACKAGES)
            )
            logger.error(error_msg)
            raise ImportError(error_msg)
        
        self._setup_langchain_components()

    def _setup_langchain_components(self):
        """Setup LangChain components for enhanced retrieval."""
        try:
            # Initialize embeddings with proper error handling
            if not config.openai_api_key:
                raise ValueError("OpenAI API key not configured")
            
            self.embeddings = OpenAIEmbeddings(
                api_key=SecretStr(config.openai_api_key),
                base_url=config.openai_base_url if config.openai_base_url else None
            )
            
            # Initialize vector store
            self.vectorstore = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory
            )
            
            # Initialize text splitter for document processing
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len,
                separators=["\n\n", "\n", " ", ""]
            )
            
            # Setup retrieval chain
            self._setup_retrieval_chain()
            
            # Verify required components
            if not self.embeddings:
                raise RuntimeError("Embeddings initialization failed")
            if not self.vectorstore:
                raise RuntimeError("Vector store initialization failed")
            if not self.text_splitter:
                raise RuntimeError("Text splitter initialization failed")
            if not hasattr(self, 'retrieval_chain'):
                raise RuntimeError("Retrieval chain setup failed")
                
            logger.info(
                "LangChain Knowledge Manager initialized successfully",
                persist_directory=self.persist_directory,
                collection_name=self.collection_name,
                components={
                    "embeddings": self.embeddings.__class__.__name__,
                    "vectorstore": self.vectorstore.__class__.__name__,
                    "text_splitter": self.text_splitter.__class__.__name__
                }
            )
            
        except Exception as e:
            error_msg = f"Failed to initialize LangChain components: {str(e)}"
            logger.error(
                error_msg,
                error_type=e.__class__.__name__,
                persist_directory=self.persist_directory,
                collection_name=self.collection_name
            )
            raise RuntimeError(error_msg) from e

    def _setup_retrieval_chain(self):
        """Setup the retrieval QA chain."""
        try:
            # Initialize retriever with defaults if not configured
            retriever = self.vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 3}
            )
            
            # Create prompt template for combining context and query
            prompt_template = """Answer the question based only on the following context:
            {context}
            
            Question: {query}
            
            Answer:"""
            prompt = ChatPromptTemplate.from_template(prompt_template)
            
            # Initialize LLM with appropriate config
            llm = ChatOpenAI(
                model=config.openai_model or "gpt-4-turbo-preview",
                api_key=SecretStr(config.openai_api_key),
                base_url=config.openai_base_url if config.openai_base_url else None,
                temperature=0
            )
            
            # Format documents for the prompt
            format_docs = lambda docs: "\n\n".join(doc.page_content for doc in docs)
            
            # Create and verify the retrieval chain
            self.retrieval_chain = (
                {"context": retriever | format_docs, "query": RunnablePassthrough()}
                | prompt
                | llm
                | StrOutputParser()
            )
            
            # Test that the chain is callable
            if not hasattr(self.retrieval_chain, 'invoke') and not hasattr(self.retrieval_chain, '__call__'):
                raise RuntimeError("Retrieval chain is not properly constructed")
            
            logger.info("Retrieval chain setup completed successfully")
            
        except Exception as e:
            error_msg = f"Failed to setup retrieval chain: {str(e)}"
            logger.error(error_msg)
            self.retrieval_chain = None  # Ensure field exists even if setup fails
            raise RuntimeError(error_msg) from e
    
    def _format_docs(self, docs):
        """Format documents for the prompt."""
        formatted_docs = []
        for doc in docs:
            source = doc.metadata.get('source', 'Unknown')
            content = doc.page_content
            formatted_docs.append(f"Source: {source}\nContent: {content}")
            
            # Log each retrieved document
            logger.info("Retrieved document from knowledge base",
                       source=source,
                       content_preview=content[:100] + "..." if len(content) > 100 else content,
                       metadata=doc.metadata)
        
        formatted_context = "\n\n".join(formatted_docs)
        
        # Log the complete context being sent to LLM
        logger.info("Sending context to LLM",
                   context_length=len(formatted_context),
                   num_docs=len(docs),
                   sources=[doc.metadata.get('source', 'Unknown') for doc in docs])
        
        return formatted_context
    
    def add_document(self, text: str, source: str, filepath: Optional[str] = None) -> str:
        """Add a single document to the knowledge base."""
        document_id = str(uuid.uuid4())
        try:
            # Process text with text splitter
            chunks = self.text_splitter.split_text(text)
            
            # Add metadata to each chunk
            docs = []
            for i, chunk in enumerate(chunks):
                doc = Document(
                    page_content=chunk,
                    metadata={
                        "source": source,
                        "filepath": filepath or source,
                        "chunk_id": i,
                        "document_id": document_id
                    }
                )
                docs.append(doc)
            
            # Add to vector store
            self.vectorstore.add_documents(docs)
            
            logger.info(
                "Document added successfully",
                document_id=document_id,
                source=source,
                num_chunks=len(chunks)
            )
            
            return document_id
            
        except Exception as e:
            logger.error(
                "Failed to add document",
                error=str(e),
                source=source,
                document_id=document_id
            )
            raise

    def bulk_add_from_directory(
        self, 
        directory_path: str,
        extensions: List[str] = [".md", ".txt"],
        recursive: bool = False
    ) -> int:
        """Add all documents from a directory to the knowledge base."""
        if not os.path.exists(directory_path):
            logger.error("Directory does not exist", directory_path=directory_path)
            raise FileNotFoundError(f"Directory not found: {directory_path}")
        
        base_path = Path(directory_path)
        pattern = "**/*" if recursive else "*"
        
        processed_count = 0
        failed_count = 0
        
        for ext in extensions:
            for filepath in base_path.glob(pattern + ext):
                if self._process_file(filepath):
                    processed_count += 1
                else:
                    failed_count += 1
        
        logger.info(
            "Bulk import completed",
            directory=directory_path,
            processed=processed_count,
            failed=failed_count
        )
        
        return processed_count

    def _process_file(self, filepath: Path) -> bool:
        """Process a single file and add it to the knowledge base."""
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                content = file.read().strip()
            
            if not content:
                logger.warning("Empty file skipped", filepath=str(filepath))
                return False
            
            self.add_document(
                text=content,
                source=filepath.name,
                filepath=str(filepath)
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Error processing file",
                filepath=str(filepath),
                error=str(e)
            )
            return False

    async def search_with_chain(self, query: str, max_results: int = 3) -> str:
        """Use the retrieval chain to search for relevant information."""
        try:
            if not self.retrieval_chain:
                raise RuntimeError("Retrieval chain not initialized")
                
            # Use ainvoke for async operation
            response = await self.retrieval_chain.ainvoke(query)
            
            if not response:
                logger.warning("No results found in knowledge base", query=query)
                return "No relevant information found in the knowledge base."
            
            logger.info(
                "Search completed successfully",
                query=query,
                response_length=len(str(response))
            )
            
            return response
            
        except Exception as e:
            error_msg = f"Error during chain-based search: {str(e)}"
            logger.error(
                error_msg,
                error=str(e),
                query=query
            )
            # Return a user-friendly error message
            return "📚 **Error searching knowledge base.** Please contact support for assistance."

    def search(self, query: str, max_results: int = 3, similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Traditional search method for backward compatibility."""
        try:
            docs_and_scores = self.vectorstore.similarity_search_with_score(
                query, k=max_results
            )
            
            results = []
            for doc, score in docs_and_scores:
                if score >= similarity_threshold:
                    results.append({
                        "content": doc.page_content,
                        "source": doc.metadata.get("source", "unknown"),
                        "filepath": doc.metadata.get("filepath"),
                        "similarity": score
                    })
            
            logger.info(
                "Traditional search completed",
                query=query,
                results_count=len(results),
                similarity_threshold=similarity_threshold
            )
            
            return results
            
        except Exception as e:
            logger.error(
                "Error during traditional search",
                error=str(e),
                query=query
            )
            raise

    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the knowledge base collection."""
        try:
            # Get collection stats
            collection = self.vectorstore._collection
            count = collection.count()
            
            return {
                "document_count": count,
                "collection_name": self.collection_name,
                "persist_directory": self.persist_directory
            }
            
        except Exception as e:
            logger.error(
                "Error getting collection info",
                error=str(e)
            )
            raise

    def clear_collection(self):
        """Clear all documents from the knowledge base."""
        try:
            self.vectorstore.delete_collection()
            self.vectorstore = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory
            )
            
            logger.info(
                "Knowledge base collection cleared",
                collection_name=self.collection_name
            )
            
        except Exception as e:
            logger.error(
                "Error clearing collection",
                error=str(e)
            )
            raise
