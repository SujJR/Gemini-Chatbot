import os
import psycopg2
import uuid
import numpy as np
from sqlalchemy import create_engine, Column, String, Integer, Text, Float, ForeignKey, func
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from psycopg2.errors import OperationalError
from psycopg2.extensions import register_adapter, AsIs

Base = declarative_base()

# Create a psycopg2 adapter for numpy float32 data type
def adapt_numpy_float32(numpy_float32):
    return AsIs(float(numpy_float32))

# Register the adapter
register_adapter(np.float32, adapt_numpy_float32)

class Document(Base):
    """Document table for pgvector"""
    __tablename__ = 'documents'
    
    id = Column(UUID, primary_key=True, default=lambda: str(uuid.uuid4()))
    content = Column(Text, nullable=False)
    source = Column(String(255), nullable=True)
    page = Column(Integer, nullable=True)
    chunk_id = Column(Integer, nullable=True)
    # Define embedding as array data type in PostgreSQL
    embedding = Column(ARRAY(Float))

class PGVectorStore:
    """PostgreSQL pgvector store implementation"""
    
    def __init__(self, connection_string="postgresql://postgres:postgres@localhost:5432/vector_db"):
        """Initialize pgvector store"""
        # Extract username from connection string or use environment variable
        # The connection string format is: postgresql://username:password@host:port/dbname
        
        # Allow overriding with environment variables - support for Supabase PostgreSQL
        if "DB_HOST" in os.environ:
            host = os.environ.get("DB_HOST")
            port = os.environ.get("DB_PORT", "5432")
            user = os.environ.get("DB_USER", "postgres")
            password = os.environ.get("DB_PASSWORD", "")
            dbname = os.environ.get("DB_NAME", "postgres")
            connection_string = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
            print(f"Using Supabase PostgreSQL connection: postgresql://{user}:****@{host}:{port}/{dbname}")
        
        self.engine = None
        self.Session = None
        
        try:
            # Create SQLAlchemy engine
            self.engine = create_engine(connection_string)
            
            # Test connection before creating tables
            conn = self.engine.raw_connection()
            conn.close()
            
            # Create tables if they don't exist
            Base.metadata.create_all(self.engine)
            
            # Create session factory
            self.Session = sessionmaker(bind=self.engine)
            
            # Check if we are using Supabase or another PostgreSQL host
            is_supabase = "supabase.co" in connection_string
            
            # Skip vector extension and index setup for Supabase - they don't support
            # the pgvector extension with the ivfflat index type
            if not is_supabase:
                # Create pgvector extension if it doesn't exist
                # This requires the pgvector extension to be installed on PostgreSQL
                conn = self.engine.raw_connection()
                try:
                    with conn.cursor() as cur:
                        # First check if pgvector extension is available
                        cur.execute("SELECT COUNT(*) FROM pg_available_extensions WHERE name='vector';")
                        if cur.fetchone()[0] > 0:
                            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                            # Create index for vector similarity search
                            cur.execute("""
                            DO $$
                            BEGIN
                                IF NOT EXISTS (
                                    SELECT 1 FROM pg_indexes 
                                    WHERE indexname = 'embedding_idx'
                                ) THEN
                                    -- Create the index - using simpler cosine index
                                    EXECUTE 'CREATE INDEX IF NOT EXISTS embedding_idx ON documents USING gin (embedding);';
                                END IF;
                            END
                            $$;
                            """)
                            print("Created pgvector extension and index")
                        else:
                            print("WARNING: pgvector extension is not available on this PostgreSQL server")
                    conn.commit()
                except Exception as e:
                    print(f"Warning: Could not set up pgvector extension: {e}")
                    print("Continuing without vector search capability")
                finally:
                    conn.close()
            else:
                print("Detected Supabase PostgreSQL - skipping pgvector extension setup")
                
        except Exception as e:
            print(f"Error connecting to PostgreSQL: {e}")
            self.engine = None
            self.Session = None
    
    def add_document(self, document, embedding):
        """Add a document with its embedding to the vector store"""
        if self.Session is None:
            return False
        
        try:
            # Session for the current operation
            session = self.Session()
            
            # Convert embedding to a list of Python floats
            # Make sure we're using Python floats, not numpy floats
            embedding_list = [float(x) for x in embedding]
            
            # Extract content and metadata
            content = document.get("content", "")
            metadata = document.get("metadata", {})
            
            # Create new document
            new_doc = Document(
                content=content,
                source=metadata.get("source", ""),
                page=metadata.get("page", 0),
                chunk_id=metadata.get("chunk_id", 0),
                embedding=embedding_list
            )
            
            # Add and commit
            session.add(new_doc)
            session.commit()
            session.close()
            
            return True
            
        except Exception as e:
            print(f"Error adding document to pgvector: {e}")
            if session:
                session.rollback()
                session.close()
            return False
    
    def similarity_search(self, query, query_embedding, k=5):
        """Search for similar documents using vector similarity"""
        if self.Session is None:
            return []
            
        try:
            # Create session
            session = self.Session()
            
            # Convert query embedding to a list of Python floats
            pg_embedding = [float(x) for x in query_embedding]
            
            # Check if we are using Supabase (or can't use pgvector)
            is_supabase = False
            try:
                conn = self.engine.raw_connection()
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector';")
                    has_pgvector = cur.fetchone() is not None
                conn.close()
                
                if not has_pgvector:
                    is_supabase = True
            except:
                is_supabase = True
            
            if is_supabase:
                # Use basic filtering when pgvector is not available
                print("Using basic SQL similarity search (pgvector not available)")
                
                # Fetch all documents (with a limit)
                docs = session.query(Document).limit(100).all()
                
                # Calculate distances in Python (inefficient but works as fallback)
                results = []
                for doc in docs:
                    if doc.embedding:
                        # Calculate Euclidean distance
                        dist = sum((a - b) ** 2 for a, b in zip(pg_embedding, doc.embedding)) ** 0.5
                        results.append((doc, dist))
                
                # Sort by distance and take top k
                results.sort(key=lambda x: x[1])
                results = results[:k]
                
                # Format results
                documents = []
                for doc, distance in results:
                    documents.append({
                        "content": doc.content,
                        "metadata": {
                            "source": doc.source,
                            "page": doc.page,
                            "chunk_id": doc.chunk_id
                        },
                        "score": float(distance)
                    })
            else:
                # Use pgvector for similarity search
                # Execute SQL with a regular array comparison (less efficient but works)
                sql = """
                SELECT id, content, source, page, chunk_id, 
                      (embedding <-> :embedding) AS distance
                FROM documents
                ORDER BY distance ASC
                LIMIT :limit
                """
                
                result = session.execute(sql, {
                    "embedding": pg_embedding,
                    "limit": k
                })
                
                # Format results
                documents = []
                for row in result:
                    doc = {
                        "content": row.content,
                        "metadata": {
                            "source": row.source,
                            "page": row.page,
                            "chunk_id": row.chunk_id
                        },
                        "score": float(row.distance)
                    }
                    documents.append(doc)
                
            session.close()
            return documents
            
        except Exception as e:
            print(f"Error searching in pgvector: {e}")
            try:
                if self.Session is not None:
                    session = self.Session()
                    session.close()
            except:
                pass
            
            # Fallback: Return empty results
            return [] 