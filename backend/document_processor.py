import os
import time
import pypdf
from pathlib import Path
import traceback # Import traceback for detailed error logging

# Helper function to safely get environment variables
def get_env_var(var_name):
    return os.environ.get(var_name)

def extract_text_from_pdf(file_path):
    """Extract text from a PDF file"""
    text = ""
    print(f"  Extracting text from: {file_path}")
    try:
        with open(file_path, 'rb') as file:
            reader = pypdf.PdfReader(file)
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                text += page.extract_text() + "\n\n"
        print(f"  Extracted {len(text)} characters.")
        return text
    except Exception as e:
        print(f"  ❌ Error extracting text from PDF: {e}")
        print(traceback.format_exc()) # Log stack trace
        return ""

def split_text_into_chunks(text, chunk_size=1000, overlap=200):
    """Split text into overlapping chunks of approximately equal size"""
    print(f"  Splitting text into chunks (size={chunk_size}, overlap={overlap})")
    if not text:
        print("  ❌ Cannot split empty text.")
        return []
    
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        # Find the end of the current chunk
        end = min(start + chunk_size, text_length)
        
        # If we're not at the end of the text, try to find a good breaking point
        if end < text_length:
            # Try to find the last period, newline, or space to break on
            for char in ['. ', '\n', ' ']:
                pos = text.rfind(char, start, end)
                if pos != -1:
                    end = pos + 1
                    break
        
        # Add this chunk to our list
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append(chunk_text)
        
        # Move the start position for the next chunk, considering overlap
        start = end - overlap if end < text_length else text_length
    
    print(f"  Split into {len(chunks)} chunks.")
    return chunks

