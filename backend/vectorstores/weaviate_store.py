import os
import uuid
import weaviate
from weaviate.auth import AuthApiKey
from weaviate.util import get_valid_uuid

class WeaviateVectorStore:
    """Weaviate vector store implementation"""
    
    def __init__(self, url="http://localhost:8080", api_key=None):
        """Initialize Weaviate vector store"""
        try:
            # Configure authentication if API key is provided (for cloud instances)
            auth_config = None
            if api_key:
                auth_config = AuthApiKey(api_key=api_key)
                print(f"Using Weaviate with API key authentication")
            
            # Initialize client with auth if needed
            self.client = weaviate.Client(
                url=url,
                auth_client_secret=auth_config,
                additional_headers={
                    "X-OpenAI-Api-Key": os.environ.get("OPENAI_API_KEY")  # If using OpenAI modules
                }
            )
            
            # Verify connection
            if not self.client.is_ready():
                raise Exception("Weaviate server is not ready")
            
            # Check if class exists, create it if not
            if not self.client.schema.exists("Document"):
                class_obj = {
                    "class": "Document",
                    "vectorizer": "none",  # We'll provide our own vectors
                    "properties": [
                        {
                            "name": "content",
                            "dataType": ["text"]
                        },
                        {
                            "name": "source",
                            "dataType": ["string"]
                        },
                        {
                            "name": "page",
                            "dataType": ["int"]
                        },
                        {
                            "name": "chunkId",
                            "dataType": ["int"]
                        }
                    ]
                }
                self.client.schema.create_class(class_obj)
        except Exception as e:
            print(f"Error initializing Weaviate: {e}")
            # Create a dummy client for fault tolerance
            self.client = None
    
    def add_document(self, document, embedding):
        """Add a document to the vector store"""
        if self.client is None:
            return False
        
        try:
            # Extract content and metadata
            content = document.get("content", "")
            metadata = document.get("metadata", {})
            
            # Create a UUID based on the content
            doc_uuid = get_valid_uuid(str(uuid.uuid4()))
            
            # Prepare properties
            properties = {
                "content": content,
                "source": metadata.get("source", ""),
                "page": metadata.get("page", 0),
                "chunkId": metadata.get("chunk_id", 0)
            }
            
            # Add the document to Weaviate
            self.client.data_object.create(
                data_object=properties,
                class_name="Document",
                uuid=doc_uuid,
                vector=embedding
            )
            
            return True
        except Exception as e:
            print(f"Error adding document to Weaviate: {e}")
            return False
    
    def similarity_search(self, query, query_embedding, k=5):
        """Search for similar documents"""
        if self.client is None:
            return []
        
        try:
            result = (
                self.client.query
                .get("Document", ["content", "source", "page", "chunkId"])
                .with_near_vector({"vector": query_embedding})
                .with_limit(k)
                .do()
            )
            
            # Format results
            documents = []
            if "data" in result and "Get" in result["data"] and "Document" in result["data"]["Get"]:
                for item in result["data"]["Get"]["Document"]:
                    doc = {
                        "content": item.get("content", ""),
                        "metadata": {
                            "source": item.get("source", ""),
                            "page": item.get("page", 0),
                            "chunk_id": item.get("chunkId", 0)
                        },
                        "score": item.get("_additional", {}).get("distance", 0.0)
                    }
                    documents.append(doc)
            
            return documents
        except Exception as e:
            print(f"Error searching in Weaviate: {e}")
            return [] 