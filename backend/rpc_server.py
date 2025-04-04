import os
import time
import uuid
from typing import Dict, List, Any, Optional
from jsonrpcserver import method, Success, Result, Error, dispatch
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from dotenv import load_dotenv
import google.generativeai as genai

# RAG imports
from rag.document import extract_text_from_pdf, split_text
from rag.faiss_store import FAISSVectorStore
from rag.chroma_store import ChromaVectorStore
from rag.utils import save_uploaded_file, format_results
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from rag.mongo_store import MongoVectorStore
from rag.pgvector_store import PGVectorStore
from rag.milvus_store import MilvusVectorStore

# Load environment variables
load_dotenv()

app = Flask(__name__)
# Enable CORS for all routes and all origins
CORS(app, resources={r"/*": {"origins": "*"}})

# Configure the Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Initialize the model for chat
model = genai.GenerativeModel('gemini-2.0-flash')
chat_session = model.start_chat(history=[])

# Initialize embedding model with Gemini
embedding_model = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=os.getenv("GEMINI_API_KEY")
)

# Initialize vector stores
faiss_store = FAISSVectorStore(embedding_model)
chroma_store = ChromaVectorStore(embedding_model)

# Try to import Weaviate, but handle the case where it fails
weaviate_available = False
weaviate_store = None
try:
    from rag.weaviate_store import WeaviateVectorStore
    weaviate_store = WeaviateVectorStore(embedding_model)
    weaviate_available = True
    print("Weaviate successfully initialized")
except ImportError as e:
    print(f"Weaviate import failed: {e}")
    print("The application will run without Weaviate support")

mongo_store = MongoVectorStore(embedding_model)
pgvector_store = PGVectorStore(embedding_model)

# Initialize Milvus vector store with proper error handling
milvus_available = False
milvus_store = None
try:
    from rag.milvus_store import MilvusVectorStore
    print("Attempting to initialize Milvus...")
    milvus_store = MilvusVectorStore(embedding_model)
    
    # Check if initialization was successful
    if milvus_store.initialized:
        milvus_available = True
        print("✅ Milvus successfully initialized")
    else:
        print("❌ Milvus initialization failed - running without Milvus")
except Exception as e:
    print(f"❌ Milvus import error: {str(e)}")
    print("The application will run without Milvus support")

# ----- RPC Methods -----

@method
def chat(message: str) -> Result:
    """RPC method for chat"""
    if not message:
        return Error(code=-32602, message="No message provided")
    
    try:
        response = chat_session.send_message(message)
        return Success({"response": response.text})
    except Exception as e:
        print(f"Error in chat: {str(e)}")
        return Error(code=-32603, message=str(e))

