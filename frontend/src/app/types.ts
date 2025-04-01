export interface Message {
  text: string;
  sender: 'user' | 'bot';
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
}

export interface UploadResponse {
  success: boolean;
  message: string;
  document: {
    filename: string;
    chunk_count: number;
    indexing_times: IndexingTimes;
  };
}

export interface RagResponse {
  success: boolean;
  query: string;
  db_type: string;
  query_time: number;
  rag_response: string;
  retrieved_docs: DocumentResult[];
}

export type DatabaseType = 'faiss' | 'chroma' | 'weaviate';

export interface ComparisonResult {
  query: string;
  responses: Record<DatabaseType, RagResponse>;
  fastest: DatabaseType;
}