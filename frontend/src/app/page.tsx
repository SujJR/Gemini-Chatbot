"use client";

import { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Message as MessageType, UploadResponse, RagResponse, DatabaseType, ComparisonResult } from './types';
import Message from './components/Message';
import DocumentUpload from './components/DocumentUpload';
import ChatInput from './components/ChatInput';
import RagResults from './components/RagResults';
import RagQueryForm from './components/RagQueryForm';
import rpcClient from './rpc_client';

export default function Home() {
  // Chat-related states
  const [messages, setMessages] = useState<MessageType[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [availableDatabases, setAvailableDatabases] = useState<DatabaseType[]>(['faiss', 'chroma']);

  // RAG-related states
  const [uploadStatus, setUploadStatus] = useState<UploadResponse | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [currentQuery, setCurrentQuery] = useState<string>('');
  const [activeDatabase, setActiveDatabase] = useState<DatabaseType>('faiss');
  const [ragResponses, setRagResponses] = useState<Record<DatabaseType, RagResponse | null>>({
    faiss: null,
    chroma: null,
    weaviate: null,
    mongo: null,
    pgvector: null,
    milvus: null
  });
  const [comparisonResult, setComparisonResult] = useState<ComparisonResult | null>(null);
  const [isQuerying, setIsQuerying] = useState(false);
  
  // Tab management
  const [activeTab, setActiveTab] = useState<'chat' | 'rag'>('chat');

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const [serverStatus, setServerStatus] = useState<'checking' | 'online' | 'offline'>('checking');
  const [connectionError, setConnectionError] = useState<string | null>(null);

  // Check backend connectivity on component mount
  useEffect(() => {
    async function checkServerConnectivity() {
      try {
        setServerStatus('checking');
        setConnectionError(null);
        
        // Try to ping the server
        const isOnline = await rpcClient.ping();
        
        if (isOnline) {
          setServerStatus('online');
          console.log('Successfully connected to backend server');
        } else {
          setServerStatus('offline');
          setConnectionError('Cannot connect to the backend server. Please ensure the server is running at http://localhost:5000');
          console.error('Failed to connect to backend server');
        }
      } catch (error: any) {
        console.error('Error checking server connectivity:', error);
        setServerStatus('offline');
        
        // More specific error message
        let errorMessage = 'Error connecting to backend server.';
        if (error.code === 'ECONNABORTED') {
          errorMessage = 'Connection timeout. Backend server is not responding.';
        } else if (error.message && error.message.includes('Network Error')) {
          errorMessage = 'Network error. Backend server might not be running.';
        }
        
        setConnectionError(`${errorMessage} Check that backend is running at http://localhost:5000`);
      }
    }

    checkServerConnectivity();
    
    // Set up a periodic check every 10 seconds if offline
    const intervalId = setInterval(() => {
      if (serverStatus === 'offline') {
        checkServerConnectivity();
      }
    }, 10000);
    
    return () => clearInterval(intervalId);
  }, []);

  useEffect(() => {
    async function fetchAvailableDatabases() {
      if (serverStatus !== 'online') {
        return; // Don't attempt to fetch if server is offline
      }
      
      try {
        setIsLoading(true);
        const data = await rpcClient.getAvailableDatabases();
        // Convert string array to DatabaseType array with assertion
        const dbTypes = data.available_databases.map(db => db as DatabaseType);
        setAvailableDatabases(dbTypes);
        if (dbTypes.length > 0) {
          setActiveDatabase(dbTypes[0]);
        }
      } catch (error) {
        console.error('Error fetching available databases:', error);
        setConnectionError('Failed to fetch available databases. Is the backend server running?');
      } finally {
        setIsLoading(false);
      }
    }

    fetchAvailableDatabases();
  }, [serverStatus]);
  
  const handleSendMessage = async (messageText: string) => {
    if (!messageText.trim()) return;

    const userMessage: MessageType = {
      id: Date.now().toString(),
      content: messageText,
      sender: "user",
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      let response: MessageType;
      
      if (activeTab === 'rag') {
        // Use RAG query
        const data = await rpcClient.ragQuery(messageText, activeDatabase, false);
        
        if (data.success) {
          if (data.comparison_results) {
            // Handle comparison results
            const results = data.comparison_results;
            
            // Format database comparison results
            let dbComparison = "Database Comparison Results:\n";
            let fastestDb: string | null = null;
            let fastestTime = Infinity;
            
            // First pass to find the fastest database
            for (const db in results) {
              if (results[db].success && results[db].query_time < fastestTime) {
                fastestTime = results[db].query_time;
                fastestDb = db;
              }
            }
            
            // Second pass to format the results
            for (const db in results) {
              const time = results[db].query_time?.toFixed(4) || "N/A";
              const docsCount = results[db].success ? results[db].retrieved_docs?.length || 0 : 0;
              const status = results[db].success ? "✓" : "✗";
              const errorMessage = results[db].success ? "" : ` (Error: ${results[db].error || "Unknown error"})`;
              const isFastest = db === fastestDb ? " ⚡ FASTEST" : "";
              
              dbComparison += `\n${db.toUpperCase()} ${status}${isFastest} - Time: ${time}s, Docs: ${docsCount}${errorMessage}`;
            }
            
            // Add a summary of the fastest database
            let fastestDisplay = 'None';
            if (fastestDb) {
              fastestDisplay = `${fastestDb.toUpperCase()} (${results[fastestDb].query_time.toFixed(4)}s)`;
            }
            dbComparison += `\nFastest database: ${fastestDisplay}\n\n`;
            
            // Set the response content with comparison results
            response = {
              id: Date.now().toString(),
              content: `${dbComparison}RAG Response:\n${data.response}`,
              sender: "assistant",
              timestamp: new Date().toISOString(),
            };
          } else {
            // Standard RAG response without comparison
            response = {
              id: Date.now().toString(),
              content: data.response,
              sender: "assistant",
              timestamp: new Date().toISOString(),
            };
          }
        } else {
          response = {
            id: Date.now().toString(),
            content: `Error: ${data.error || "Unknown error occurred"}`,
            sender: "assistant",
            timestamp: new Date().toISOString(),
          };
        }
      } else {
        // Use regular chat
        const data = await rpcClient.chat(messageText);
        
        response = {
          id: Date.now().toString(),
          content: data.response,
          sender: "assistant",
          timestamp: new Date().toISOString(),
        };
      }

      setMessages((prev) => [...prev, response]);
    } catch (error) {
      console.error('Error sending message:', error);
      
      const errorResponse: MessageType = {
        id: Date.now().toString(),
        content: `Error: ${error instanceof Error ? error.message : "Unknown error occurred"}`,
        sender: "system",
        timestamp: new Date().toISOString(),
      };
      
      setMessages((prev) => [...prev, errorResponse]);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle document upload completion
  const handleUploadComplete = (response: UploadResponse) => {
    setUploadStatus(response);
    
    // Find fastest database
    const times = response.document.indexing_times;
    const availableDbs = Object.keys(times).filter(db => times[db as keyof typeof times] >= 0) as DatabaseType[];
    
    const fastest = Object.entries(times)
      .filter(([_, time]) => time >= 0)
      .reduce(
        (fastest, [db, time]) => time < fastest.time ? {db, time} : fastest,
        { db: 'none', time: Infinity }
      );
    
    // Update available databases based on upload response
    if (response.document.available_dbs) {
      const newAvailableDbs = Object.entries(response.document.available_dbs)
        .filter(([_, isAvailable]) => isAvailable)
        .map(([db]) => db as DatabaseType);
      
      setAvailableDatabases(newAvailableDbs);
    }
    
    // Generate indexing time message
    const indexingTimesMessage = availableDbs
      .map(db => `- ${db.toUpperCase()}: ${times[db].toFixed(4)}s`)
      .join('\n');
    
    setMessages(prev => [
      ...prev,
      {
        text: `Successfully uploaded document: ${response.document.filename}. 
        The document has been indexed in all available vector databases.
        
        Indexing times:
        
        ${indexingTimesMessage}
        
        Fastest database: ${fastest.db.toUpperCase()} (${fastest.time.toFixed(4)}s)
        
        You can now ask questions about this document using the RAG query interface.`,
        sender: 'bot'
      }
    ]);
  };

  // Handle RAG query submission for a single database
  const handleRagQuery = async (query: string, dbType: DatabaseType, compareAll: boolean = false) => {
    setIsQuerying(true);
    setCurrentQuery(query);
    
    // Add query to message history with appropriate text based on compareAll
    setMessages(prev => [
      ...prev,
      {
        text: compareAll 
          ? `Comparing all databases for query: ${query}` 
          : `Query using ${dbType.toUpperCase()}: ${query}`,
        sender: 'user'
      }
    ]);

    try {
      // Use the compare_all parameter in the API request
      const response = await rpcClient.ragQuery(query, dbType, compareAll);

      if (response.success) {
        if (compareAll && response.comparison_results) {
          // Handle comparison results
          const results = response.comparison_results;
          const bestDb = response.best_db;
          
          if (!results) {
            setMessages(prev => [
              ...prev,
              {
                text: `No results found in any database.`,
                sender: 'bot'
              }
            ]);
            return;
          }
          
          // Format performance comparison message
          let dbComparison = "Database Comparison Results:\n";
          
          // Track fastest DB for display
          let fastestDb: string | null = null;
          let fastestTime = Infinity;
          
          // First pass: Find the fastest database
          for (const db in results) {
            if (results[db].success && results[db].query_time < fastestTime) {
              fastestTime = results[db].query_time;
              fastestDb = db;
            }
          }
          
          // Second pass: Format the results with clear indication of fastest
          for (const db in results) {
            const time = results[db].query_time?.toFixed(4) || "N/A";
            const docsCount = results[db].success ? results[db].retrieved_docs?.length || 0 : 0;
            const status = results[db].success ? "✓" : "✗";
            const errorMessage = results[db].success ? "" : ` (Error: ${results[db].error || "Unknown error"})`;
            const isFastest = db === fastestDb ? " ⚡ FASTEST" : "";
            
            dbComparison += `\n${db.toUpperCase()} ${status}${isFastest} - Time: ${time}s, Docs: ${docsCount}${errorMessage}`;
          }
          
          // Add summary of fastest database
          let fastestDisplay = 'None';
          if (fastestDb) {
            fastestDisplay = `${fastestDb.toUpperCase()} (${results[fastestDb].query_time.toFixed(4)}s)`;
          }
          dbComparison += `\nFastest database: ${fastestDisplay}\n\n`;
          
          dbComparison += `RAG Response:\n${response.response}`;
          
          // Add comparison results to messages
          setMessages(prev => [
            ...prev,
            {
              text: dbComparison,
              sender: 'bot'
            }
          ]);
          
          // Update state with comparison result
          if (bestDb) {
            setComparisonResult({
              query,
              responses: results as unknown as Record<DatabaseType, RagResponse>,
              fastest: bestDb as DatabaseType
            });
          }
        } else {
          // Handle single database response (original behavior)
          setRagResponses(prev => ({
            ...prev,
            [dbType]: response
          }));
          
          // Add response to chat
          setMessages(prev => [
            ...prev,
            {
              text: `${dbType.toUpperCase()} (${response.query_time.toFixed(4)}s): ${response.response}`,
              sender: 'bot'
            }
          ]);
        }
      } else {
        setMessages(prev => [
          ...prev,
          {
            text: `Error querying ${compareAll ? 'databases' : dbType.toUpperCase()}: ${response.error || 'Unknown error'}`,
            sender: 'bot'
          }
        ]);
      }
    } catch (error) {
      console.error('RAG query error:', error);
      setMessages(prev => [
        ...prev,
        {
          text: `Error querying ${compareAll ? 'databases' : dbType.toUpperCase()}: Request failed`,
          sender: 'bot'
        }
      ]);
    } finally {
      setIsQuerying(false);
    }
  };

  // Add a server status indicator component
  const ServerStatusIndicator = () => (
    <div className={`server-status ${serverStatus === 'online' ? 'online' : 'offline'}`}>
      <span className="status-dot"></span>
      Server: {serverStatus === 'checking' ? 'Checking...' : serverStatus === 'online' ? 'Online' : 'Offline'}
    </div>
  );

  // Add error banner when there's a connection error
  const ConnectionErrorBanner = () => {
    if (!connectionError) return null;
    
    return (
      <div className="error-banner">
        <p>{connectionError}</p>
        <button onClick={() => window.location.reload()}>Retry</button>
      </div>
    );
  };

  return (
    <main className="flex min-h-screen flex-col p-8">
      <ServerStatusIndicator />
      <ConnectionErrorBanner />
      
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
                  <RagQueryForm
                    onQueryComplete={(response) => {
                      // This is now handled directly in handleRagQuery
                    }}
                    isQuerying={isQuerying}
                    setIsQuerying={setIsQuerying}
                    availableDatabases={availableDatabases}
                    onSubmitQuery={(query, dbType, doCompareAll) => handleRagQuery(query, dbType, doCompareAll)}
                  />
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
              setAvailableDatabases={setAvailableDatabases}
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
                  <div className="overflow-hidden bg-white rounded-md border border-gray-200">
                    {Object.entries(uploadStatus.document.indexing_times)
                      .filter(([_, time]) => time >= 0)
                      .sort(([_, timeA], [__, timeB]) => timeA - timeB)
                      .map(([db, time], index, arr) => (
                        <div 
                          key={db} 
                          className={`flex justify-between items-center px-3 py-2 ${
                            index < arr.length - 1 ? 'border-b border-gray-100' : ''
                          } ${index === 0 ? 'font-medium text-green-600' : ''}`}
                        >
                          <span className="capitalize">
                            {index === 0 && '🏆 '}
                            {db}
                          </span>
                          <span>{time.toFixed(4)}s</span>
                        </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
            
            {comparisonResult && (
              <div className="mt-6">
                <h3 className="font-medium text-gray-700 mb-2">Query Performance</h3>
                <div className="overflow-hidden bg-white rounded-md border border-gray-200">
                  {Object.entries(comparisonResult.responses)
                    .sort(([_, respA], [__, respB]) => respA.query_time - respB.query_time)
                    .map(([db, response], index) => (
                      <div 
                        key={db} 
                        className={`flex justify-between items-center px-3 py-2 ${
                          index < Object.keys(comparisonResult.responses).length - 1 ? 'border-b border-gray-100' : ''
                        } ${db === comparisonResult.fastest ? 'font-medium text-green-600' : ''}`}
                      >
                        <span className="capitalize">
                          {db === comparisonResult.fastest && '🏆 '}
                          {db}
                        </span>
                        <span>{response.query_time.toFixed(4)}s</span>
                      </div>
                  ))}
                </div>
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

      {/* Add some CSS for the new components */}
      <style jsx>{`
        .server-status {
          position: fixed;
          top: 10px;
          right: 10px;
          padding: 5px 10px;
          border-radius: 4px;
          font-size: 12px;
          background-color: #f3f4f6;
          display: flex;
          align-items: center;
          gap: 5px;
          z-index: 100;
        }
        
        .status-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          display: inline-block;
        }
        
        .online .status-dot {
          background-color: #10b981;
        }
        
        .offline .status-dot {
          background-color: #ef4444;
        }
        
        .error-banner {
          width: 100%;
          padding: 10px 15px;
          background-color: #fee2e2;
          color: #b91c1c;
          border-radius: 4px;
          margin-bottom: 20px;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        
        .error-banner button {
          background-color: #b91c1c;
          color: white;
          padding: 5px 10px;
          border-radius: 4px;
          font-size: 12px;
        }
      `}</style>
    </main>
  );
}