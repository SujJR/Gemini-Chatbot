from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List, Dict

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text content from a PDF file
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        str: Extracted text content
    """
    reader = PdfReader(pdf_path)
    text = ""
    
    for page in reader.pages:
        text += page.extract_text() + "\n"
        
    return text

def split_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Dict]:
    """
    Split text into chunks for processing
    
    Args:
        text: The text to split
        chunk_size: Size of each chunk
        chunk_overlap: Overlap between chunks
        
    Returns:
        List[Dict]: List of document chunks with metadata
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len
    )
    
    chunks = splitter.create_documents([text])
    return chunks