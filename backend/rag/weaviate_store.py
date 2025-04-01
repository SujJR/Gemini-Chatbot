import time
import os
import uuid
from typing import List, Dict, Tuple
from langchain.schema import Document

class WeaviateVectorStore:
    def __init__(self, embedding_model=None):
        """Initialize the Weaviate vector store with embedding model"""
        self.embedding_model = embedding_model
        self.vectorstore = None
        self.index_name = "DocumentChunks"
        self.client = None
        self.initialize_client()
    
    def initialize_client(self):
        """Initialize the Weaviate client separately to avoid circular imports"""
        try:
            import weaviate
            from weaviate.auth import AuthApiKey

# Best practice: store your credentials in environment variables
            weaviate_url = "https://j2nw1vfottyzfm4kjp38za.c0.asia-southeast1.gcp.weaviate.cloud"
            weaviate_api_key = "BGrA6MxDawu3vbuxJUdq6VFie7cxDnZgzVHc"
            
            # Or use environment variables (recommended for production)
            # weaviate_url = os.environ.get("WEAVIATE_URL")
            # weaviate_api_key = os.environ.get("WEAVIATE_API_KEY")

# Connect to Weaviate Cloud
            self.client = weaviate.Client(
                url=weaviate_url,
                auth_client_secret=AuthApiKey(api_key=weaviate_api_key)
            )
        
        # Test connection
            self.client.cluster.get_nodes_status()
            
            # Initialize schema if needed
            self._create_schema_if_not_exists()
            
            # Keep Weaviate class reference
            self._Weaviate = weaviate
            
            print("Successfully connected to Weaviate")
            return True
        except Exception as e:
            print(f"Error initializing Weaviate client: {str(e)}")
            self.client = None
            return False
            
    def _create_schema_if_not_exists(self):
        """Create the Weaviate schema if it doesn't exist yet"""
        if self.client is None:
            return
            
        # Check if the class already exists
        try:
            schema = self.client.schema.get()
            classes = [c["class"] for c in schema["classes"]] if "classes" in schema else []
            
            if self.index_name not in classes:
                # Create the class
                class_obj = {
                    "class": self.index_name,
                    "description": "Document chunks for RAG",
                    "vectorizer": "none",  # We use our own embeddings
                    "properties": [
                        {
                            "name": "content",
                            "dataType": ["text"],
                            "description": "The text content of the document chunk",
                        },
                        {
                            "name": "source",
                            "dataType": ["string"],
                            "description": "Source file of the document",
                        },
                        {
                            "name": "page",
                            "dataType": ["int"],
                            "description": "Page number in the source file",
                        }
                    ],
                }
                self.client.schema.create_class(class_obj)
                print(f"Created schema class: {self.index_name}")
        except Exception as e:
            print(f"Error creating Weaviate schema: {str(e)}")
        
    def add_documents(self, documents: List[Document]) -> float:
        """
        Add documents to Weaviate vector store
        
        Args:
            documents: List of documents to add
            
        Returns:
            float: Time taken to add documents
        """
        if self.client is None:
            return 0.0
            
        start_time = time.time()
        
        try:
            # Import here to avoid circular imports
            from langchain_community.vectorstores import Weaviate
            
            # First, delete existing documents with the same index name
            try:
                self.client.batch.delete_objects(
                    class_name=self.index_name,
                    where={
                        "operator": "NotEqual",
                        "operands": [{"path": ["content"], "operator": "Equal", "valueString": ""}],
                    },
                )
            except Exception as e:
                print(f"Error clearing existing documents: {str(e)}")
                
            # Create vectorstore from documents
            self.vectorstore = Weaviate.from_documents(
                documents,
                self.embedding_model,
                client=self.client,
                index_name=self.index_name,
                text_key="content"
            )
            
            end_time = time.time()
            return end_time - start_time
        except Exception as e:
            print(f"Error adding documents to Weaviate: {str(e)}")
            return 0.0
        
    def query(self, query_text: str, top_k: int = 5) -> Tuple[float, List[Document]]:
        """
        Query the Weaviate vector store
        
        Args:
            query_text: Query text
            top_k: Number of results to return
            
        Returns:
            Tuple[float, List[Document]]: Time taken and results
        """
        if self.client is None or self.vectorstore is None:
            return 0.0, []
            
        start_time = time.time()
        
        try:
            # Search for similar documents
            results = self.vectorstore.similarity_search(query_text, k=top_k)
            end_time = time.time()
            return end_time - start_time, results
        except Exception as e:
            print(f"Error querying Weaviate: {str(e)}")
            return 0.0, []