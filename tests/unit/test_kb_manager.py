"""Unit tests for Knowledge Base Manager."""
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
from src.knowledge.kb_manager import KnowledgeBaseManager


class TestKnowledgeBaseManager:
    """Test Knowledge Base Manager functionality."""
    
    @patch('src.knowledge.kb_manager.chromadb.PersistentClient')
    @patch('src.knowledge.kb_manager.embedding_functions.DefaultEmbeddingFunction')
    def test_init_success(self, mock_embedding_function, mock_chroma_client):
        """Test successful initialization of KnowledgeBaseManager."""
        # Setup mocks
        mock_client = MagicMock()
        mock_chroma_client.return_value = mock_client
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_embedding_func = MagicMock()
        mock_embedding_function.return_value = mock_embedding_func
        
        # Initialize KnowledgeBaseManager
        kb_manager = KnowledgeBaseManager(
            persist_directory="test_db",
            collection_name="test_collection"
        )
        
        # Verify initialization
        assert kb_manager.persist_directory == "test_db"
        assert kb_manager.collection_name == "test_collection"
        assert kb_manager.client == mock_client
        assert kb_manager.collection == mock_collection
        
        # Verify ChromaDB client was created with correct parameters
        mock_chroma_client.assert_called_once_with(path="test_db")
        mock_client.get_or_create_collection.assert_called_once_with(
            name="test_collection",
            embedding_function=mock_embedding_func,
            metadata={"description": "AI OnCall knowledge base documents"}
        )
    
    @patch('src.knowledge.kb_manager.chromadb.PersistentClient')
    @patch('src.knowledge.kb_manager.embedding_functions.DefaultEmbeddingFunction')
    def test_add_document_success(self, mock_embedding_function, mock_chroma_client):
        """Test successful document addition."""
        # Setup mocks
        mock_client = MagicMock()
        mock_chroma_client.return_value = mock_client
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        
        kb_manager = KnowledgeBaseManager()
        
        # Test document addition
        doc_text = "This is a test document about server configuration."
        source = "server-config.md"
        
        with patch('src.knowledge.kb_manager.uuid.uuid4') as mock_uuid:
            mock_uuid.return_value.hex = "test-doc-id"
            
            result_id = kb_manager.add_document(doc_text, source)
            
            # Verify document was added correctly
            assert result_id == str(mock_uuid.return_value)
            mock_collection.add.assert_called_once_with(
                documents=[doc_text],
                metadatas=[{
                    "source": source,
                    "filepath": source
                }],
                ids=[str(mock_uuid.return_value)]
            )
    
    @patch('src.knowledge.kb_manager.chromadb.PersistentClient')
    @patch('src.knowledge.kb_manager.embedding_functions.DefaultEmbeddingFunction')
    def test_add_document_with_filepath(self, mock_embedding_function, mock_chroma_client):
        """Test document addition with custom filepath."""
        # Setup mocks
        mock_client = MagicMock()
        mock_chroma_client.return_value = mock_client
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        
        kb_manager = KnowledgeBaseManager()
        
        # Test document addition with filepath
        doc_text = "Database troubleshooting guide"
        source = "db-guide.md"
        filepath = "/docs/database/db-guide.md"
        
        with patch('src.knowledge.kb_manager.uuid.uuid4') as mock_uuid:
            mock_uuid.return_value.hex = "test-doc-id-2"
            
            result_id = kb_manager.add_document(doc_text, source, filepath)
            
            # Verify document was added with correct metadata
            mock_collection.add.assert_called_once_with(
                documents=[doc_text],
                metadatas=[{
                    "source": source,
                    "filepath": filepath
                }],
                ids=[str(mock_uuid.return_value)]
            )
    
    @patch('src.knowledge.kb_manager.chromadb.PersistentClient')
    @patch('src.knowledge.kb_manager.embedding_functions.DefaultEmbeddingFunction')
    def test_add_document_error(self, mock_embedding_function, mock_chroma_client):
        """Test document addition error handling."""
        # Setup mocks
        mock_client = MagicMock()
        mock_chroma_client.return_value = mock_client
        mock_collection = MagicMock()
        mock_collection.add.side_effect = Exception("ChromaDB error")
        mock_client.get_or_create_collection.return_value = mock_collection
        
        kb_manager = KnowledgeBaseManager()
        
        # Test error handling
        with pytest.raises(Exception, match="ChromaDB error"):
            kb_manager.add_document("test content", "test.md")
    
    @patch('src.knowledge.kb_manager.chromadb.PersistentClient')
    @patch('src.knowledge.kb_manager.embedding_functions.DefaultEmbeddingFunction')
    def test_search_success(self, mock_embedding_function, mock_chroma_client):
        """Test successful knowledge base search."""
        # Setup mocks
        mock_client = MagicMock()
        mock_chroma_client.return_value = mock_client
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        
        # Mock search results
        mock_search_results = {
            "ids": [["doc1", "doc2"]],
            "documents": [["First document content", "Second document content"]],
            "distances": [[0.1, 0.3]],
            "metadatas": [[
                {"source": "doc1.md", "filepath": "/docs/doc1.md"},
                {"source": "doc2.md", "filepath": "/docs/doc2.md"}
            ]]
        }
        mock_collection.query.return_value = mock_search_results
        
        kb_manager = KnowledgeBaseManager()
        
        # Test search
        results = kb_manager.search("server configuration", max_results=2, similarity_threshold=0.5)
        
        # Verify search was called correctly
        mock_collection.query.assert_called_once_with(
            query_texts=["server configuration"],
            n_results=2
        )
        
        # Verify results formatting
        assert len(results) == 2
        
        # Check first result
        assert results[0]["id"] == "doc1"
        assert results[0]["content"] == "First document content"
        assert results[0]["source"] == "doc1.md"
        assert results[0]["filepath"] == "/docs/doc1.md"
        assert results[0]["similarity"] == 0.9  # 1 - 0.1
        assert results[0]["distance"] == 0.1
        
        # Check second result
        assert results[1]["id"] == "doc2"
        assert results[1]["content"] == "Second document content"
        assert results[1]["source"] == "doc2.md"
        assert results[1]["filepath"] == "/docs/doc2.md"
        assert results[1]["similarity"] == 0.7  # 1 - 0.3
        assert results[1]["distance"] == 0.3
    
    @patch('src.knowledge.kb_manager.chromadb.PersistentClient')
    @patch('src.knowledge.kb_manager.embedding_functions.DefaultEmbeddingFunction')
    def test_search_similarity_threshold_filtering(self, mock_embedding_function, mock_chroma_client):
        """Test search results filtering by similarity threshold."""
        # Setup mocks
        mock_client = MagicMock()
        mock_chroma_client.return_value = mock_client
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        
        # Mock search results with varying distances
        mock_search_results = {
            "ids": [["doc1", "doc2", "doc3"]],
            "documents": [["Good match", "Poor match", "Medium match"]],
            "distances": [[0.1, 0.6, 0.4]],  # similarities: 0.9, 0.4, 0.6
            "metadatas": [[
                {"source": "doc1.md"},
                {"source": "doc2.md"},
                {"source": "doc3.md"}
            ]]
        }
        mock_collection.query.return_value = mock_search_results
        
        kb_manager = KnowledgeBaseManager()
        
        # Test search with threshold that filters out poor matches
        results = kb_manager.search("test query", similarity_threshold=0.5)
        
        # Should only return doc1 (0.9) and doc3 (0.6), filtering out doc2 (0.4)
        assert len(results) == 2
        assert results[0]["id"] == "doc1"
        assert results[1]["id"] == "doc3"
    
    @patch('src.knowledge.kb_manager.chromadb.PersistentClient')
    @patch('src.knowledge.kb_manager.embedding_functions.DefaultEmbeddingFunction')
    def test_search_no_results(self, mock_embedding_function, mock_chroma_client):
        """Test search with no matching documents."""
        # Setup mocks
        mock_client = MagicMock()
        mock_chroma_client.return_value = mock_client
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        
        # Mock empty search results
        mock_search_results = {
            "ids": [[]],
            "documents": [[]],
            "distances": [[]],
            "metadatas": [[]]
        }
        mock_collection.query.return_value = mock_search_results
        
        kb_manager = KnowledgeBaseManager()
        
        # Test search with no results
        results = kb_manager.search("nonexistent query")
        
        assert results == []
    
    @patch('src.knowledge.kb_manager.chromadb.PersistentClient')
    @patch('src.knowledge.kb_manager.embedding_functions.DefaultEmbeddingFunction')
    def test_search_error(self, mock_embedding_function, mock_chroma_client):
        """Test search error handling."""
        # Setup mocks
        mock_client = MagicMock()
        mock_chroma_client.return_value = mock_client
        mock_collection = MagicMock()
        mock_collection.query.side_effect = Exception("Search error")
        mock_client.get_or_create_collection.return_value = mock_collection
        
        kb_manager = KnowledgeBaseManager()
        
        # Test error handling
        results = kb_manager.search("test query")
        
        assert results == []
    
    @patch('src.knowledge.kb_manager.chromadb.PersistentClient')
    @patch('src.knowledge.kb_manager.embedding_functions.DefaultEmbeddingFunction')
    def test_get_collection_info_success(self, mock_embedding_function, mock_chroma_client):
        """Test successful collection info retrieval."""
        # Setup mocks
        mock_client = MagicMock()
        mock_chroma_client.return_value = mock_client
        mock_collection = MagicMock()
        mock_collection.count.return_value = 42
        mock_client.get_or_create_collection.return_value = mock_collection
        
        kb_manager = KnowledgeBaseManager(
            persist_directory="test_db",
            collection_name="test_collection"
        )
        
        # Test collection info
        info = kb_manager.get_collection_info()
        
        assert info["name"] == "test_collection"
        assert info["document_count"] == 42
        assert info["persist_directory"] == "test_db"
    
    @patch('src.knowledge.kb_manager.chromadb.PersistentClient')
    @patch('src.knowledge.kb_manager.embedding_functions.DefaultEmbeddingFunction')
    def test_get_collection_info_error(self, mock_embedding_function, mock_chroma_client):
        """Test collection info error handling."""
        # Setup mocks
        mock_client = MagicMock()
        mock_chroma_client.return_value = mock_client
        mock_collection = MagicMock()
        mock_collection.count.side_effect = Exception("Count error")
        mock_client.get_or_create_collection.return_value = mock_collection
        
        kb_manager = KnowledgeBaseManager()
        
        # Test error handling
        info = kb_manager.get_collection_info()
        
        assert info == {}
    
    @patch('src.knowledge.kb_manager.chromadb.PersistentClient')
    @patch('src.knowledge.kb_manager.embedding_functions.DefaultEmbeddingFunction')
    def test_clear_collection_success(self, mock_embedding_function, mock_chroma_client):
        """Test successful collection clearing."""
        # Setup mocks
        mock_client = MagicMock()
        mock_chroma_client.return_value = mock_client
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_embedding_func = MagicMock()
        mock_embedding_function.return_value = mock_embedding_func
        
        kb_manager = KnowledgeBaseManager(collection_name="test_collection")
        
        # Test collection clearing
        kb_manager.clear_collection()
        
        # Verify collection was deleted and recreated
        mock_client.delete_collection.assert_called_once_with(name="test_collection")
        assert mock_client.get_or_create_collection.call_count == 2  # Once in init, once in clear
    
    @patch('src.knowledge.kb_manager.chromadb.PersistentClient')
    @patch('src.knowledge.kb_manager.embedding_functions.DefaultEmbeddingFunction')
    def test_clear_collection_error(self, mock_embedding_function, mock_chroma_client):
        """Test collection clearing error handling."""
        # Setup mocks
        mock_client = MagicMock()
        mock_chroma_client.return_value = mock_client
        mock_client.delete_collection.side_effect = Exception("Delete error")
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        
        kb_manager = KnowledgeBaseManager()
        
        # Test error handling
        with pytest.raises(Exception, match="Delete error"):
            kb_manager.clear_collection()
    
    def test_process_file_success(self):
        """Test successful file processing."""
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as temp_file:
            temp_file.write("# Test Document\nThis is test content.")
            temp_path = Path(temp_file.name)
        
        try:
            # Setup KB manager with mocked ChromaDB
            with patch('src.knowledge.kb_manager.chromadb.PersistentClient'), \
                 patch('src.knowledge.kb_manager.embedding_functions.DefaultEmbeddingFunction'):
                
                kb_manager = KnowledgeBaseManager()
                
                # Mock add_document method
                with patch.object(kb_manager, 'add_document') as mock_add:
                    result = kb_manager._process_file(temp_path)
                    
                    assert result is True
                    mock_add.assert_called_once_with(
                        text="# Test Document\nThis is test content.",
                        source=temp_path.name,
                        filepath=str(temp_path)
                    )
        finally:
            # Clean up
            temp_path.unlink()
    
    def test_process_file_empty_file(self):
        """Test processing of empty file."""
        # Create empty temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        
        try:
            # Setup KB manager with mocked ChromaDB
            with patch('src.knowledge.kb_manager.chromadb.PersistentClient'), \
                 patch('src.knowledge.kb_manager.embedding_functions.DefaultEmbeddingFunction'):
                
                kb_manager = KnowledgeBaseManager()
                
                result = kb_manager._process_file(temp_path)
                
                assert result is False
        finally:
            # Clean up
            temp_path.unlink()
    
    def test_process_file_read_error(self):
        """Test file processing with read error."""
        # Use non-existent file path
        fake_path = Path("/nonexistent/file.md")
        
        # Setup KB manager with mocked ChromaDB
        with patch('src.knowledge.kb_manager.chromadb.PersistentClient'), \
             patch('src.knowledge.kb_manager.embedding_functions.DefaultEmbeddingFunction'):
            
            kb_manager = KnowledgeBaseManager()
            
            result = kb_manager._process_file(fake_path)
            
            assert result is False
    
    def test_bulk_add_from_directory_success(self):
        """Test successful bulk addition from directory."""
        # Create temporary directory with test files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files
            (temp_path / "doc1.md").write_text("Document 1 content")
            (temp_path / "doc2.txt").write_text("Document 2 content") 
            (temp_path / "doc3.py").write_text("# Python file - should be ignored")
            
            # Setup KB manager with mocked ChromaDB
            with patch('src.knowledge.kb_manager.chromadb.PersistentClient'), \
                 patch('src.knowledge.kb_manager.embedding_functions.DefaultEmbeddingFunction'):
                
                kb_manager = KnowledgeBaseManager()
                
                # Mock _process_file to return success
                with patch.object(kb_manager, '_process_file', return_value=True) as mock_process:
                    result = kb_manager.bulk_add_from_directory(str(temp_path))
                    
                    # Should process 2 files (doc1.md and doc2.txt), ignore doc3.py
                    assert result == 2
                    assert mock_process.call_count == 2
    
    def test_bulk_add_from_directory_nonexistent(self):
        """Test bulk addition from non-existent directory."""
        # Setup KB manager with mocked ChromaDB
        with patch('src.knowledge.kb_manager.chromadb.PersistentClient'), \
             patch('src.knowledge.kb_manager.embedding_functions.DefaultEmbeddingFunction'):
            
            kb_manager = KnowledgeBaseManager()
            
            # Test with non-existent directory
            with pytest.raises(ValueError, match="Directory .* not found"):
                kb_manager.bulk_add_from_directory("/nonexistent/directory")
    
    def test_bulk_add_from_directory_recursive(self):
        """Test bulk addition with recursive option."""
        # Create temporary directory with nested structure
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create nested directory
            nested_dir = temp_path / "nested"
            nested_dir.mkdir()
            
            # Create test files
            (temp_path / "root.md").write_text("Root document")
            (nested_dir / "nested.md").write_text("Nested document")
            
            # Setup KB manager with mocked ChromaDB
            with patch('src.knowledge.kb_manager.chromadb.PersistentClient'), \
                 patch('src.knowledge.kb_manager.embedding_functions.DefaultEmbeddingFunction'):
                
                kb_manager = KnowledgeBaseManager()
                
                # Mock _process_file to return success
                with patch.object(kb_manager, '_process_file', return_value=True) as mock_process:
                    # Test non-recursive (should only find root.md)
                    result_non_recursive = kb_manager.bulk_add_from_directory(
                        str(temp_path), recursive=False
                    )
                    assert result_non_recursive == 1
                    
                    # Reset mock
                    mock_process.reset_mock()
                    
                    # Test recursive (should find both files)
                    result_recursive = kb_manager.bulk_add_from_directory(
                        str(temp_path), recursive=True
                    )
                    assert result_recursive == 2 