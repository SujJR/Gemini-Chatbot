import os
import pymongo
from pymongo.errors import PyMongoError
import uuid
import atexit
from urllib.parse import quote_plus
from pymongo import MongoClient

class MongoDBVectorStore:
    """MongoDB vector store implementation"""
    
    def __init__(self, connection_string=None):
        """Initialize MongoDB vector store with pymongo"""
        self.client = None
        self.db = None
        self.collection = None
        
        try:
            # Default to localhost if no connection string provided
            if connection_string is None:
                connection_string = "mongodb://localhost:27017"
            
            print(f"Connecting to MongoDB: {connection_string.split('@')[0]}@****")
            
            # For Atlas connections, we need to ensure we have a proper Atlas URL
            if "mongodb+srv" in connection_string:
                # Ensure it's using the atlas-specific domain
                if "mongodb.net" not in connection_string:
                    # This is not a proper Atlas URL, let's try local connection instead
                    print("Invalid MongoDB Atlas URL - trying local connection")
                    connection_string = "mongodb://localhost:27017"
            
            # Create a proper connection config for better stability
            connection_options = {
                "serverSelectionTimeoutMS": 30000,  # 30 seconds timeout
                "connectTimeoutMS": 30000,
                "socketTimeoutMS": 60000,
                "maxPoolSize": 10,                 # Smaller connection pool
                "minPoolSize": 0,                  # Start with no connections if not needed
                "maxIdleTimeMS": 30000,            # Close idle connections after 30 seconds
                "retryWrites": True,               # Enable retry for write operations
                "retryReads": True,                # Enable retry for read operations
                "w": "majority",                   # Write concern for data durability
                "waitQueueTimeoutMS": 10000        # How long to wait for a connection
            }
            
            # Connect to MongoDB with improved error handling
            self.client = MongoClient(connection_string, **connection_options)
            
            # Force a roundtrip to the server to check the connection
            self.client.admin.command('ping')
            print("Successfully connected to MongoDB server")
            
            # Get database and collection
            self.db = self.client["vector_db"]
            self.collection = self.db["documents"]
            
            # Create a simple index on content
            try:
                self.collection.create_index([("content", pymongo.TEXT)])
                print("Created text index in MongoDB")
            except Exception as e:
                print(f"Warning: Failed to create index: {e}")
            
            # Register cleanup handler to ensure connection is properly closed
            atexit.register(self._cleanup)
                
        except Exception as e:
            print(f"Error initializing MongoDB: {e}")
            # Close any open connections
            if self.client:
                try:
                    self.client.close()
                except:
                    pass
            self.client = None
            self.db = None
            self.collection = None
    
    def _cleanup(self):
        """Clean up MongoDB connection"""
        if self.client is not None:
            try:
                self.client.close()
                print("MongoDB connection closed cleanly")
            except Exception as e:
                print(f"Error closing MongoDB connection: {e}")
    
    def add_document(self, document, embedding):
        """Add a document to the vector store"""
        if self.collection is None:
            print("MongoDB collection is not available")
            return False
            
        try:
            # Extract content and metadata
            content = document.get("content", "")
            metadata = document.get("metadata", {})
            
            # Prepare document
            mongo_doc = {
                "_id": str(uuid.uuid4()),
                "content": content,
                "metadata": metadata,
                "embedding": embedding
            }
            
            # Insert document with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.collection.insert_one(mongo_doc)
                    return True
                except PyMongoError as e:
                    if attempt < max_retries - 1:
                        print(f"MongoDB insert failed (attempt {attempt+1}/{max_retries}): {e}")
                        # Wait a bit before retry
                        import time
                        time.sleep(1)
                    else:
                        # Last attempt failed
                        raise
            
        except PyMongoError as e:
            print(f"Error adding document to MongoDB: {e}")
            # Try to reconnect if the connection was lost
            try:
                if self.client:
                    self.client.admin.command('ping')
            except:
                print("MongoDB connection lost - attempting to reconnect")
                self.__init__(connection_string="mongodb://localhost:27017")
            return False
    
    def similarity_search(self, query, query_embedding, k=5):
        """Search for similar documents using vector similarity"""
        if self.collection is None:
            return []
            
        try:
            # Determine if we're using Atlas (vector search) or standard MongoDB
            is_atlas = False
            try:
                server_info = self.client.server_info()
                is_atlas = "atlas" in server_info.get("version", "").lower()
            except:
                pass
                
            if is_atlas:
                # MongoDB Atlas vector search
                pipeline = [
                    {
                        "$vectorSearch": {
                            "index": "embedding_index",
                            "queryVector": query_embedding,
                            "path": "embedding",
                            "numCandidates": k * 10,  # Get more candidates for better results
                            "limit": k
                        }
                    },
                    {
                        "$project": {
                            "_id": 0,
                            "content": 1,
                            "metadata": 1,
                            "score": {"$meta": "vectorSearchScore"}
                        }
                    }
                ]
                
                # Try the vector search
                try:
                    results = list(self.collection.aggregate(pipeline))
                except PyMongoError as e:
                    print(f"Vector search error: {e}")
                    raise
            else:
                # Standard MongoDB search (fallback)
                print("Using standard MongoDB search (not vector search)")
                results = list(self.collection.find(
                    {},
                    {"_id": 0, "content": 1, "metadata": 1}
                ).limit(k))
                
                # Add dummy score
                for doc in results:
                    doc["score"] = 0.0
            
            # Format the results
            documents = []
            for doc in results:
                formatted_doc = {
                    "content": doc.get("content", ""),
                    "metadata": doc.get("metadata", {}),
                    "score": doc.get("score", 0.0)
                }
                documents.append(formatted_doc)
            
            return documents
            
        except Exception as e:
            print(f"Error searching in MongoDB: {e}")
            return []
    
    def __del__(self):
        """Destructor to ensure connection cleanup"""
        self._cleanup() 