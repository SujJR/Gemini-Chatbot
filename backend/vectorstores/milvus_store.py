import os
import uuid
from pymilvus import (
    connections,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
    utility
)

class MilvusVectorStore:
    """Milvus vector store implementation"""
    
    def __init__(self, uri="localhost:19530", user=None, password=None, collection_name="documents"):
        """Initialize Milvus vector store"""
        self.initialized = False
        
        try:
            # Check if using cloud or local
            is_cloud = uri and not uri.startswith("localhost")
            
            # Connection parameters
            conn_params = {
                "uri": uri
            }
            
            # Add authentication for Zilliz Cloud
            if is_cloud and user and password:
                conn_params["user"] = user
                conn_params["password"] = password
                conn_params["secure"] = True
                print(f"Using Zilliz Cloud Milvus with authentication: {uri}")
            
            # Connect to Milvus
            connections.connect("default", **conn_params)
            
            # Validate connection
            if not utility.has_collection(collection_name):
                print(f"Collection {collection_name} doesn't exist, creating it")
                self._create_collection(collection_name)
            else:
                self.collection = Collection(collection_name)
                self.collection.load()
            
            self.collection_name = collection_name
            self.initialized = True
            print(f"Successfully connected to Milvus at {uri}")
            
        except Exception as e:
            print(f"Error initializing Milvus: {e}")
            self.initialized = False
    
    def _create_collection(self, collection_name="documents"):
        """Create Milvus collection with schema"""
        # Define fields
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=36),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=255),
            FieldSchema(name="page", dtype=DataType.INT32),
            FieldSchema(name="chunk_id", dtype=DataType.INT32),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=768)  # Adjust dimension as needed
        ]
        
        # Create schema
        schema = CollectionSchema(fields)
        
        # Create collection
        self.collection = Collection(collection_name, schema)
        
        # Create index for vectors
        index_params = {
            "metric_type": "L2",  # L2 distance (Euclidean)
            "index_type": "HNSW",  # Choose appropriate index type
            "params": {"M": 8, "efConstruction": 64}
        }
        self.collection.create_index("embedding", index_params)
        self.collection.load()
    
    def add_document(self, document, embedding):
        """Add a document to the vector store"""
        if not self.initialized:
            return False
        
        try:
            # Extract content and metadata
            content = document.get("content", "")
            metadata = document.get("metadata", {})
            
            # Prepare document data
            doc_id = str(uuid.uuid4())
            
            # Check embedding dimension
            expected_dim = 768  # Should match the schema dimension
            if len(embedding) != expected_dim:
                print(f"Warning: Expected embedding dimension {expected_dim}, got {len(embedding)}")
                # Resize embedding if necessary
                if len(embedding) > expected_dim:
                    embedding = embedding[:expected_dim]
                else:
                    # Pad with zeros
                    embedding = embedding + [0.0] * (expected_dim - len(embedding))
            
            # Insert data
            data = [
                [doc_id],
                [content],
                [metadata.get("source", "")],
                [metadata.get("page", 0)],
                [metadata.get("chunk_id", 0)],
                [embedding]
            ]
            
            # Insert into Milvus
            self.collection.insert(data)
            
            return True
        except Exception as e:
            print(f"Error adding document to Milvus: {e}")
            return False
    
    def similarity_search(self, query, query_embedding, k=5):
        """Search for similar documents using vector similarity"""
        if not self.initialized:
            return []
        
        try:
            # Prepare search parameters
            search_params = {
                "metric_type": "L2",
                "params": {"ef": 64}
            }
            
            # Perform search
            result = self.collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=k,
                output_fields=["content", "source", "page", "chunk_id"]
            )
            
            # Format results
            documents = []
            for hits in result:
                for hit in hits:
                    doc = {
                        "content": hit.entity.get("content", ""),
                        "metadata": {
                            "source": hit.entity.get("source", ""),
                            "page": hit.entity.get("page", 0),
                            "chunk_id": hit.entity.get("chunk_id", 0)
                        },
                        "score": hit.distance
                    }
                    documents.append(doc)
            
            return documents
        except Exception as e:
            print(f"Error searching in Milvus: {e}")
            return [] 