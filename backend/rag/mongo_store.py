import time
import os
from typing import List, Tuple
from langchain.schema import Document
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, OperationFailure, ConfigurationError
import numpy as np

class MongoVectorStore:
    def __init__(self, embedding_model=None):
        self.embedding_model = embedding_model
        self.initialized = False
        self.client = None
        self.db = None
        self.collection = None
        self.vector_search_available = False
        self.embedding_dim = 768  # Default dimension
        
        try:
            # Get embedding dimension from model if available
            if embedding_model:
                test_embedding = self.embedding_model.embed_query("test")
                self.embedding_dim = len(test_embedding)
                print(f"✅ Detected embedding dimension: {self.embedding_dim}")
            
            # Get MongoDB credentials from environment variables
            mongo_user = os.getenv("MONGO_USER")
            mongo_password = os.getenv("MONGO_PASSWORD")
            mongo_cluster = os.getenv("MONGO_CLUSTER")
            
            # Construct the connection string
            self.mongo_url = f"mongodb+srv://{mongo_user}:{mongo_password}@{mongo_cluster}.z8hiz.mongodb.net/?retryWrites=true&w=majority"
            
            # Connect to MongoDB with proper error handling
            try:
                self.client = MongoClient(
                    self.mongo_url, 
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=5000,
                    socketTimeoutMS=10000
                )
                # Test the connection
                self.client.admin.command('ping')
                print("✅ Successfully connected to MongoDB")
                
                # Initialize database and collection
                self.db = self.client["my_vector_database"]
                self.collection = self.db["my_vector_collection"]
                
                # Try to create a standard index on content for text search fallback
                try:
                    self.collection.create_index("content")
                    print("✅ Created index on content field")
                except Exception as e:
                    print(f"⚠️ Note: Could not create content index: {str(e)}")
                
                # Try to create vector search index if available
                try:
                    # Check if Atlas Vector Search is available by attempting to create an index
                    index_model = [("embedding", "vector")]
                    
                    self.collection.create_index(
                        index_model,
                        name="vector_index",
                    )
                    
                    # If it reaches here, basic vector index created - try to use Atlas Search
                    # This will be used by the manual similarity search method
                    print("✅ Created basic vector index")
                    self.vector_search_available = False
                    
                except Exception as vector_index_error:
                    print(f"ℹ️ Basic vector index not supported: {str(vector_index_error)}")
                    print("⚠️ Will use manual vector similarity search")
                    self.vector_search_available = False
                
                self.initialized = True
                
            except ServerSelectionTimeoutError as e:
                print(f"❌ MongoDB connection timeout: {str(e)}")
                self.initialized = False
            except (OperationFailure, ConfigurationError) as e:
                print(f"❌ MongoDB operation/config error: {str(e)}")
                self.initialized = False
                
        except Exception as e:
            print(f"❌ Error initializing MongoDB: {str(e)}")
            self.initialized = False
    
    def add_documents(self, documents: List[Document]) -> float:
        if not self.initialized:
            print("❌ Cannot add documents: MongoDB not initialized")
            return 0.0
            
        start_time = time.time()
        try:
            # Store content and embeddings in batches
            batch_size = 50
            total_docs = 0
            
            for i in range(0, len(documents), batch_size):
                batch = documents[i:min(i + batch_size, len(documents))]
                docs_to_insert = []
                
                for doc in batch:
                    try:
                        embedding = self.embedding_model.embed_query(doc.page_content)
                        
                        # Ensure embedding has correct dimension
                        if len(embedding) != self.embedding_dim:
                            print(f"⚠️ Embedding dimension mismatch: expected {self.embedding_dim}, got {len(embedding)}")
                            # Adjust if needed to avoid errors
                            if len(embedding) > self.embedding_dim:
                                embedding = embedding[:self.embedding_dim]
                            else:
                                # Pad with zeros if too short
                                embedding = embedding + [0] * (self.embedding_dim - len(embedding))
                        
                        docs_to_insert.append({
                            "content": doc.page_content,
                            "metadata": doc.metadata if doc.metadata else {},
                            "embedding": embedding
                        })
                    except Exception as doc_error:
                        print(f"❌ Error processing document: {str(doc_error)}")
                
                if docs_to_insert:
                    self.collection.insert_many(docs_to_insert)
                    total_docs += len(docs_to_insert)
            
            print(f"✅ Added {total_docs} documents to MongoDB")
            return time.time() - start_time
        except Exception as e:
            print(f"❌ Error adding documents to MongoDB: {str(e)}")
            return 0.0

    def query(self, query_text: str, top_k: int = 5) -> Tuple[float, List[Document]]:
        if not self.initialized:
            print("❌ Cannot query: MongoDB not initialized")
            return 0.0, []
            
        start_time = time.time()
        try:
            # Get query embedding
            query_emb = self.embedding_model.embed_query(query_text)
            
            # Manual cosine similarity search
            print("Using manual cosine similarity search")
            
            # Get all documents
            all_docs = list(self.collection.find())
            print(f"Retrieved {len(all_docs)} documents for manual similarity search")
            
            if not all_docs:
                print("⚠️ No documents found in collection")
                return time.time() - start_time, []
            
            # Calculate similarity scores
            docs_with_scores = []
            for doc in all_docs:
                if "embedding" in doc and "content" in doc:
                    try:
                        score = self._cosine_similarity(query_emb, doc["embedding"])
                        docs_with_scores.append((score, doc))
                    except Exception as score_error:
                        print(f"⚠️ Error calculating similarity: {str(score_error)}")
            
            # Sort by similarity score (descending)
            docs_with_scores.sort(key=lambda x: x[0], reverse=True)
            
            # Take top_k results
            top_results = docs_with_scores[:top_k]
            
            # Convert to Document objects
            out_docs = []
            for score, doc in top_results:
                out_docs.append(
                    Document(
                        page_content=doc["content"],
                        metadata={**doc.get("metadata", {}), "score": score}
                    )
                )
            
            print(f"✅ Found {len(out_docs)} documents using cosine similarity")
            return time.time() - start_time, out_docs
            
        except Exception as e:
            print(f"❌ Error during similarity search: {str(e)}")
            # Ultimate fallback - just return some documents
            try:
                print("Trying basic document retrieval fallback")
                all_docs = list(self.collection.find().limit(top_k))
                out_docs = [
                    Document(
                        page_content=doc["content"],
                        metadata=doc.get("metadata", {})
                    )
                    for doc in all_docs
                    if "content" in doc
                ]
                print(f"✅ Found {len(out_docs)} documents using basic fallback")
                return time.time() - start_time, out_docs
            except Exception as fallback_e:
                print(f"❌ Error in basic fallback: {str(fallback_e)}")
                return 0.0, []
    
    def _cosine_similarity(self, a, b):
        """Calculate cosine similarity between two vectors"""
        try:
            a_array = np.array(a, dtype=float)
            b_array = np.array(b, dtype=float)
            
            # Check for zero vectors to avoid division by zero
            a_norm = np.linalg.norm(a_array)
            b_norm = np.linalg.norm(b_array)
            
            if a_norm == 0 or b_norm == 0:
                return 0.0
                
            return float(np.dot(a_array, b_array) / (a_norm * b_norm))
        except Exception as e:
            print(f"⚠️ Error in cosine similarity calculation: {str(e)}")
            return 0.0