import React, { useState, useEffect } from 'react';
import { DatabaseType } from '../types';

interface RagQueryFormProps {
  onQueryComplete: (response: any) => void;
  isQuerying: boolean;
  setIsQuerying: (isQuerying: boolean) => void;
  // Add prop for available databases
  availableDatabases?: DatabaseType[];
  // Add prop for submitting queries
  onSubmitQuery: (query: string, dbType: DatabaseType, compareAll: boolean) => void;
}

const RagQueryForm: React.FC<RagQueryFormProps> = ({ 
  onQueryComplete, 
  isQuerying, 
  setIsQuerying,
  availableDatabases = ['faiss', 'chroma', 'weaviate', 'mongo', 'pgvector', 'milvus'],
  onSubmitQuery
}) => {
  const [query, setQuery] = useState('');
  const [selectedDatabase, setSelectedDatabase] = useState<DatabaseType>('faiss');
  const [compareAll, setCompareAll] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  
  // If the selected database becomes unavailable, switch to first available
  useEffect(() => {
    if (availableDatabases.length > 0 && !availableDatabases.includes(selectedDatabase)) {
      setSelectedDatabase(availableDatabases[0]);
    }
  }, [availableDatabases, selectedDatabase]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!query.trim()) {
      setError('Please enter a query');
      return;
    }
    
    setError(null);
    
    // Instead of making the API call directly, call the provided onSubmitQuery function
    onSubmitQuery(query, selectedDatabase, compareAll);
  };
  
  // Create a database button with consistent styling
  const DatabaseButton = ({ name, value }: { name: string, value: DatabaseType }) => (
    <button
      type="button"
      onClick={() => setSelectedDatabase(value)}
      disabled={!availableDatabases.includes(value) || compareAll}
      className={`py-2 px-3 rounded-md text-center text-sm font-medium ${
        selectedDatabase === value && !compareAll
          ? 'bg-blue-100 text-blue-700 border border-blue-300'
          : !availableDatabases.includes(value) || compareAll
            ? 'bg-gray-50 text-gray-400 border border-gray-200 cursor-not-allowed'
            : 'bg-gray-100 text-gray-700 border border-gray-300 hover:bg-gray-200'
      }`}
    >
      {name}
    </button>
  );

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
      
      <div className="flex items-center mb-4">
        <input
          id="compare-all"
          type="checkbox"
          checked={compareAll}
          onChange={(e) => setCompareAll(e.target.checked)}
          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
        />
        <label htmlFor="compare-all" className="ml-2 block text-sm font-medium text-gray-700">
          Compare All Available Databases
        </label>
        <span className="ml-2 bg-blue-50 text-blue-700 text-xs px-2 py-1 rounded-full font-medium">Recommended</span>
      </div>
      
      <div className={compareAll ? "opacity-50" : ""}>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Select Vector Database {compareAll && "(disabled when comparing all)"}:
        </label>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
          <DatabaseButton name="FAISS" value="faiss" />
          <DatabaseButton name="ChromaDB" value="chroma" />
          <DatabaseButton name="Weaviate" value="weaviate" />
          <DatabaseButton name="MongoDB" value="mongo" />
          <DatabaseButton name="pgVector" value="pgvector" />
          <DatabaseButton name="Milvus" value="milvus" />
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
          {isQuerying ? 'Processing...' : compareAll ? 'Compare All Databases' : 'Submit Query'}
        </button>
      </div>
    </form>
  );
};

export default RagQueryForm;