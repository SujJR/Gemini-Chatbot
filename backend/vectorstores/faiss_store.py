import os
import faiss
import numpy as np
import pickle
from pathlib import Path

class FAISSVectorStore:
    """FAISS vector store implementation"""
    
    def __init__(self, index_path="./storage/faiss"):
        """Initialize FAISS vector store"""
        self.index_path = index_path
        self.docs_path = os.path.join(index_path, "documents.pkl")
        
        # Create storage directory if it doesn't exist
        os.makedirs(index_path, exist_ok=True)
        
        # Load existing index if it exists, otherwise create a new one
        if os.path.exists(os.path.join(index_path, "index.faiss")):
            self.load_index()
        else:
            # Initialize empty index
            self.documents = []
            self.index = None
            # We'll initialize the index when we add the first document
        
    def add_document(self, document, embedding):
        """Add a document to the vector store"""
        # If index doesn't exist yet, create it with the right dimensions
        if self.index is None:
            dimension = len(embedding)
            self.index = faiss.IndexFlatL2(dimension)
        
        # Add the document and its embedding
        self.documents.append(document)
        
        # Add embedding to the index
        np_embedding = np.array([embedding], dtype=np.float32)
        self.index.add(np_embedding)
        
        # Save after each addition
        self.save_index()
        
        return True
    
    def similarity_search(self, query, query_embedding, k=5):
        """Search for similar documents"""
        if self.index is None or len(self.documents) == 0:
            return []
        
        # Convert query embedding to numpy array
        np_embedding = np.array([query_embedding], dtype=np.float32)
        
        # Search the index
        distances, indices = self.index.search(np_embedding, min(k, len(self.documents)))
        
        # Get the documents
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.documents):  # Sanity check
                doc = self.documents[idx]
                # Add distance to the document
                doc_with_score = dict(doc)
                doc_with_score["score"] = float(distances[0][i])
                results.append(doc_with_score)
        
        return results
    
    def save_index(self):
        """Save the index and documents to disk"""
        if self.index is not None:
            # Save the FAISS index
            faiss.write_index(self.index, os.path.join(self.index_path, "index.faiss"))
            
            # Save the documents
            with open(self.docs_path, 'wb') as f:
                pickle.dump(self.documents, f)
    
    def load_index(self):
        """Load the index and documents from disk"""
        try:
            # Load the FAISS index
            self.index = faiss.read_index(os.path.join(self.index_path, "index.faiss"))
            
            # Load the documents
            if os.path.exists(self.docs_path):
                with open(self.docs_path, 'rb') as f:
                    self.documents = pickle.load(f)
            else:
                self.documents = []
        except Exception as e:
            print(f"Error loading FAISS index: {e}")
            self.index = None
            self.documents = [] 