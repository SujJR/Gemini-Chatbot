import time
import os
from typing import List, Dict, Tuple
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document

class FAISSVectorStore:
    def __init__(self, embedding_model=None):
        """Initialize the FAISS vector store with embedding model"""
        self.embedding_model = embedding_model or OpenAIEmbeddings()
        self.vectorstore = None
        
    def add_documents(self, documents: List[Document]) -> float:
        """
        Add documents to FAISS vector store
        
        Args:
            documents: List of documents to add
            
        Returns:
            float: Time taken to add documents
        """
        start_time = time.time()
        
        # Create FAISS vectorstore from documents
        self.vectorstore = FAISS.from_documents(
            documents,
            self.embedding_model
        )
        
        end_time = time.time()
        return end_time - start_time
        
    def query(self, query_text: str, top_k: int = 5) -> Tuple[float, List[Document]]:
        """
        Query the FAISS vector store
        
        Args:
            query_text: Query text
            top_k: Number of results to return
            
        Returns:
            Tuple[float, List[Document]]: Time taken and results
        """
        if self.vectorstore is None:
            return 0.0, []
            
        start_time = time.time()
        
        # Search for similar documents
        results = self.vectorstore.similarity_search(query_text, k=top_k)
        
        end_time = time.time()
        return end_time - start_time, results