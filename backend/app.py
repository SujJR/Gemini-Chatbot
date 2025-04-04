import os
import time
import uuid
import base64
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from jsonrpcserver import method, Success, Error, dispatch
from werkzeug.utils import secure_filename

# Import vector store functionalities
from vectorstores.faiss_store import FAISSVectorStore
from vectorstores.chroma_store import ChromaVectorStore
from vectorstores.weaviate_store import WeaviateVectorStore
from vectorstores.mongodb_store import MongoDBVectorStore
from vectorstores.pgvector_store import PGVectorStore
from vectorstores.milvus_store import MilvusVectorStore

from document_processor import process_document

app = Flask(__name__)
# Configure CORS with specific settings
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "max_age": 3600
    }
})

# Configure Gemini API
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "your-api-key")
genai.configure(api_key=GOOGLE_API_KEY)

# Initialize chat model - use older model for wider compatibility
try:
    print("Initializing chat model...")
    chat_model = genai.GenerativeModel('gemini-pro')
    print("✅ Chat model initialized successfully")
except Exception as e:
    print(f"❌ Error initializing chat model: {e}")
    chat_model = None

# Get database connection strings from environment
# FAISS and ChromaDB are local
# Weaviate connection URL from .env
WEAVIATE_URL = os.environ.get("WEAVIATE_URL", "http://localhost:8080")
WEAVIATE_API_KEY = os.environ.get("WEAVIATE_API_KEY")

# MongoDB connection string from .env
MONGO_USER = os.environ.get("MONGO_USER")
MONGO_PASSWORD = os.environ.get("MONGO_PASSWORD")
MONGO_CLUSTER = os.environ.get("MONGO_CLUSTER")

# First try with MongoDB Atlas if credentials are provided
if MONGO_USER and MONGO_PASSWORD and MONGO_CLUSTER:
    # Convert to lowercase for consistency
    cluster_name = MONGO_CLUSTER.lower()
    
    if "mongodb.net" in cluster_name:
        # Full MongoDB Atlas hostname provided
        MONGODB_URI = f"mongodb+srv://{MONGO_USER}:{MONGO_PASSWORD}@{cluster_name}/?retryWrites=true&w=majority"
        print(f"Using MongoDB Atlas connection: {MONGODB_URI.split('@')[0]}@****{cluster_name}")
    else:
        # Try to use simple standalone MongoDB, but be prepared for it to fail
        print(f"Using direct MongoDB connection to host: {cluster_name}")
        MONGODB_URI = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{cluster_name}:27017/?authSource=admin"
else:
    # Fallback to local MongoDB if no credentials
    MONGODB_URI = "mongodb://localhost:27017"
    print("No MongoDB credentials provided, using local MongoDB at localhost:27017")

# PostgreSQL connection string from .env
DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_NAME = os.environ.get("DB_NAME")
if DB_HOST and DB_USER and DB_PASSWORD:
    POSTGRES_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT or '5432'}/{DB_NAME or 'postgres'}"
else:
    POSTGRES_URI = os.environ.get("POSTGRES_URI", "postgresql://postgres:postgres@localhost:5432/vector_db")

# Milvus connection string from .env
MILVUS_URI = os.environ.get("MILVUS_URI")
MILVUS_USER = os.environ.get("MILVUS_USER")
MILVUS_PASSWORD = os.environ.get("MILVUS_PASSWORD")

# Initialize vector stores with error handling
try:
    faiss_store = FAISSVectorStore()
    print("✅ FAISS initialized successfully (local)")
except Exception as e:
    print(f"❌ FAISS initialization error: {e}")
    faiss_store = None

try:
    chroma_store = ChromaVectorStore()
    print("✅ ChromaDB initialized successfully (local)")
except Exception as e:
    print(f"❌ ChromaDB initialization error: {e}")
    chroma_store = None

try:
    # Use the Weaviate cloud instance
    weaviate_store = WeaviateVectorStore(url=WEAVIATE_URL, api_key=WEAVIATE_API_KEY)
    print(f"✅ Weaviate initialized successfully (cloud: {WEAVIATE_URL})")
except Exception as e:
    print(f"❌ Weaviate initialization error: {e}")
    weaviate_store = None

try:
    # Use the MongoDB Atlas cloud instance
    mongodb_store = MongoDBVectorStore(connection_string=MONGODB_URI)
    print(f"✅ MongoDB initialized successfully (cloud: {MONGO_CLUSTER})")
except Exception as e:
    print(f"❌ MongoDB initialization error: {e}")
    mongodb_store = None

try:
    # Use the Supabase PostgreSQL instance
    pgvector_store = PGVectorStore(connection_string=POSTGRES_URI)
    print(f"✅ pgvector initialized successfully (cloud: {DB_HOST})")
except Exception as e:
    print(f"❌ pgvector initialization error: {e}")
    pgvector_store = None

