import React, { useState } from 'react';
import axios from 'axios';
import { RagResponse, DatabaseType } from '../types';

interface RagQueryFormProps {
  onQueryComplete: (response: RagResponse) => void;
  isQuerying: boolean;
  setIsQuerying: (isQuerying: boolean) => void;
}

const RagQueryForm: React.FC<RagQueryFormProps> = ({ 
  onQueryComplete, 
  isQuerying, 
  setIsQuerying 
}) => {
  const [query, setQuery] = useState('');
  const [selectedDatabase, setSelectedDatabase] = useState<DatabaseType>('faiss');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!query.trim()) {
      setError('Please enter a query');
      return;
    }
    
    setError(null);
    setIsQuerying(true);
    
    try {
      const response = await axios.post<RagResponse>(
        'http://localhost:5000/api/rag',
        {
          query: query,
          db_type: selectedDatabase
        }
      );
      
      if (response.data.success) {
        onQueryComplete(response.data);
      } else {
        setError(response.data.message || 'Query failed');
      }
    } catch (err: any) {
      console.error('Query error:', err);
      setError(err.response?.data?.error || 'Error processing query');
    } finally {
      setIsQuerying(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Ask a question about your document:
        </label>
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={isQuerying}
          placeholder="Example: What are the key points discussed in this document?"
          className="w-full p-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          rows={3}
        />
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Select Vector Database:
        </label>
        <div className="grid grid-cols-3 gap-2">
          <button
            type="button"
            onClick={() => setSelectedDatabase('faiss')}
            className={`py-2 px-3 rounded-md text-center text-sm font-medium ${
              selectedDatabase === 'faiss'
                ? 'bg-blue-100 text-blue-700 border border-blue-300'
                : 'bg-gray-100 text-gray-700 border border-gray-300 hover:bg-gray-200'
            }`}
          >
            FAISS
          </button>
          <button
            type="button"
            onClick={() => setSelectedDatabase('chroma')}
            className={`py-2 px-3 rounded-md text-center text-sm font-medium ${
              selectedDatabase === 'chroma'
                ? 'bg-blue-100 text-blue-700 border border-blue-300'
                : 'bg-gray-100 text-gray-700 border border-gray-300 hover:bg-gray-200'
            }`}
          >
            ChromaDB
          </button>
          <button
            type="button"
            onClick={() => setSelectedDatabase('weaviate')}
            className={`py-2 px-3 rounded-md text-center text-sm font-medium ${
              selectedDatabase === 'weaviate'
                ? 'bg-blue-100 text-blue-700 border border-blue-300'
                : 'bg-gray-100 text-gray-700 border border-gray-300 hover:bg-gray-200'
            }`}
          >
            Weaviate
          </button>
        </div>
      </div>
      
      {error && (
        <div className="p-2 bg-red-50 border border-red-200 rounded text-red-600 text-sm">
          {error}
        </div>
      )}
      
      <div className="flex justify-end">
        <button
          type="submit"
          disabled={isQuerying || !query.trim()}
          className={`py-2 px-6 rounded-md text-white font-medium ${
            isQuerying || !query.trim()
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700'
          }`}
        >
          {isQuerying ? 'Processing...' : 'Submit Query'}
        </button>
      </div>
    </form>
  );
};

export default RagQueryForm;