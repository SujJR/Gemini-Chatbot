"use client";

import { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Message as MessageType, UploadResponse, RagResponse, DatabaseType, ComparisonResult } from './types';
import Message from './components/Message';
import DocumentUpload from './components/DocumentUpload';
import ChatInput from './components/ChatInput';
import RagResults from './components/RagResults';

export default function Home() {
  // Chat-related states
  const [messages, setMessages] = useState<MessageType[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // RAG-related states
  const [uploadStatus, setUploadStatus] = useState<UploadResponse | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [currentQuery, setCurrentQuery] = useState<string>('');
  const [activeDatabase, setActiveDatabase] = useState<DatabaseType>('faiss');
  const [ragResponses, setRagResponses] = useState<Record<DatabaseType, RagResponse | null>>({
    faiss: null,
    chroma: null,
    weaviate: null
  });
  const [comparisonResult, setComparisonResult] = useState<ComparisonResult | null>(null);
  const [isQuerying, setIsQuerying] = useState(false);
  
  // Tab management
  const [activeTab, setActiveTab] = useState<'chat' | 'rag'>('chat');

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async (messageText: string) => {
    // Add user message to chat
    const userMessage: MessageType = { text: messageText, sender: 'user' };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      // Send message to backend
      const response = await axios.post('http://localhost:5000/api/chat', {
        message: messageText
      });

      // Add bot response to chat
      if (response.data.success) {
        const botMessage: MessageType = {
          text: response.data.response,
          sender: 'bot'
        };
        setMessages(prev => [...prev, botMessage]);
      } else {
        const errorMessage: MessageType = {
          text: `Error: ${response.data.error || 'Unknown error'}`,
          sender: 'bot'
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    } catch (error) {
      console.error('Error:', error);
      const errorMessage: MessageType = {
        text: 'Sorry, there was an error processing your request.',
        sender: 'bot'
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle document upload completion
  const handleUploadComplete = (response: UploadResponse) => {
    setUploadStatus(response);
    
    // Find fastest database
    const times = response.document.indexing_times;
    const fastest = Object.entries(times).reduce(
      (fastest, [db, time]) => time < fastest.time ? {db, time} : fastest,
      { db: 'none', time: Infinity }
    );
    
    setMessages(prev => [
      ...prev,
      {
        text: `Successfully uploaded document: ${response.document.filename}. 
        The document has been indexed in all three vector databases.
        
        Indexing times:
        - FAISS: ${times.faiss.toFixed(4)}s
        - ChromaDB: ${times.chroma.toFixed(4)}s
        - Weaviate: ${times.weaviate.toFixed(4)}s
        
        Fastest database: ${fastest.db.toUpperCase()} (${fastest.time.toFixed(4)}s)
        
        You can now ask questions about this document using the RAG query interface.`,
        sender: 'bot'
      }
    ]);
  };

  // Handle RAG query submission for a single database
  const handleRagQuery = async (query: string, dbType: DatabaseType) => {
    setIsQuerying(true);
    setCurrentQuery(query);
    
    // Add query to message history
    setMessages(prev => [
      ...prev,
      {
        text: `Query using ${dbType.toUpperCase()}: ${query}`,
        sender: 'user'
      }
    ]);

    try {
      const response = await axios.post<RagResponse>('http://localhost:5000/api/rag', {
        query,
        db_type: dbType
      });

      if (response.data.success) {
        // Update responses state
        setRagResponses(prev => ({
          ...prev,
          [dbType]: response.data
        }));
        
        // Add response to chat
        setMessages(prev => [
          ...prev,
          {
            text: `${dbType.toUpperCase()} (${response.data.query_time.toFixed(4)}s): ${response.data.rag_response}`,
            sender: 'bot'
          }
        ]);
      } else {
        setMessages(prev => [
          ...prev,
          {
            text: `Error querying ${dbType.toUpperCase()}: ${response.data.message || 'Unknown error'}`,
            sender: 'bot'
          }
        ]);
      }
    } catch (error) {
      console.error('RAG query error:', error);
      setMessages(prev => [
        ...prev,
        {
          text: `Error querying ${dbType.toUpperCase()}: Request failed`,
          sender: 'bot'
        }
      ]);
    } finally {
      setIsQuerying(false);
    }
  };
  
  // Comparison handler for running the same query against all databases
  const handleCompareAllDatabases = async (query: string) => {
    setIsQuerying(true);
    setCurrentQuery(query);
    setComparisonResult(null);
    
    // Add query to message history
    setMessages(prev => [
      ...prev,
      {
        text: `Comparing all databases for query: ${query}`,
        sender: 'user'
      }
    ]);
    
    const allResponses: Record<DatabaseType, RagResponse> = {} as Record<DatabaseType, RagResponse>;
    const databases: DatabaseType[] = ['faiss', 'chroma', 'weaviate'];
    
    try {
      // Run queries in parallel against all databases
      const results = await Promise.all(
        databases.map(db => 
          axios.post<RagResponse>('http://localhost:5000/api/rag', { query, db_type: db })
        )
      );
      
      // Process results
      results.forEach((response, index) => {
        if (response.data.success) {
          const dbType = databases[index] as DatabaseType;
          allResponses[dbType] = response.data;
        }
      });
      
      // Find fastest database
      let fastest: DatabaseType = 'faiss';
      let fastestTime = Infinity;
      
      for (const [db, response] of Object.entries(allResponses)) {
        if (response.query_time < fastestTime) {
          fastest = db as DatabaseType;
          fastestTime = response.query_time;
        }
      }
      
      // Set comparison result
      setComparisonResult({
        query,
        responses: allResponses,
        fastest
      });
      
      // Add summary message to chat
      const comparisonMessage = `
Database Comparison Results:
${databases.map(db => 
  `- ${db.toUpperCase()}: ${allResponses[db]?.query_time.toFixed(4)}s`
).join('\n')}

Fastest database: ${fastest.toUpperCase()} (${allResponses[fastest]?.query_time.toFixed(4)}s)

Response from fastest database (${fastest.toUpperCase()}):
${allResponses[fastest]?.rag_response}
      `;
      
      setMessages(prev => [
        ...prev,
        {
          text: comparisonMessage,
          sender: 'bot'
        }
      ]);
      
      // Update individual responses state
      setRagResponses(allResponses);
      
    } catch (error) {
      console.error('Comparison error:', error);
      setMessages(prev => [
        ...prev,
        {
          text: 'Error comparing databases. Please try again.',
          sender: 'bot'
        }
      ]);
    } finally {
      setIsQuerying(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm p-4">
        <div className="container mx-auto flex justify-between items-center">
          <h1 className="text-xl font-bold">Vector Database RAG Comparison</h1>
          
          {/* Tab selector */}
          <div className="flex space-x-2">
            <button 
              onClick={() => setActiveTab('chat')}
              className={`px-3 py-2 rounded-md ${activeTab === 'chat' 
                ? 'bg-blue-600 text-white' 
                : 'bg-gray-200 text-gray-800'}`}
            >
              Chat
            </button>
            <button 
              onClick={() => setActiveTab('rag')}
              className={`px-3 py-2 rounded-md ${activeTab === 'rag' 
                ? 'bg-blue-600 text-white' 
                : 'bg-gray-200 text-gray-800'}`}
            >
              RAG Query
            </button>
          </div>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Main content */}
        <div className="flex-1 flex flex-col">
          {/* Messages container */}
          <div className="flex-1 overflow-y-auto p-4">
            {messages.map((message, index) => (
              <Message key={index} message={message} />
            ))}
            <div ref={messagesEndRef} />
            
            {isLoading && (
              <div className="flex justify-center my-4">
                <div className="animate-pulse text-gray-500">Processing...</div>
              </div>
            )}
          </div>

          {/* Input area */}
          <div className="p-4 border-t">
            {activeTab === 'chat' ? (
              <ChatInput 
                onSendMessage={handleSendMessage} 
                isLoading={isLoading} 
                placeholder="Type a message..."
              />
            ) : (
              <div className="space-y-4">
                <ChatInput 
                  onSendMessage={(query) => handleRagQuery(query, activeDatabase)}
                  isLoading={isQuerying}
                  placeholder={`Ask a question about the document using ${activeDatabase.toUpperCase()}...`}
                  buttonText={`Query with ${activeDatabase.toUpperCase()}`}
                />
                
                <div className="flex space-x-2 mt-2">
                  <button
                    onClick={() => setActiveDatabase('faiss')}
                    className={`px-3 py-2 text-sm rounded-md flex-1 ${
                      activeDatabase === 'faiss' 
                        ? 'bg-blue-100 text-blue-800 border border-blue-300' 
                        : 'bg-gray-100 text-gray-700'
                    }`}
                    disabled={isQuerying}
                  >
                    FAISS
                  </button>
                  <button
                    onClick={() => setActiveDatabase('chroma')}
                    className={`px-3 py-2 text-sm rounded-md flex-1 ${
                      activeDatabase === 'chroma' 
                        ? 'bg-blue-100 text-blue-800 border border-blue-300' 
                        : 'bg-gray-100 text-gray-700'
                    }`}
                    disabled={isQuerying}
                  >
                    ChromaDB
                  </button>
                  <button
                    onClick={() => setActiveDatabase('weaviate')}
                    className={`px-3 py-2 text-sm rounded-md flex-1 ${
                      activeDatabase === 'weaviate' 
                        ? 'bg-blue-100 text-blue-800 border border-blue-300' 
                        : 'bg-gray-100 text-gray-700'
                    }`}
                    disabled={isQuerying}
                  >
                    Weaviate
                  </button>
                </div>
                
                <div className="mt-2">
                  <button
                    onClick={() => currentQuery && handleCompareAllDatabases(currentQuery)}
                    className="w-full px-3 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-400 disabled:opacity-50"
                  >
                    Compare All Databases
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Sidebar */}
        <div className="w-80 bg-white shadow-md border-l p-4 overflow-y-auto">
          <h2 className="text-lg font-bold mb-4">Document Management</h2>
          
          <DocumentUpload 
            onUploadComplete={handleUploadComplete} 
            isUploading={isUploading}
            setIsUploading={setIsUploading}
          />
          
          {uploadStatus && (
            <div className="mt-6">
              <h3 className="font-medium text-gray-700 mb-2">Current Document</h3>
              <div className="p-3 border rounded-md bg-gray-50">
                <div className="font-medium truncate">{uploadStatus.document.filename}</div>
                <div className="text-sm text-gray-500 mt-1">
                  {uploadStatus.document.chunk_count} chunks indexed
                </div>
              </div>
              
              <div className="mt-4">
                <h3 className="font-medium text-gray-700 mb-2">Indexing Performance</h3>
                {Object.entries(uploadStatus.document.indexing_times).map(([db, time]) => (
                  <div key={db} className="flex justify-between items-center py-1">
                    <span className="font-medium capitalize">{db}</span>
                    <span className="text-gray-700">{time.toFixed(4)}s</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {comparisonResult && (
            <div className="mt-6">
              <h3 className="font-medium text-gray-700 mb-2">Query Performance</h3>
              {Object.entries(comparisonResult.responses).map(([db, response]) => (
                <div key={db} className={`flex justify-between items-center py-1 ${
                  db === comparisonResult.fastest ? 'font-medium text-green-600' : ''
                }`}>
                  <span className="capitalize">
                    {db === comparisonResult.fastest && '🏆 '}
                    {db}
                  </span>
                  <span>{response.query_time.toFixed(4)}s</span>
                </div>
              ))}
            </div>
          )}
          
          {ragResponses[activeDatabase] && (
            <div className="mt-6">
              <h3 className="font-medium text-gray-700 mb-2">Retrieved Documents</h3>
              <RagResults 
                results={ragResponses[activeDatabase]!.retrieved_docs} 
                queryTime={ragResponses[activeDatabase]!.query_time} 
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}