@method
def upload_document(file_data: str, filename: str) -> Result:
    """
    RPC method to handle document upload
    The file_data should be base64 encoded
    """
    import base64
    
    if not file_data or not filename:
        return Error(code=-32602, message="No file provided")
    
    if not filename.lower().endswith('.pdf'):
        return Error(code=-32602, message="Only PDF files are supported")
    
    try:
        # Decode base64 file data
        file_bytes = base64.b64decode(file_data)
        
        # Create a unique filename
        unique_filename = f"{uuid.uuid4()}_{secure_filename(filename)}"
        
        # Save file to disk
        upload_dir = os.path.join(os.getcwd(), 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, unique_filename)
        
        with open(file_path, 'wb') as f:
            f.write(file_bytes)
        
        # Extract text from PDF
        text = extract_text_from_pdf(file_path)
        
        if not text or len(text) < 10:
            return Error(code=-32603, message="Could not extract text from the PDF file")
            
        # Split text into chunks
        document_chunks = split_text(text)
        
        if not document_chunks or len(document_chunks) == 0:
            return Error(code=-32603, message="Failed to process document into chunks")
            
        # Initialize timing dictionary
        indexing_times = {
            "faiss": 0,
            "chroma": 0,
            "weaviate": -1,
            "mongo": -1,
            "pgvector": -1,
            "milvus": -1
        }
        
        # Time how long it takes to add documents to each vector store
        # FAISS
        start_time = time.time()
        faiss_store.add_documents(document_chunks)
        indexing_times["faiss"] = time.time() - start_time
        
        # ChromaDB
        start_time = time.time()
        chroma_store.add_documents(document_chunks)
        indexing_times["chroma"] = time.time() - start_time
        
        # Weaviate (if available)
        if weaviate_available and weaviate_store:
            start_time = time.time()
            weaviate_store.add_documents(document_chunks)
            indexing_times["weaviate"] = time.time() - start_time
            
        # MongoDB
        try:
            start_time = time.time()
            mongo_store.add_documents(document_chunks)
            indexing_times["mongo"] = time.time() - start_time
        except Exception as e:
            print(f"Error indexing in MongoDB: {str(e)}")
            
        # pgvector
        try:
            start_time = time.time()
            pgvector_store.add_documents(document_chunks)
            indexing_times["pgvector"] = time.time() - start_time
        except Exception as e:
            print(f"Error indexing in pgvector: {str(e)}")
            
        # Milvus (if available)
        if milvus_available and milvus_store:
            try:
                start_time = time.time()
                milvus_store.add_documents(document_chunks)
                indexing_times["milvus"] = time.time() - start_time
            except Exception as e:
                print(f"Error indexing in Milvus: {str(e)}")
        
        # Return success with timing metrics
        return Success({
            "message": "Document processed successfully",
            "document": {
                "filename": filename,
                "chunk_count": len(document_chunks),
                "indexing_times": indexing_times,
                "available_dbs": {
                    "faiss": True,
                    "chroma": True,
                    "weaviate": weaviate_available,
                    "mongo": indexing_times["mongo"] >= 0,
                    "pgvector": indexing_times["pgvector"] >= 0,
                    "milvus": milvus_available and indexing_times["milvus"] >= 0
                }
            }
        })
    
    except Exception as e:
        print(f"Error processing document: {str(e)}")
        return Error(code=-32603, message=f"Error: {str(e)}")