def process_document(file_path, get_embedding_fn):
    """Process a document: extract text, create chunks, and index into vector stores"""
    print("Starting document processing pipeline...")
    try:
        # Extract text from PDF
        text = extract_text_from_pdf(file_path)
        
        if not text or len(text) < 10:
            print("❌ PDF text extraction failed or text too short.")
            return {"success": False, "message": "Could not extract sufficient text from the PDF file"}
            
        # Split text into chunks
        document_chunks = split_text_into_chunks(text)
        
        if not document_chunks or len(document_chunks) == 0:
            print("❌ Document splitting failed.")
            return {"success": False, "message": "Failed to process document into text chunks"}
            
        # Initialize timing dictionary
        indexing_times = {
            "faiss": -1,
            "chroma": -1,
            "weaviate": -1,
            "mongo": -1,
            "pgvector": -1,
            "milvus": -1
        }
        
        # Track available databases
        available_dbs = {
            "faiss": False,
            "chroma": False,
            "weaviate": False,
            "mongo": False,
            "pgvector": False,
            "milvus": False
        }
        
        # Process chunks and prepare for indexing
        print("  Preparing document chunks for indexing...")
        processed_chunks = []
        for i, chunk in enumerate(document_chunks):
            doc = {
                "content": chunk,
                "metadata": {
                    "source": Path(file_path).name,
                    "chunk_id": i,
                    "page": i // 2  # Approximate page number
                }
            }
            processed_chunks.append(doc)
        print(f"  Prepared {len(processed_chunks)} chunks.")
        
        # Create a cache for embeddings to avoid recomputing
        print("  Creating embedding cache...")
        embedding_cache = {}
        def get_embedding_cached(text_to_embed):
            if text_to_embed not in embedding_cache:
                print(f"    Generating embedding for chunk hash: {hash(text_to_embed)}")
                embedding_cache[text_to_embed] = get_embedding_fn(text_to_embed)
            return embedding_cache[text_to_embed]
        
        # Index into each vector store
        print("  Starting indexing process...")
        
        # FAISS (local)
        try:
            from vectorstores.faiss_store import FAISSVectorStore
            faiss_store = FAISSVectorStore()
            start_time = time.time()
            print("    Indexing into FAISS...")
            for doc in processed_chunks:
                embedding = get_embedding_cached(doc["content"])
                if not faiss_store.add_document(doc, embedding):
                    print(f"    ⚠️ Failed to add document chunk {doc['metadata']['chunk_id']} to FAISS")
            indexing_times["faiss"] = time.time() - start_time
            available_dbs["faiss"] = True
            print(f"    ✅ FAISS indexing successful: {len(processed_chunks)} chunks in {indexing_times['faiss']:.2f}s (local)")
        except ImportError:
            print("    ⚠️ Skipping FAISS: faiss_store library not found.")
        except Exception as e:
            print(f"    ❌ Error indexing in FAISS: {e}")
            print(traceback.format_exc())
        
        # ChromaDB (local)
        try:
            from vectorstores.chroma_store import ChromaVectorStore
            chroma_store = ChromaVectorStore()
            start_time = time.time()
            print("    Indexing into ChromaDB...")
            for doc in processed_chunks:
                embedding = get_embedding_cached(doc["content"])
                if not chroma_store.add_document(doc, embedding):
                    print(f"    ⚠️ Failed to add document chunk {doc['metadata']['chunk_id']} to ChromaDB")
            indexing_times["chroma"] = time.time() - start_time
            available_dbs["chroma"] = True
            print(f"    ✅ ChromaDB indexing successful: {len(processed_chunks)} chunks in {indexing_times['chroma']:.2f}s (local)")
        except ImportError:
             print("    ⚠️ Skipping ChromaDB: chroma_store library not found.")
        except Exception as e:
            print(f"    ❌ Error indexing in ChromaDB: {e}")
            print(traceback.format_exc())
        
        # Weaviate (cloud)
        weaviate_url = get_env_var("WEAVIATE_URL")
        weaviate_api_key = get_env_var("WEAVIATE_API_KEY")
        if weaviate_url and weaviate_api_key:
            try:
                from vectorstores.weaviate_store import WeaviateVectorStore
                weaviate_store = WeaviateVectorStore(url=weaviate_url, api_key=weaviate_api_key)
                if weaviate_store.client is not None:
                    start_time = time.time()
                    print("    Indexing into Weaviate...")
                    for doc in processed_chunks:
                        embedding = get_embedding_cached(doc["content"])
                        if not weaviate_store.add_document(doc, embedding):
                            print(f"    ⚠️ Failed to add document chunk {doc['metadata']['chunk_id']} to Weaviate")
                    indexing_times["weaviate"] = time.time() - start_time
                    available_dbs["weaviate"] = True
                    print(f"    ✅ Weaviate indexing successful: {len(processed_chunks)} chunks in {indexing_times['weaviate']:.2f}s (cloud)")
                else:
                    print("    ⚠️ Skipping Weaviate: Client initialization failed.")
            except ImportError:
                print("    ⚠️ Skipping Weaviate: weaviate_store library not found.")
            except Exception as e:
                print(f"    ❌ Error indexing in Weaviate: {e}")
                print(traceback.format_exc())
        else:
            print("    ⚠️ Skipping Weaviate: No URL or API key provided in .env")
        
        # MongoDB (cloud)
        mongo_user = get_env_var("MONGO_USER")
        mongo_password = get_env_var("MONGO_PASSWORD")
        mongo_cluster = get_env_var("MONGO_CLUSTER")
        if mongo_user and mongo_password and mongo_cluster:
            try:
                from vectorstores.mongodb_store import MongoDBVectorStore
                # Construct connection string here, assuming app.py logic handles it
                if "mongodb.net" in mongo_cluster.lower():
                    mongodb_uri = f"mongodb+srv://{mongo_user}:{mongo_password}@{mongo_cluster}/?retryWrites=true&w=majority"
                else:
                     mongodb_uri = f"mongodb://{mongo_user}:{mongo_password}@{mongo_cluster}:27017/?authSource=admin"
                
                mongo_store = MongoDBVectorStore(connection_string=mongodb_uri)
                if mongo_store.collection is not None:
                    start_time = time.time()
                    print("    Indexing into MongoDB...")
                    for doc in processed_chunks:
                        embedding = get_embedding_cached(doc["content"])
                        if not mongo_store.add_document(doc, embedding):
                             print(f"    ⚠️ Failed to add document chunk {doc['metadata']['chunk_id']} to MongoDB")
                    indexing_times["mongo"] = time.time() - start_time
                    available_dbs["mongo"] = True
                    print(f"    ✅ MongoDB indexing successful: {len(processed_chunks)} chunks in {indexing_times['mongo']:.2f}s (cloud)")
                else:
                    print("    ⚠️ Skipping MongoDB: Collection initialization failed.")
            except ImportError:
                 print("    ⚠️ Skipping MongoDB: mongodb_store library not found.")
            except Exception as e:
                print(f"    ❌ Error indexing in MongoDB: {e}")
                print(traceback.format_exc())
        else:
            print("    ⚠️ Skipping MongoDB: No credentials provided in .env")
        
        # pgvector (cloud)
        db_host = get_env_var("DB_HOST")
        db_user = get_env_var("DB_USER")
        db_password = get_env_var("DB_PASSWORD")
        if db_host and db_user and db_password:
            try:
                from vectorstores.pgvector_store import PGVectorStore
                db_port = get_env_var("DB_PORT") or "5432"
                db_name = get_env_var("DB_NAME") or "postgres"
                postgres_uri = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
                pgvector_store = PGVectorStore(connection_string=postgres_uri)
                if pgvector_store.Session is not None:
                    start_time = time.time()
                    print("    Indexing into pgvector...")
                    for doc in processed_chunks:
                        embedding = get_embedding_cached(doc["content"])
                        if not pgvector_store.add_document(doc, embedding):
                            print(f"    ⚠️ Failed to add document chunk {doc['metadata']['chunk_id']} to pgvector")
                    indexing_times["pgvector"] = time.time() - start_time
                    available_dbs["pgvector"] = True
                    print(f"    ✅ pgvector indexing successful: {len(processed_chunks)} chunks in {indexing_times['pgvector']:.2f}s (cloud)")
                else:
                    print("    ⚠️ Skipping pgvector: Session initialization failed.")
            except ImportError:
                print("    ⚠️ Skipping pgvector: pgvector_store library not found.")
            except Exception as e:
                print(f"    ❌ Error indexing in pgvector: {e}")
                print(traceback.format_exc())
        else:
            print("    ⚠️ Skipping pgvector: No credentials provided in .env")
        
        # Milvus (cloud)
        milvus_uri = get_env_var("MILVUS_URI")
        milvus_user = get_env_var("MILVUS_USER")
        milvus_password = get_env_var("MILVUS_PASSWORD")
        if milvus_uri and milvus_user and milvus_password:
            try:
                from vectorstores.milvus_store import MilvusVectorStore
                milvus_store = MilvusVectorStore(uri=milvus_uri, user=milvus_user, password=milvus_password)
                if milvus_store.initialized:
                    start_time = time.time()
                    print("    Indexing into Milvus...")
                    for doc in processed_chunks:
                        embedding = get_embedding_cached(doc["content"])
                        if not milvus_store.add_document(doc, embedding):
                            print(f"    ⚠️ Failed to add document chunk {doc['metadata']['chunk_id']} to Milvus")
                    indexing_times["milvus"] = time.time() - start_time
                    available_dbs["milvus"] = True
                    print(f"    ✅ Milvus indexing successful: {len(processed_chunks)} chunks in {indexing_times['milvus']:.2f}s (cloud)")
                else:
                     print("    ⚠️ Skipping Milvus: Client initialization failed.")
            except ImportError:
                 print("    ⚠️ Skipping Milvus: milvus_store library not found.")
            except Exception as e:
                print(f"    ❌ Error indexing in Milvus: {e}")
                print(traceback.format_exc())
        else:
            print("    ⚠️ Skipping Milvus: No credentials provided in .env")
        
        print("Indexing process finished.")
        if not any(available_dbs.values()):
            print("⚠️ Warning: No vector databases were successfully indexed")
            # Return an error if indexing failed completely
            return {"success": False, "message": "Indexing failed for all databases."} 
        
        # Return success with timing metrics
        return {
            "success": True,
            "message": "Document processed and indexed successfully",
            "document": {
                "filename": Path(file_path).name,
                "chunk_count": len(document_chunks),
                "indexing_times": indexing_times,
                "available_dbs": available_dbs
            }
        }
    
    except Exception as e:
        print(f"❌ Unhandled error during document processing: {e}")
        print(traceback.format_exc()) # Log the full stack trace
        return {"success": False, "message": f"Document processing failed: {e}"} 