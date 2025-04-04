import React from 'react';
import { DatabaseType } from '../types';

interface DatabaseOptionProps {
  name: string;
  value: DatabaseType;
  active: boolean;
  onClick: () => void;
  disabled?: boolean;
}

const DatabaseOption: React.FC<DatabaseOptionProps> = ({ name, value, active, onClick, disabled }) => (
  <button
    className={`px-4 py-2 rounded-md mx-1 my-1 ${
      active 
        ? 'bg-blue-600 text-white' 
        : 'bg-gray-200 text-gray-800 hover:bg-gray-300'
    } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
    onClick={onClick}
    disabled={disabled}
  >
    {name}
  </button>
);

interface DatabaseSelectorProps {
  activeDatabase: DatabaseType;
  setActiveDatabase: (db: DatabaseType) => void;
  availableDatabases: DatabaseType[];
  disabled?: boolean;
}

const DatabaseSelector: React.FC<DatabaseSelectorProps> = ({
  activeDatabase,
  setActiveDatabase,
  availableDatabases,
  disabled = false
}) => {
  return (
    <div className="flex flex-wrap justify-center mb-4">
      <DatabaseOption 
        name="FAISS" 
        value="faiss" 
        active={activeDatabase === 'faiss'} 
        onClick={() => setActiveDatabase('faiss')}
        disabled={disabled || !availableDatabases.includes('faiss')}
      />
      <DatabaseOption 
        name="ChromaDB" 
        value="chroma" 
        active={activeDatabase === 'chroma'} 
        onClick={() => setActiveDatabase('chroma')}
        disabled={disabled || !availableDatabases.includes('chroma')}
      />
      <DatabaseOption 
        name="Weaviate" 
        value="weaviate" 
        active={activeDatabase === 'weaviate'} 
        onClick={() => setActiveDatabase('weaviate')}
        disabled={disabled || !availableDatabases.includes('weaviate')}
      />
      {/* New database options */}
      <DatabaseOption 
        name="MongoDB" 
        value="mongo" 
        active={activeDatabase === 'mongo'} 
        onClick={() => setActiveDatabase('mongo')}
        disabled={disabled || !availableDatabases.includes('mongo')}
      />
      <DatabaseOption 
        name="pgvector" 
        value="pgvector" 
        active={activeDatabase === 'pgvector'} 
        onClick={() => setActiveDatabase('pgvector')}
        disabled={disabled || !availableDatabases.includes('pgvector')}
      />
      <DatabaseOption 
        name="Milvus" 
        value="milvus" 
        active={activeDatabase === 'milvus'} 
        onClick={() => setActiveDatabase('milvus')}
        disabled={disabled || !availableDatabases.includes('milvus')}
      />
    </div>
  );
};

export default DatabaseSelector;