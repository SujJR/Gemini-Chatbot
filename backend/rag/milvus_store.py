import time
import os
from typing import List, Tuple
from langchain.schema import Document
from pymilvus import (
    connections,
    utility,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
    MilvusException
)

class MilvusVectorStore:
    def __init__(self, embedding_model=None):
        self.embedding_model = embedding_model
        self.initialized = False
        self.collection = None
        
        try:
            # Get Milvus credentials from environment variables
            milvus_uri = os.getenv("MILVUS_URI")
            milvus_user = os.getenv("MILVUS_USER")
            milvus_password = os.getenv("MILVUS_PASSWORD")
            
            # Connect to Milvus cloud
            connections.connect(
                alias="default",
                uri=milvus_uri,
                user=milvus_user,
                password=milvus_password
            )
            
            # Create collection if it doesn't exist
            collection_name = "document_chunks"
            if not utility.has_collection(collection_name):
                # Get embedding dimension from the model
                test_embedding = self.embedding_model.embed_query("test")
                embedding_dim = len(test_embedding)
                
                # Define schema
                fields = [
                    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                    FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
                    FieldSchema(name="metadata", dtype=DataType.JSON),
                    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=embedding_dim)
                ]
                schema = CollectionSchema(fields=fields, description="Document chunks with embeddings")
                
                # Create collection
                self.collection = Collection(name=collection_name, schema=schema)
                
                # Create index
                index_params = {
                    "metric_type": "COSINE",
                    "index_type": "IVF_FLAT",
                    "params": {"nlist": 1024}
                }
                self.collection.create_index(field_name="embedding", index_params=index_params)
            else:
                self.collection = Collection(collection_name)
                # Verify embedding dimension matches
                test_embedding = self.embedding_model.embed_query("test")
                schema = self.collection.schema
                for field in schema.fields:
                    if field.name == "embedding":
                        if field.dim != len(test_embedding):
                            # Drop and recreate collection with correct dimension
                            utility.drop_collection(collection_name)
                            self.__init__(self.embedding_model)
                            return
            
            self.initialized = True
            print("✅ Successfully connected to Milvus")
            
        except MilvusException as e:
            print(f"❌ Milvus error: {str(e)}")
            self.initialized = False
        except Exception as e:
            print(f"❌ Error initializing Milvus: {str(e)}")
            self.initialized = False
    
    def add_documents(self, documents: List[Document]) -> float:
        if not self.initialized:
            print("❌ Cannot add documents: Milvus not initialized")
            return 0.0
            
        start_time = time.time()
        try:
            # Prepare data for insertion
            contents = []
            metadatas = []
            embeddings = []
            
            for doc in documents:
                contents.append(doc.page_content)
                metadatas.append(doc.metadata if doc.metadata else {})
                embeddings.append(self.embedding_model.embed_query(doc.page_content))
            
            # Insert data
            entities = [
                contents,
                metadatas,
                embeddings
            ]
            
            self.collection.insert(entities)
            self.collection.flush()
            
            print(f"✅ Added {len(documents)} documents to Milvus")
            return time.time() - start_time
            
        except Exception as e:
            print(f"❌ Error adding documents to Milvus: {str(e)}")
            return 0.0

    def query(self, query_text: str, top_k: int = 5) -> Tuple[float, List[Document]]:
        if not self.initialized:
            print("❌ Cannot query: Milvus not initialized")
            return 0.0, []
            
        start_time = time.time()
        try:
            # Get query embedding
            query_emb = self.embedding_model.embed_query(query_text)
            
            # Load collection into memory
            self.collection.load()
            
            # Search
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 10}
            }
            
            results = self.collection.search(
                data=[query_emb],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                output_fields=["content", "metadata"]
            )
            
            # Convert results to Document objects
            out_docs = []
            for hits in results:
                for hit in hits:
                    out_docs.append(
                        Document(
                            page_content=hit.entity.get('content'),
                            metadata=hit.entity.get('metadata') if hit.entity.get('metadata') else {}
                        )
                    )
            
            print(f"✅ Found {len(out_docs)} documents in Milvus")
            return time.time() - start_time, out_docs
            
        except Exception as e:
            print(f"❌ Error querying Milvus: {str(e)}")
            return 0.0, []