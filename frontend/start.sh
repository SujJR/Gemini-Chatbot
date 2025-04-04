#!/bin/bash

# Start script for Gemini Chatbot Frontend

echo "Starting Gemini Chatbot Frontend"

# Check if .env.local file exists
if [ ! -f ".env.local" ]; then
  echo "Creating .env.local file with default settings..."
  cat > .env.local << EOF
# Backend API URL for RPC calls
NEXT_PUBLIC_API_URL=http://localhost:5001/rpc

# Gemini API key (if needed on frontend)
# NEXT_PUBLIC_GEMINI_API_KEY=your-api-key-here
EOF
fi

# Check if node_modules exists, if not install dependencies
if [ ! -d "node_modules" ]; then
  echo "Installing dependencies..."
  npm install
fi

# Run the development server
echo "Starting Next.js development server..."
echo "The frontend will be available at http://localhost:3000"
echo "Press Ctrl+C to stop the server"

npm run dev 