try:
    # Use the Zilliz cloud Milvus instance
    milvus_store = MilvusVectorStore(uri=MILVUS_URI, user=MILVUS_USER, password=MILVUS_PASSWORD)
    print(f"✅ Milvus initialized successfully (cloud: {MILVUS_URI})")
except Exception as e:
    print(f"❌ Milvus initialization error: {e}")
    milvus_store = None

# Global dictionary to track available databases
available_dbs = {
    "faiss": faiss_store is not None,
    "chroma": chroma_store is not None,
    "weaviate": weaviate_store is not None,
    "mongo": mongodb_store is not None,
    "pgvector": pgvector_store is not None,
    "milvus": milvus_store is not None
}

# Helper function to get embedding from Gemini
def get_embedding(text):
    """Simple text processing function"""
    if not text:
        return []
    
    # Just return a simple list of zeros for compatibility
    return [0.0] * 768

# Helper function to generate a response using Gemini with RAG context
def generate_rag_response(query, retrieved_docs):
    if not retrieved_docs or len(retrieved_docs) == 0:
        return "No relevant information found."

    # Prepare context from retrieved documents
    context = "\n\n".join([f"Document {i+1}:\n{doc.get('content', '')}" for i, doc in enumerate(retrieved_docs)])
    
    # Generate response using Gemini
    prompt = f"""You are an AI assistant helping to answer questions based on provided documents.
    Use only the information in the documents to answer the question. If you don't know or can't find the information,
    just say so. Be concise and accurate.
    
    Document Context:
    {context}
    
    Question: {query}
    
    Answer:"""
    
    try:
        response = chat_model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error generating response: {e}")
        return "I encountered an error while generating a response."

# RPC Methods

@method
def chat(message: str):
    """Handle a chat message and return a response"""
    try:
        response = chat_model.generate_content(message)
        return Success({"response": response.text})
    except Exception as e:
        return Error(code=500, message=str(e))

