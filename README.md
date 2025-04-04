# Gemini Chatbot with Vector Database Comparison

This project implements a RAG (Retrieval Augmented Generation) chatbot using Gemini AI, with support for multiple vector databases for document storage and retrieval.

## Features

- Chat interface with Gemini AI model
- Document upload and indexing
- RAG queries with context from stored documents
- Multiple vector database support:
  - FAISS (local)
  - ChromaDB (local)
  - Weaviate (cloud)
  - MongoDB Atlas (cloud)
  - PostgreSQL with pgvector (cloud)
  - Milvus/Zilliz (cloud)
- Database performance comparison
- JSON-RPC based communication between frontend and backend

## Setup

### Prerequisites

- Node.js 16+
- Python 3.9+
- Google Gemini API key

### Backend Setup

1. Navigate to the backend directory:
   ```
   cd backend
   ```

2. Create a virtual environment (optional but recommended):
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Create a `.env` file with your API keys and database credentials:
   ```
   # Gemini API key (required)
   GOOGLE_API_KEY=your_gemini_api_key_here
   
   # Cloud database credentials (optional)
   WEAVIATE_URL=your_weaviate_url
   WEAVIATE_API_KEY=your_weaviate_api_key
   
   MONGO_USER=your_mongodb_user
   MONGO_PASSWORD=your_mongodb_password
   MONGO_CLUSTER=your_mongodb_cluster
   
   DB_HOST=your_postgres_host
   DB_PORT=5432
   DB_USER=your_postgres_user
   DB_PASSWORD=your_postgres_password
   DB_NAME=your_postgres_database
   
   MILVUS_URI=your_milvus_uri
   MILVUS_USER=your_milvus_user
   MILVUS_PASSWORD=your_milvus_password
   ```

4. Start the backend:
   ```
   ./start.sh
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```
   cd frontend
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Create a `.env.local` file (optional, created automatically by start.sh):
   ```
   NEXT_PUBLIC_API_URL=http://localhost:5000/rpc
   ```

4. Start the frontend:
   ```
   ./start.sh
   ```

5. Open your browser and go to http://localhost:3000
Here are some of the screenshots of the outcome.

Old Attachments:
<br />

<img width="1465" alt="Screenshot 2025-04-04 at 5 45 52 AM" src="https://github.com/user-attachments/assets/0a1a7dac-bc3f-4211-a94e-9ece6b08616e" />
<img width="1465" alt="Screenshot 2025-04-04 at 5 13 43 AM" src="https://github.com/user-attachments/assets/d4bfd93b-ed6a-4fbc-a24d-b1683ff6d851" />
<img width="206" alt="Screenshot 2025-04-04 at 5 11 50 AM" src="https://github.com/user-attachments/assets/663c7c77-1f1e-4bd2-9008-dc454ccfcd1a" />
<img width="206" alt="Screenshot 2025-04-04 at 5 11 38 AM" src="https://github.com/user-attachments/assets/579010f0-526e-4301-9e31-3b7b73e0dc59" />

<br />
<br />
<br />
<br />
<br />
New Attachments with RPC Implementation:
<br />

<img width="1465" alt="Screenshot 2025-04-04 at 8 17 17 PM" src="https://github.com/user-attachments/assets/3e4b8117-f821-4a74-b6ee-3e8b56b9b5b5" />
<img width="1465" alt="Screenshot 2025-04-04 at 8 11 40 PM" src="https://github.com/user-attachments/assets/67bdb712-98d4-4d37-9611-4acdb66d4ef0" />






