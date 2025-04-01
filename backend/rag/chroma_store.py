import time
import os
from typing import List, Dict, Tuple
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document

class ChromaVectorStore:
    def __init__(self, embedding_model=None):
        """Initialize the Chroma vector store with embedding model"""
        self.embedding_model = embedding_model or OpenAIEmbeddings()
        self.vectorstore = None
        self.persist_directory = os.path.join("chroma_db")
        os.makedirs(self.persist_directory, exist_ok=True)
        
    def add_documents(self, documents: List[Document]) -> float:
        """
        Add documents to Chroma vector store
        
        Args:
            documents: List of documents to add
            
        Returns:
            float: Time taken to add documents
        """
        start_time = time.time()
        
        # Create Chroma vectorstore from documents
        self.vectorstore = Chroma.from_documents(
            documents,
            self.embedding_model,
            persist_directory=self.persist_directory
        )
        
        # Persist the vectorstore
        self.vectorstore.persist()
        
        end_time = time.time()
        return end_time - start_time
        
    def query(self, query_text: str, top_k: int = 5) -> Tuple[float, List[Document]]:
        """
        Query the Chroma vector store
        
        Args:
            query_text: Query text
            top_k: Number of results to return
            
        Returns:
            Tuple[float, List[Document]]: Time taken and results
        """
        if self.vectorstore is None:
            # Initialize from persisted data if available
            try:
                self.vectorstore = Chroma(
                    persist_directory=self.persist_directory,
                    embedding_function=self.embedding_model
                )
            except:
                return 0.0, []
                
        start_time = time.time()
        
        # Search for similar documents
        results = self.vectorstore.similarity_search(query_text, k=top_k)
        
        end_time = time.time()
        return end_time - start_time, results