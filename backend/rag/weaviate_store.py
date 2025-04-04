import time
import os
import json
from typing import List, Tuple
from langchain.schema import Document
import weaviate
from weaviate.util import generate_uuid5

class WeaviateVectorStore:
    def __init__(self, embedding_model=None):
        self.embedding_model = embedding_model
        self.initialized = False
        self.client = None
        
        try:
            # Get Weaviate credentials from environment variables
            weaviate_url = os.getenv("WEAVIATE_URL", "https://test-4x0j0j8h.weaviate.network")
            weaviate_api_key = os.getenv("WEAVIATE_API_KEY", "n6mdfI32xrXF3DH76i8Pdwc4Ijp0CMHTD2A")
            
            print(f"Connecting to Weaviate at {weaviate_url}")
            
            # Initialize Weaviate client with longer timeout
            try:
                self.client = weaviate.Client(
                    url=weaviate_url,
                    auth_client_secret=weaviate.AuthApiKey(api_key=weaviate_api_key),
                    timeout_config=(10, 30)  # (connect_timeout, read_timeout) in seconds
                )
                
                # Test connection
                print("Testing Weaviate connection...")
                self.client.schema.get()
                print("Connection successful!")
                
                # Define the target schema
                target_schema = {
                    "class": "Document",
                    "description": "A document with text content and metadata",
                    "vectorizer": "none",  # We'll provide our own vectors
                    "properties": [
                        {
                            "name": "content",
                            "dataType": ["text"],
                            "description": "The content of the document"
                        },
                        {
                            "name": "metadata",
                            "dataType": ["text"],  # Store metadata as JSON string
                            "description": "Metadata associated with the document (JSON string)"
                        }
                    ]
                }
                
                # Create or update schema if necessary
                if not self.client.schema.exists("Document"):
                    print("Creating Document schema...")
                    self.client.schema.create({"classes": [target_schema]})
                    print("✅ Created schema in Weaviate")
                else:
                    # Optional: Check if existing schema matches and update if needed
                    # current_schema = self.client.schema.get("Document")
                    # if current_schema != target_schema: # Implement more robust comparison if needed
                    #     print("Schema mismatch, attempting update...")
                    #     self.client.schema.update_config("Document", target_schema) # Or delete and recreate
                    print("✅ Document schema already exists")
                
                self.initialized = True
                print("✅ Successfully connected to Weaviate and verified schema")
                
            except Exception as conn_error:
                print(f"❌ Weaviate connection/schema error: {str(conn_error)}")
                self.initialized = False
                # Simplified retry: Just try connecting again, assuming schema issue was transient or fixed externally
                try:
                    print("Retrying basic connection test...")
                    # Re-initialize client without schema creation attempt in retry
                    self.client = weaviate.Client(
                        url=weaviate_url,
                        auth_client_secret=weaviate.AuthApiKey(api_key=weaviate_api_key),
                        timeout_config=(10, 30)
                    )
                    self.client.schema.get() # Simple connection test
                    print("✅ Connection successful on retry, proceeding.")
                    # Assume schema exists or will be handled later if needed
                    self.initialized = True
                except Exception as retry_error:
                     print(f"❌ Weaviate retry failed: {str(retry_error)}")
                     self.initialized = False
                
        except Exception as e:
            print(f"❌ Error initializing Weaviate: {str(e)}")
            self.initialized = False
    
    def add_documents(self, documents: List[Document]) -> float:
        if not self.initialized:
            print("❌ Cannot add documents: Weaviate not initialized")
            return 0.0
            
        start_time = time.time()
        added_count = 0
        try:
            # Use batch processing for better performance
            with self.client.batch as batch:
                batch.batch_size = 20  # Set smaller batch size
                batch.timeout_retries = 3  # Retry on timeout
                
                for doc in documents:
                    try:
                        # Generate embedding
                        embedding = self.embedding_model.embed_query(doc.page_content)
                        
                        # Create document object with JSON stringified metadata
                        doc_obj = {
                            "content": doc.page_content,
                            "metadata": json.dumps(doc.metadata if doc.metadata else {}) # Serialize to JSON string
                        }
                        
                        # Generate a consistent ID based on content
                        doc_id = generate_uuid5(doc.page_content)
                        
                        # Add to batch
                        batch.add_data_object(
                            data_object=doc_obj,
                            class_name="Document",
                            uuid=doc_id,
                            vector=embedding
                        )
                        added_count += 1
                    except Exception as e:
                        print(f"❌ Error adding document (UUID: {doc_id if 'doc_id' in locals() else 'N/A'}) to batch: {str(e)}")
            
            print(f"✅ Attempted to add {len(documents)} documents, successfully processed {added_count} for Weaviate batch.")
            return time.time() - start_time
            
        except Exception as e:
            print(f"❌ Error adding documents to Weaviate: {str(e)}")
            return 0.0

    def query(self, query_text: str, top_k: int = 5) -> Tuple[float, List[Document]]:
        if not self.initialized:
            print("❌ Cannot query: Weaviate not initialized")
            return 0.0, []
            
        start_time = time.time()
        try:
            # Get query embedding
            query_emb = self.embedding_model.embed_query(query_text)
            
            # Perform vector search
            result = (
                self.client.query
                .get("Document", ["content", "metadata"])
                .with_near_vector({
                    "vector": query_emb,
                    "certainty": 0.6  # Lower threshold to get more results
                })
                .with_limit(top_k)
                .do()
            )
            
            # Extract results
            docs = []
            if (result and "data" in result and 
                "Get" in result["data"] and 
                "Document" in result["data"]["Get"]):
                
                for item in result["data"]["Get"]["Document"]:
                    try:
                        # Ensure metadata is properly handled and deserialized
                        metadata_str = item.get("metadata", "{}")
                        # Handle potential None or empty strings explicitly
                        if not metadata_str:
                            metadata_str = "{}"
                        metadata = json.loads(metadata_str)
                    except json.JSONDecodeError:
                        print(f"⚠️ Could not decode metadata JSON: {metadata_str}")
                        metadata = {} # Fallback to empty dict
                    
                    docs.append(
                        Document(
                            page_content=item["content"],
                            metadata=metadata # Use the deserialized dictionary
                        )
                    )
            
            print(f"✅ Found {len(docs)} documents in Weaviate")
            return time.time() - start_time, docs
            
        except Exception as search_error:
            print(f"❌ Error during Weaviate search: {str(search_error)}")
            return time.time() - start_time, []