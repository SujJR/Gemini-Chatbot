import time
import os
import json
from typing import List, Tuple
from langchain.schema import Document
import psycopg2
from psycopg2.extensions import STATUS_READY
from psycopg2.extras import execute_values, Json
import numpy as np
# Import register_vector from pgvector.psycopg2
from pgvector.psycopg2 import register_vector

# No manual adapter needed

class PGVectorStore:
    def __init__(self, embedding_model=None):
        self.embedding_model = embedding_model
        self.initialized = False
        self.conn = None
        # Use model's actual dimension
        self.embedding_dim = 768  # Default for Google embeddings
        
        try:
            # Get PostgreSQL credentials from environment variables
            db_host = os.getenv("DB_HOST")
            db_port = os.getenv("DB_PORT")
            db_user = os.getenv("DB_USER")
            db_password = os.getenv("DB_PASSWORD")
            db_name = os.getenv("DB_NAME")
            
            print(f"Connecting to PostgreSQL at {db_host}:{db_port}")
            
            # Connect to PostgreSQL
            self.conn = psycopg2.connect(
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_password,
                database=db_name,
                connect_timeout=10
            )
            self.conn.autocommit = False
            
            # Register the vector type handler with psycopg2
            try:
                register_vector(self.conn)
                print("✅ pgvector handler registered with psycopg2")
            except Exception as reg_error:
                print(f"❌ Error registering pgvector handler: {reg_error}")
                raise # Reraise error if registration fails, as it's critical

            # Get actual embedding dimension from the model
            if self.embedding_model:
                test_embedding = self.embedding_model.embed_query("test")
                self.embedding_dim = len(test_embedding)
                print(f"✅ Detected embedding dimension: {self.embedding_dim}")

            # Create vector extension if it doesn't exist
            with self.conn.cursor() as cur:
                try:
                    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                    self.conn.commit()
                    print("✅ Created or verified vector extension")
                except Exception as e:
                    print(f"❌ Error creating vector extension: {str(e)}")
                    self.conn.rollback()
                    raise
            
            # Check if table exists and verify its dimension
            table_exists = False
            current_dimension = None
            docs_count = 0
            
            with self.conn.cursor() as cur:
                try:
                    cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'document_chunks');")
                    table_exists = cur.fetchone()[0]
                    
                    if table_exists:
                        # Try to get the dimension
                        try:
                            cur.execute("SELECT array_length(embedding, 1) FROM document_chunks LIMIT 1;")
                            row = cur.fetchone()
                            if row and row[0]:
                                current_dimension = row[0]
                                print(f"Found existing table with dimension {current_dimension}")
                                
                                # Get document count
                                cur.execute("SELECT COUNT(*) FROM document_chunks;")
                                docs_count = cur.fetchone()[0]
                                print(f"Table has {docs_count} existing documents")
                        except Exception as dim_error:
                            print(f"Could not determine dimension of existing table: {str(dim_error)}")
                except Exception as e:
                    print(f"Error checking table existence: {str(e)}")
                    current_dimension = None
            
            # Determine if we need to recreate the table
            recreate_table = False
            if not table_exists:
                print("Table does not exist, will create it")
                recreate_table = True
            elif current_dimension != self.embedding_dim:
                print(f"⚠️ DIMENSION MISMATCH: Table has dimension {current_dimension}, but model uses {self.embedding_dim}")
                if docs_count > 0:
                    print(f"⚠️ WARNING: Recreating table will delete {docs_count} existing documents!")
                    print(f"⚠️ Documents will need to be re-uploaded")
                recreate_table = True
            
            # Recreate table if needed
            if recreate_table:
                with self.conn.cursor() as cur:
                    try:
                        print("🔄 Dropping document_chunks table to ensure correct dimensions")
                        cur.execute("DROP TABLE IF EXISTS document_chunks;")
                        self.conn.commit()
                        print("✅ Dropped table for recreation")
                    except Exception as e:
                        print(f"⚠️ Error dropping table: {str(e)}")
                        self.conn.rollback()
                
                # Create table with the correct dimensions
                with self.conn.cursor() as cur:
                    try:
                        # Ensure table definition uses the determined dimension
                        create_table_sql = f"""
                            CREATE TABLE IF NOT EXISTS document_chunks (
                                id SERIAL PRIMARY KEY,
                                content TEXT NOT NULL,
                                metadata JSONB,
                                embedding vector({self.embedding_dim})
                            );
                        """
                        print(f"Creating table with dimension {self.embedding_dim}")
                        cur.execute(create_table_sql)
                        self.conn.commit()
                        print(f"✅ Created document_chunks table with dimension {self.embedding_dim}")
                    except psycopg2.Error as e:
                        print(f"❌ Database error creating table: {str(e)}")
                        self.conn.rollback()
                        raise
            else:
                print(f"✅ Using existing table with correct dimension {self.embedding_dim}")
            
            # Create index for vector similarity search
            with self.conn.cursor() as cur:
                try:
                    # First check if index exists to avoid error
                    cur.execute("""
                        SELECT 1 FROM pg_indexes 
                        WHERE indexname = 'document_chunks_embedding_idx';
                    """)
                    if cur.fetchone() is None:  # Index doesn't exist
                        cur.execute("""
                            CREATE INDEX document_chunks_embedding_idx 
                            ON document_chunks 
                            USING ivfflat (embedding vector_cosine_ops)
                            WITH (lists = 100);
                        """)
                        self.conn.commit()
                        print("✅ Created vector search index")
                    else:
                        print("✅ Vector search index already exists")
                except Exception as e:
                    print(f"⚠️ Error creating index (non-critical): {str(e)}")
                    self.conn.rollback()
                    # Continue anyway, as this is not critical
            
            # Verify table exists and is accessible
            with self.conn.cursor() as cur:
                try:
                    cur.execute("SELECT COUNT(*) FROM document_chunks;")
                    count = cur.fetchone()[0]
                    print(f"✅ Connected to pgvector. Current document count: {count}")
                    self.initialized = True
                except Exception as e:
                    print(f"❌ Error verifying table: {str(e)}")
                    self.conn.rollback()
                    raise
            
        except Exception as e:
            print(f"❌ Error initializing pgvector: {str(e)}")
            self.initialized = False
            if self.conn:
                try:
                    self.conn.close()
                except:
                    pass
    
    def add_documents(self, documents: List[Document]) -> float:
        if not self.initialized:
            print("❌ Cannot add documents: pgvector not initialized")
            return 0.0
        
        start_time = time.time()
        added_count = 0
        print(f"Adding {len(documents)} documents to pgvector...")
        
        try:
            with self.conn.cursor() as cur:
                # Get initial count
                cur.execute("SELECT COUNT(*) FROM document_chunks;")
                initial_count = cur.fetchone()[0]
                print(f"Initial document count: {initial_count}")
                
                data = []
                for i, doc in enumerate(documents):
                    try:
                        if i % 50 == 0:
                            print(f"Processing document {i+1}/{len(documents)}...")
                            
                        # Get embedding from model - use actual dimensions
                        embedding = self.embedding_model.embed_query(doc.page_content)
                        
                        # Handle metadata - ensure it's JSON serializable
                        metadata = Json(doc.metadata if doc.metadata else {})
                        
                        # Add to batch insert
                        data.append((doc.page_content, metadata, embedding))
                        
                    except Exception as e:
                        print(f"❌ Error processing document {i+1} for add: {str(e)}")
                
                if data:
                    print(f"Inserting {len(data)} documents into pgvector...")
                    execute_values(
                        cur,
                        """
                        INSERT INTO document_chunks (content, metadata, embedding)
                        VALUES %s
                        """,
                        data
                    )
                    self.conn.commit()
                    added_count = len(data)
                    
                    # Verify documents were added
                    cur.execute("SELECT COUNT(*) FROM document_chunks;")
                    new_count = cur.fetchone()[0]
                    actual_added = new_count - initial_count
                    
                    if actual_added == added_count:
                        print(f"✅ Successfully added {added_count} documents to pgvector (verified)")
                    else:
                        print(f"⚠️ Expected to add {added_count} documents, but count increased by {actual_added}")
                else:
                    print("⚠️ No valid documents processed to add")
            
            return time.time() - start_time
            
        except psycopg2.Error as e:
            print(f"❌ Database error adding documents to pgvector: {str(e)}")
            if self.conn:
                try:
                    self.conn.rollback()
                    print("Rolled back transaction due to add error.")
                except Exception as rb_error:
                    print(f"⚠️ Error during rollback attempt after add error: {rb_error}")
            return 0.0
        except Exception as e:
            print(f"❌ Unexpected error adding documents to pgvector: {str(e)}")
            if self.conn:
                try: self.conn.rollback() 
                except Exception: pass
            return 0.0

    def query(self, query_text: str, top_k: int = 5) -> Tuple[float, List[Document]]:
        if not self.initialized:
            print("❌ Cannot query: pgvector not initialized")
            return 0.0, []
            
        start_time = time.time()
        out_docs = []
        
        try:
            # First check if we have any data in the table
            with self.conn.cursor() as cur:
                try:
                    cur.execute("SELECT COUNT(*) FROM document_chunks;")
                    count = cur.fetchone()[0]
                    if count == 0:
                        print("⚠️ pgvector database is empty - no documents to search")
                        print("   Please upload documents first.")
                        return time.time() - start_time, []
                    else:
                        print(f"pgvector database has {count} documents to search")
                except Exception as e:
                    print(f"❌ Error checking document count: {str(e)}")
                    self.conn.rollback()
            
            # Get query embedding
            print(f"Getting embedding for query: {query_text[:50]}...")
            query_emb = self.embedding_model.embed_query(query_text)
            print(f"Embedding dimension: {len(query_emb)}")
            
            with self.conn.cursor() as cur:
                # Reset transaction state if necessary
                if self.conn.status != STATUS_READY:
                     self.conn.rollback() 
                     print("Rolled back potentially aborted transaction before query.")
                     
                try:
                    # Use cosine similarity for vector search with parameter binding
                    query_sql = """
                        SELECT content, metadata, embedding <=> %s::vector AS distance
                        FROM document_chunks
                        WHERE embedding IS NOT NULL
                        ORDER BY embedding <=> %s::vector 
                        LIMIT %s
                    """
                    
                    # Pass embedding directly as parameter (twice - once for select, once for order by)
                    print("Executing vector search query...")
                    cur.execute(query_sql, (query_emb, query_emb, top_k))
                    
                    results = cur.fetchall()
                    print(f"Query returned {len(results)} results")
                    
                    # Show similarity scores for debugging
                    if results:
                        print("Similarity scores:")
                        for i, row in enumerate(results):
                            similarity = row[2] if len(row) > 2 else "unknown"
                            print(f"  Result {i+1}: distance={similarity}")
                    
                    # Convert results to Document objects
                    for row in results:
                        try:
                            content = row[0]
                            metadata = row[1] if row[1] else {}
                            
                            # Convert to Document object
                            doc = Document(page_content=content, metadata=metadata)
                            out_docs.append(doc)
                        except Exception as doc_error:
                            print(f"❌ Error processing result row: {str(doc_error)}")
                            
                    print(f"✅ Found {len(out_docs)} documents in pgvector")
                    
                except psycopg2.Error as db_error:
                    print(f"❌ Database error during vector search: {str(db_error)}")
                    self.conn.rollback() 
                    print("Rolled back transaction due to query error.")
                    
                except Exception as search_error:
                    print(f"❌ Unexpected error during vector search: {str(search_error)}")
                    try: self.conn.rollback() 
                    except Exception: pass
            
        except Exception as e:
            print(f"❌ Error querying pgvector (outer scope): {str(e)}")
            if self.conn:
                try: self.conn.rollback() 
                except Exception: pass
                     
        return time.time() - start_time, out_docs