import os
import uuid
from typing import Dict, List
from werkzeug.utils import secure_filename

def get_unique_id() -> str:
    """Generate a unique ID"""
    return str(uuid.uuid4())

def save_uploaded_file(file, upload_dir: str = "uploads") -> str:
    """
    Save an uploaded file to disk with a secure filename
    
    Args:
        file: File object from request
        upload_dir: Directory to save the file
        
    Returns:
        str: Path to the saved file
    """
    # Create upload directory if it doesn't exist
    os.makedirs(upload_dir, exist_ok=True)
    
    # Get secure filename and add unique ID to avoid collisions
    filename = secure_filename(file.filename)
    unique_filename = f"{get_unique_id()}_{filename}"
    file_path = os.path.join(upload_dir, unique_filename)
    
    # Save the file
    file.save(file_path)
    
    return file_path

def format_document_for_display(doc):
    """Format a document for display in frontend"""
    if not hasattr(doc, 'page_content'):
        return {
            "content": str(doc),
            "metadata": {}
        }
        
    metadata = {}
    if hasattr(doc, 'metadata'):
        metadata = doc.metadata
    
    return {
        "content": doc.page_content,
        "metadata": metadata
    }

def format_results(query_time, results):
    """Format search results for the frontend"""
    formatted_docs = [format_document_for_display(doc) for doc in results]
    
    return {
        "query_time": query_time,
        "results": formatted_docs
    }