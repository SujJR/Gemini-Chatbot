#!/bin/bash

echo "=========================================================="
echo "Starting Gemini Chatbot Backend..."
echo "=========================================================="

# Create necessary directories first
echo "Creating required directories..."
mkdir -p uploads
mkdir -p storage/{faiss,chroma}

# Check if virtual environment exists
if [ ! -d "venv" ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv venv || { 
    echo "ERROR: Failed to create virtual environment. Make sure python3 and python3-venv are installed."; 
    echo "On macOS: brew install python3"
    echo "On Ubuntu: sudo apt install python3-venv"
    exit 1; 
  }
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate || { 
  echo "ERROR: Failed to activate virtual environment."; 
  exit 1; 
}

# Check Python version
python_version=$(python --version 2>&1)
echo "Using $python_version"

# Install requirements if needed
if [ ! -f "venv/.requirements_installed" ]; then
  echo "Installing Python requirements (this may take a minute)..."
  pip install -r requirements.txt || {
    echo "ERROR: Failed to install requirements. Check your internet connection and pip installation.";
    exit 1;
  }
  touch venv/.requirements_installed
  echo "Requirements installed successfully."
else
  echo "Python requirements already installed."
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
  echo "Creating default .env file..."
  cat > .env << EOF
# Required: Gemini API key
GOOGLE_API_KEY=your_gemini_api_key_here

# Optional: Cloud database credentials
# Weaviate
WEAVIATE_URL=https://your-cluster-id.weaviate.network
WEAVIATE_API_KEY=your-weaviate-api-key

# MongoDB Atlas
MONGO_USER=your_mongodb_user
MONGO_PASSWORD=your_mongodb_password
# For MongoDB Atlas, you can use either:
# 1. Just the cluster name (will use default domain):
MONGO_CLUSTER=cluster0
# 2. Or the full hostname from your connection string:
# MONGO_CLUSTER=cluster0.abcde.mongodb.net

# PostgreSQL with pgvector
DB_HOST=your-db-hostname.supabase.co
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_postgres_password
DB_NAME=postgres

# Milvus/Zilliz
MILVUS_URI=https://your-instance-id.cloud.zilliz.com
MILVUS_USER=your_milvus_user
MILVUS_PASSWORD=your_milvus_password
EOF
  echo "=========================================================="
  echo "IMPORTANT: Please edit the .env file with your API keys"
  echo "and credentials, then restart this script."
  echo "=========================================================="
  exit 1
fi

# Check if GOOGLE_API_KEY is set with a valid value in .env
GOOGLE_API_KEY=$(grep GOOGLE_API_KEY .env | cut -d= -f2)
if [ "$GOOGLE_API_KEY" = "your_gemini_api_key_here" ] || [ -z "$GOOGLE_API_KEY" ]; then
  echo "=========================================================="
  echo "ERROR: You need to set your GOOGLE_API_KEY in the .env file"
  echo "Get a key at: https://ai.google.dev/"
  echo "Then edit the .env file and restart this script"
  echo "=========================================================="
  exit 1
fi

# Check Python packages
echo "Verifying dependencies..."
python -c "import google.generativeai" 2>/dev/null || {
  echo "ERROR: google-generativeai package not found. Try reinstalling requirements:";
  echo "pip install -r requirements.txt";
  exit 1;
}

# Load environment variables
echo "Loading environment variables from .env file..."
export $(grep -v '^#' .env | xargs)

# Start the server
echo "=========================================================="
echo "Starting backend server at http://localhost:5001"
echo "Press Ctrl+C to stop the server"
echo "=========================================================="
export PORT=5001
python app.py 