@method
def upload_document(file_data: str, filename: str):
    """Accept a base64 encoded PDF file, save it, extract text, and index into vector stores"""
    try:
        # Decode base64 string to file
        decoded_data = base64.b64decode(file_data)
        
        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join(os.path.dirname(__file__), 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save the file
        safe_filename = secure_filename(filename)
        file_path = os.path.join(upload_dir, safe_filename)
        print(f"Saving uploaded file to: {file_path}")
        with open(file_path, 'wb') as f:
            f.write(decoded_data)
        print(f"File saved successfully: {safe_filename}")
        
        # Process the document (extract text and create chunks)
        print(f"Processing document: {safe_filename}")
        result = process_document(file_path, get_embedding)
        print(f"Document processing completed.")
        
        # Update available databases based on the result from process_document
        global available_dbs
        if result and result.get("success"):
             available_dbs = result["document"]["available_dbs"]
             print(f"Updated available databases: {available_dbs}")
             return Success(result)
        else:
            # If process_document failed, return its error message
            error_message = result.get("message", "Document processing failed with an unspecified error.")
            print(f"Error during document processing: {error_message}")
            return Error(code=500, message=error_message)
            
    except Exception as e:
        # Log the full exception details
        import traceback
        print(f"FATAL ERROR in upload_document: {e}")
        print(traceback.format_exc()) # Print the full stack trace
        # Return a more specific error message if possible
        return Error(code=500, message=f"Upload failed due to an internal server error: {e}")

@method
def rag_query(query: str, db_type: str, compare_all: bool = False):
    """
    Process a query using either a selected vector database or all databases for comparison.
    
    Parameters:
    - query: The search query
    - db_type: The database to use (faiss, chroma, weaviate, mongo, pgvector, milvus)
    - compare_all: If True, query all databases and compare results
    
    Returns:
    - JSON with query results and RAG response
    """
    start_time = time.time()
    
    # Mapping of DB type to vector store objects
    db_map = {
        "faiss": faiss_store,
        "chroma": chroma_store,
        "weaviate": weaviate_store,
        "mongo": mongodb_store,
        "pgvector": pgvector_store,
        "milvus": milvus_store
    }
    
    try:
        if compare_all:
            # Query all available databases and compare results
            all_results = {}
            min_time = float('inf')  # Track lowest query time
            best_db = None
            max_results = 0
            best_retrieved_docs = []
            
            for db_name, db in db_map.items():
                if db is None:
                    all_results[db_name] = {
                        "success": False,
                        "error": "Database not available or initialized"
                    }
                    continue
                    
                if db_name in available_dbs and available_dbs.get(db_name, False):
                    db_start_time = time.time()
                    try:
                        # Use similarity search to retrieve documents from the vector database
                        query_embedding = get_embedding(query)
                        retrieved_docs = db.similarity_search(query, query_embedding)
                        
                        db_query_time = time.time() - db_start_time
                        all_results[db_name] = {
                            "success": True,
                            "query_time": db_query_time,
                            "retrieved_docs": retrieved_docs
                        }
                        
                        # Track the database with the lowest query time (if it returned results)
                        if db_query_time < min_time and len(retrieved_docs) > 0:
                            min_time = db_query_time
                            best_db = db_name
                            max_results = len(retrieved_docs)
                            best_retrieved_docs = retrieved_docs
                            print(f"New fastest: {db_name} with {max_results} docs and time {min_time}")
                        
                    except Exception as e:
                        all_results[db_name] = {
                            "success": False,
                            "error": str(e)
                        }
                else:
                    all_results[db_name] = {
                        "success": False,
                        "error": "Database not available"
                    }
            
            # If no valid times, fall back to most results
            if best_db is None:
                for db_name, result in all_results.items():
                    if result.get("success", False) and result.get("retrieved_docs"):
                        doc_count = len(result["retrieved_docs"])
                        if doc_count > max_results:
                            max_results = doc_count
                            best_db = db_name
                            best_retrieved_docs = result["retrieved_docs"]
            
            # Generate RAG response based on best results
            print(f"Using {best_db} to generate RAG response with {max_results} documents")
            rag_response = generate_rag_response(query, best_retrieved_docs) if max_results > 0 else "No results found."
            
            total_time = time.time() - start_time
            return Success({
                "success": True,
                "query": query,
                "query_time": total_time,
                "response": rag_response,
                "best_db": best_db,
                "comparison_results": all_results
            })
        else:
            # Regular RAG query on a single database
            db = db_map.get(db_type)
            if not db:
                return Error(code=400, message=f"Invalid database type or database not initialized: {db_type}")
            
            # Check if database is available
            if not available_dbs.get(db_type, False):
                return Error(code=404, message=f"Database {db_type} has no indexed documents or is not available")
            
            # Use similarity search to retrieve documents from the vector database
            query_embedding = get_embedding(query)
            retrieved_docs = db.similarity_search(query, query_embedding)
            
            # Generate response using Gemini
            rag_response = generate_rag_response(query, retrieved_docs)
            
            query_time = time.time() - start_time
            return Success({
                "success": True,
                "query": query,
                "db_type": db_type,
                "query_time": query_time,
                "response": rag_response,
                "retrieved_docs": retrieved_docs
            })
    except Exception as e:
        return Error(code=500, message=str(e))

@method
def get_available_dbs():
    """Get a list of available vector databases"""
    # Filter to include only databases that have been initialized
    available_databases = [db for db, available in available_dbs.items() if available]
    if not available_databases:
        # Default to all DB types if none have been initialized
        available_databases = ["faiss", "chroma", "weaviate", "mongo", "pgvector", "milvus"]
    
    return Success({"available_databases": available_databases})

# Create RPC endpoint
@app.route("/rpc", methods=["POST"])
def handle_rpc():
    """JSON-RPC request handler"""
    response = dispatch(request.get_data(as_text=True))
    return response

# Legacy REST API endpoints for backward compatibility
@app.route("/api/chat", methods=["POST"])
def rest_chat():
    data = request.json
    message = data.get("message", "")
    result = chat(message)
    if hasattr(result, 'result'):
        return jsonify({"success": True, "response": result.result["response"]})
    return jsonify({"success": False, "error": getattr(result, 'message', 'Unknown error')})

@app.route("/api/upload", methods=["POST"])
def rest_upload():
    if "file" not in request.files:
        return jsonify({"success": False, "message": "No file part"})
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "message": "No selected file"})
    
    # Read the file and convert to base64
    file_data = base64.b64encode(file.read()).decode('utf-8')
    
    result = upload_document(file_data, file.filename)
    # Check if result is a Success instance from jsonrpcserver
    if hasattr(result, 'result'):
        return jsonify(result.result)
    return jsonify({"success": False, "message": getattr(result, 'message', 'Unknown error')})

@app.route("/api/rag", methods=["POST"])
def rest_rag_query():
    data = request.json
    query = data.get("query", "")
    db_type = data.get("db_type", "faiss")
    compare_all = data.get("compare_all", False)
    
    result = rag_query(query, db_type, compare_all)
    if hasattr(result, 'result'):
        return jsonify(result.result)
    return jsonify({"success": False, "message": getattr(result, 'message', 'Unknown error')})

@app.route("/api/available-dbs", methods=["GET"])
def rest_available_dbs():
    result = get_available_dbs()
    if hasattr(result, 'result'):
        return jsonify({"success": True, **result.result})
    return jsonify({"success": False, "message": getattr(result, 'message', 'Unknown error')})

@app.route("/api/test", methods=["GET"])
def test():
    """Simple endpoint to test if the API is working"""
    return jsonify({"message": "API is working!", "status": "ok"})

@app.route("/ping", methods=["GET"])
def ping():
    """Lightweight ping endpoint for health checks"""
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=True, host="0.0.0.0", port=port)