@method
def rag_query(query: str, db_type: str = 'faiss', compare_all: bool = False) -> Result:
    """
    RPC method to process a RAG query using the selected vector database or all databases
    """
    if not query:
        return Error(code=-32602, message="No query provided")
    
    try:
        # If compare_all is True, we'll query all available databases and return all results
        if compare_all:
            all_results = {}
            # Get the list of available databases
            available_dbs = ["faiss", "chroma"]
            if weaviate_available:
                available_dbs.append("weaviate")
            if mongo_store.initialized:
                available_dbs.append("mongo")
            if pgvector_store.initialized:
                available_dbs.append("pgvector")
            if milvus_available and milvus_store.initialized:
                available_dbs.append("milvus")
            
            # Query each available database
            for db in available_dbs:
                try:
                    if db == 'faiss':
                        query_time, results = faiss_store.query(query)
                        vector_store_name = "FAISS"
                    elif db == 'chroma':
                        query_time, results = chroma_store.query(query)
                        vector_store_name = "ChromaDB"
                    elif db == 'weaviate':
                        query_time, results = weaviate_store.query(query)
                        vector_store_name = "Weaviate"
                    elif db == 'mongo':
                        query_time, results = mongo_store.query(query)
                        vector_store_name = "MongoDB"
                    elif db == 'pgvector':
                        query_time, results = pgvector_store.query(query)
                        vector_store_name = "pgvector"
                    elif db == 'milvus':
                        query_time, results = milvus_store.query(query)
                        vector_store_name = "Milvus"
                    
                    # Format results for this database
                    formatted_results = format_results(query_time, results)
                    all_results[db] = {
                        "name": vector_store_name,
                        "query_time": query_time,
                        "retrieved_docs": formatted_results["results"]
                    }
                except Exception as db_error:
                    print(f"Error querying {db}: {str(db_error)}")
                    all_results[db] = {
                        "name": db,
                        "error": str(db_error)
                    }
            
            # Use Gemini model to generate a response based on the best results
            # We'll use the database with most results or lowest query time if tied
            best_db = None
            max_results = -1
            min_time = float('inf')
            
            # Determine the fastest database (lowest query time)
            for db, result in all_results.items():
                if "query_time" in result and result["query_time"] < min_time and "retrieved_docs" in result and len(result["retrieved_docs"]) > 0:
                    min_time = result["query_time"]
                    max_results = len(result["retrieved_docs"])  # Update max_results here
                    best_db = db
            
            # If no database has results with valid times, fall back to most results
            if best_db is None:
                for db, result in all_results.items():
                    if "retrieved_docs" in result and len(result["retrieved_docs"]) > max_results:
                        max_results = len(result["retrieved_docs"])
                        best_db = db
            
            # If we have a best DB with results, generate RAG response
            rag_response = "No results found in any database."
            if best_db and max_results > 0:
                if "retrieved_docs" in all_results[best_db]:
                    # Extract content from documents
                    docs = [doc["content"] for doc in all_results[best_db]["retrieved_docs"]]
                    context = "\n\n".join(docs)
                    
                    print(f"Generating RAG response using {best_db} with {max_results} documents")
                    
                    prompt = f"""
                    Based on the following information, please answer the query: {query}
                    
                    Context information:
                    {context}
                    
                    Please provide a concise and accurate answer based only on the context provided.
                    If the context doesn't contain relevant information, state that you don't have enough information to answer.
                    """
                    
                    response = model.generate_content(prompt)
                    rag_response = response.text
            
            # Return comparison results
            return Success({
                "query": query,
                "compare_all": True,
                "results": all_results,
                "rag_response": rag_response,
                "best_db": best_db
            })
        
        # Otherwise, use the single selected database as before
        else:
            if db_type == 'faiss':
                query_time, results = faiss_store.query(query)
                vector_store_name = "FAISS"
            elif db_type == 'chroma':
                query_time, results = chroma_store.query(query)
                vector_store_name = "ChromaDB"
            elif db_type == 'weaviate':
                query_time, results = weaviate_store.query(query)
                vector_store_name = "Weaviate"
            elif db_type == 'mongo':
                query_time, results = mongo_store.query(query)
                vector_store_name = "MongoDB"
            elif db_type == 'pgvector':
                query_time, results = pgvector_store.query(query)
                vector_store_name = "pgvector"
            elif db_type == 'milvus':
                query_time, results = milvus_store.query(query)
                vector_store_name = "Milvus"
            else:
                return Error(code=-32602, message="Invalid database type")
                
            # Format results for display
            formatted_results = format_results(query_time, results)
            
            # Use Gemini model to generate a response based on retrieved context
            context = "\n\n".join([doc.page_content for doc in results])
            
            prompt = f"""
            Based on the following information, please answer the query: {query}
            
            Context information:
            {context}
            
            Please provide a concise and accurate answer based only on the context provided.
            If the context doesn't contain relevant information, state that you don't have enough information to answer.
            """
            
            response = model.generate_content(prompt)
            rag_response = response.text
            
            # Return the results
            return Success({
                "query": query,
                "db_type": db_type,
                "query_time": query_time,
                "rag_response": rag_response,
                "retrieved_docs": formatted_results["results"]
            })
    
    except Exception as e:
        print(f"Error processing RAG query: {str(e)}")
        return Error(code=-32603, message=f"Error: {str(e)}")

@method
def get_available_dbs() -> Result:
    """RPC method to return the list of available vector databases"""
    dbs = ["faiss", "chroma", "mongo", "pgvector"]
    if weaviate_available:
        dbs.append("weaviate")
    if milvus_available:
        dbs.append("milvus")
    
    return Success({
        "available_databases": dbs
    })

# Endpoint for handling RPC calls
@app.route('/rpc', methods=['POST'])
def handle_rpc():
    try:
        request_data = request.get_json()
        response = dispatch(request_data)
        return Response(str(response), content_type="application/json")
    except Exception as e:
        print(f"RPC Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/test', methods=['GET'])
def test():
    """Test endpoint to verify API is working"""
    return jsonify({"status": "ok", "message": "API is working"})

if __name__ == '__main__':
    app.run(debug=True) 