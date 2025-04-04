import os
import chromadb
import uuid
from chromadb.config import Settings

class ChromaVectorStore:
    """ChromaDB vector store implementation"""
    
    def __init__(self, persist_directory="./storage/chroma"):
        """Initialize ChromaDB vector store"""
        self.persist_directory = persist_directory
        
        # Create storage directory if it doesn't exist
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}
        )
    
    def add_document(self, document, embedding):
        """Add a document to the vector store"""
        # Generate a unique ID for the document
        doc_id = str(uuid.uuid4())
        
        # Extract content and metadata
        content = document.get("content", "")
        metadata = document.get("metadata", {})
        
        # Add the document to ChromaDB
        self.collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            metadatas=[metadata],
            documents=[content]
        )
        
        return True
    
    def similarity_search(self, query, query_embedding, k=5):
        """Search for similar documents"""
        # Get the count to limit k appropriately
        count = self.collection.count()
        if count == 0:
            return []
        
        # Query the collection
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(k, count)
        )
        
        # Format the results
        documents = []
        for i, doc_id in enumerate(results.get("ids", [[]])[0]):
            if i < len(results.get("documents", [[]])[0]) and i < len(results.get("metadatas", [[]])[0]):
                doc = {
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "score": float(results["distances"][0][i]) if "distances" in results else 0.0
                }
                documents.append(doc)
        
        return documents 