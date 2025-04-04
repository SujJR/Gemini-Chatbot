"use client";

import { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Message as MessageType, UploadResponse, RagResponse, DatabaseType, ComparisonResult } from './types';
import Message from './components/Message';
import DocumentUpload from './components/DocumentUpload';
import ChatInput from './components/ChatInput';
import RagResults from './components/RagResults';
import RagQueryForm from './components/RagQueryForm';

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

  const fetchAvailableDatabases = async () => {
    try {
      const response = await axios.get('http://localhost:5000/api/available-dbs');
      if (response.data.success) {
        const availableDBs = response.data.available_databases;
        setAvailableDatabases(availableDBs);
        
        // Set active database to the first available one if current is not available
        if (availableDBs.length > 0 && !availableDBs.includes(activeDatabase)) {
          setActiveDatabase(availableDBs[0]);
        }
      }
    } catch (error) {
      console.error('Error fetching available databases:', error);
    }
  };

  useEffect(() => {
    fetchAvailableDatabases();
  }, []);
  
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
      const response = await axios.post<RagResponse>('http://localhost:5000/api/rag', {
        query,
        db_type: dbType,
        compare_all: compareAll
      });

      if (response.data.success) {
        if (compareAll && response.data.compare_all) {
          // Handle comparison results
          const results = response.data.results;
          const bestDb = response.data.best_db;
          
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
          Object.entries(results).forEach(([db, result]) => {
            if (result.query_time && result.retrieved_docs && result.retrieved_docs.length > 0) {
              if (result.query_time < fastestTime) {
                fastestTime = result.query_time;
                fastestDb = db;
              }
            }
          });
          
          // Second pass: Format the results with clear indication of fastest
          Object.entries(results).forEach(([db, result]) => {
            if (result.query_time) {
              const isFastest = db === fastestDb;
              dbComparison += `- ${db.toUpperCase()}: ${result.query_time.toFixed(4)}s (${result.retrieved_docs?.length || 0} results)${isFastest ? ' ⚡ FASTEST' : ''}\n`;
            } else if (result.error) {
              dbComparison += `- ${db.toUpperCase()}: Error: ${result.error}\n`;
            }
          });
          
          // Add summary of fastest database
          if (fastestDb) {
            const fastestResult = results[fastestDb];
            if (fastestResult && fastestResult.query_time) {
              const time = fastestResult.query_time.toFixed(4);
              dbComparison += `\nFastest database: ${String(fastestDb).toUpperCase()} (${time}s)\n\n`;
            }
          } else if (bestDb && typeof bestDb === 'string') {
            dbComparison += `\nBest database: ${bestDb.toUpperCase()}\n\n`; 
          } else {
            dbComparison += `\nNo database returned results fast enough\n\n`;
          }
          
          dbComparison += `RAG Response:\n${response.data.rag_response}`;
          
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
        }
      } else {
        setMessages(prev => [
          ...prev,
          {
            text: `Error querying ${compareAll ? 'databases' : dbType.toUpperCase()}: ${response.data.message || 'Unknown error'}`,
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
  );
}