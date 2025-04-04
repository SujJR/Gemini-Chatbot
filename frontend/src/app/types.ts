export interface Message {
  id?: string;
  text?: string;
  content?: string;
  sender: 'user' | 'bot' | 'system' | 'assistant';
  timestamp?: string;
}

export interface DocumentResult {
  content: string;
  metadata: {
    source?: string;
    page?: number;
    [key: string]: any;
  };
}

export interface IndexingTimes {
  faiss: number;
  chroma: number;
  weaviate: number;
  mongo: number;   // Added MongoDB
  pgvector: number;  // Added pgvector
  milvus: number;  // Added Milvus
}

export interface UploadResponse {
  success: boolean;
  message: string;
  document: {
    filename: string;
    chunk_count: number;
    indexing_times: IndexingTimes;
    available_dbs: {
      faiss: boolean;
      chroma: boolean;
      weaviate: boolean;
      mongo: boolean;    // Added MongoDB availability flag
      pgvector: boolean; // Added pgvector availability flag
      milvus: boolean;   // Added Milvus availability flag
    };
  };
}

export interface DatabaseResult {
  name: string;
  query_time?: number;
  retrieved_docs?: DocumentResult[];
  error?: string;
}

export interface RagResponse {
  success: boolean;
  query: string;
  db_type: string;
  query_time: number;
  rag_response: string;
  retrieved_docs: DocumentResult[];
  message?: string;  // Optional message property for error cases
  compare_all?: boolean; // Whether this is a comparison of all databases
  results?: Record<string, DatabaseResult>; // Results from each database when compare_all is true
  best_db?: string; // The ID of the best performing database
}

// Update the DatabaseType to include the new databases
export type DatabaseType = 'faiss' | 'chroma' | 'weaviate' | 'mongo' | 'pgvector' | 'milvus';

export interface ComparisonResult {
  query: string;
  responses: Record<DatabaseType, RagResponse>;
  fastest: DatabaseType;
}