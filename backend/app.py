import os
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import google.generativeai as genai

# RAG imports
from rag.document import extract_text_from_pdf, split_text
from rag.faiss_store import FAISSVectorStore
from rag.chroma_store import ChromaVectorStore
from rag.utils import save_uploaded_file, format_results
from langchain_google_genai import GoogleGenerativeAIEmbeddings  # Changed from OpenAI to Google

# Load environment variables
load_dotenv()

app = Flask(__name__)
# Enable CORS for all routes and all origins
CORS(app, resources={r"/*": {"origins": "*"}})

# Configure the Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Initialize the model for chat
model = genai.GenerativeModel('gemini-1.5-pro')
chat_session = model.start_chat(history=[])

# Initialize embedding model with Gemini instead of OpenAI
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

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages"""
    data = request.json
    message = data.get('message', '')
    
    if not message:
        return jsonify({"success": False, "error": "No message provided"})
    
    try:
        response = chat_session.send_message(message)
        return jsonify({"success": True, "response": response.text})
    except Exception as e:
        print(f"Error in chat: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/upload', methods=['POST'])
def upload():
    """
    Handle document upload, process text, and index in all vector stores
    Returns performance metrics for each database
    """
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file provided"})
        
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"success": False, "message": "No file selected"})
        
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({"success": False, "message": "Only PDF files are supported"})
    
    try:
        # Save the uploaded file
        file_path = save_uploaded_file(file)
        
        # Extract text from PDF
        text = extract_text_from_pdf(file_path)
        
        if not text or len(text) < 10:
            return jsonify({"success": False, "message": "Could not extract text from the PDF file"})
            
        # Split text into chunks
        document_chunks = split_text(text)
        
        if not document_chunks or len(document_chunks) == 0:
            return jsonify({"success": False, "message": "Failed to process document into chunks"})
            
        # Time how long it takes to add documents to each vector store
        # FAISS
        start_time = time.time()
        faiss_store.add_documents(document_chunks)
        faiss_time = time.time() - start_time
        
        # ChromaDB
        start_time = time.time()
        chroma_store.add_documents(document_chunks)
        chroma_time = time.time() - start_time
        
        # Weaviate (if available)
        weaviate_time = 0
        if weaviate_available and weaviate_store:
            start_time = time.time()
            weaviate_store.add_documents(document_chunks)
            weaviate_time = time.time() - start_time
        
        # Return success with timing metrics
        return jsonify({
            "success": True,
            "message": "Document processed successfully",
            "document": {
                "filename": file.filename,
                "chunk_count": len(document_chunks),
                "indexing_times": {
                    "faiss": faiss_time,
                    "chroma": chroma_time,
                    "weaviate": weaviate_time if weaviate_available else -1
                },
                "weaviate_available": weaviate_available
            }
        })
    
    except Exception as e:
        print(f"Error processing document: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"})


@app.route('/api/rag', methods=['POST'])
def rag_query():
    """
    Process a RAG query using the selected vector database
    """
    data = request.json
    query = data.get('query', '')
    db_type = data.get('db_type', 'faiss')
    
    if not query:
        return jsonify({"success": False, "message": "No query provided"})
    
    # Check if Weaviate is requested but not available
    if db_type == 'weaviate' and not weaviate_available:
        return jsonify({
            "success": False, 
            "message": "Weaviate is not available. Please use FAISS or ChromaDB instead."
        })
        
    try:
        # Select the appropriate vector store based on the type
        if db_type == 'faiss':
            query_time, results = faiss_store.query(query)
            vector_store_name = "FAISS"
        elif db_type == 'chroma':
            query_time, results = chroma_store.query(query)
            vector_store_name = "ChromaDB"
        elif db_type == 'weaviate' and weaviate_available:
            query_time, results = weaviate_store.query(query)
            vector_store_name = "Weaviate"
        else:
            return jsonify({"success": False, "message": "Invalid database type"})
            
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
        return jsonify({
            "success": True,
            "query": query,
            "db_type": db_type,
            "query_time": query_time,
            "rag_response": rag_response,
            "retrieved_docs": formatted_results["results"]
        })
    
    except Exception as e:
        print(f"Error processing RAG query: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"})


@app.route('/api/available-dbs', methods=['GET'])
def available_dbs():
    """Return the list of available vector databases"""
    dbs = ["faiss", "chroma"]
    if weaviate_available:
        dbs.append("weaviate")
    
    return jsonify({
        "success": True,
        "available_databases": dbs
    })


@app.route('/api/test', methods=['GET'])
def test():
    """Test endpoint to verify API is working"""
    return jsonify({"status": "ok", "message": "API is working"})


if __name__ == '__main__':
    app.run(debug=True)