import { useState } from 'react';
import axios from 'axios';
import { UploadResponse, DatabaseType } from '../types';

interface DocumentUploadProps {
  onUploadComplete: (response: UploadResponse) => void;
  isUploading: boolean;
  setIsUploading: (isUploading: boolean) => void;
  setAvailableDatabases?: (databases: DatabaseType[]) => void; // New prop to update available DBs in parent
}

const DocumentUpload: React.FC<DocumentUploadProps> = ({ 
  onUploadComplete, 
  isUploading, 
  setIsUploading,
  setAvailableDatabases
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploadStatus, setUploadStatus] = useState<UploadResponse | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        setError('Please select a PDF file');
        setSelectedFile(null);
      } else {
        setSelectedFile(file);
        setError(null);
        // Reset upload status when a new file is selected
        setUploadStatus(null);
      }
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select a file first');
      return;
    }

    setIsUploading(true);
    setError(null);
    setUploadStatus(null);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await axios.post<UploadResponse>(
        'http://localhost:5001/api/upload',
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' }
        }
      );

      if (response.data.success) {
        setUploadStatus(response.data);
        onUploadComplete(response.data);
        
        // Update available databases in parent component if function provided
        if (setAvailableDatabases && response.data.document.available_dbs) {
          const availableDbs: DatabaseType[] = [];
          Object.entries(response.data.document.available_dbs).forEach(([db, isAvailable]) => {
            if (isAvailable) {
              availableDbs.push(db as DatabaseType);
            }
          });
          setAvailableDatabases(availableDbs);
        }
      } else {
        setError(response.data.message || 'Upload failed');
      }
    } catch (err: any) {
      console.error('Upload error:', err);
      setError(err.response?.data?.error || 'Error uploading document');
    } finally {
      setIsUploading(false);
    }
  };

  // Render database availability status
  const renderDatabaseStatus = () => {
    if (!uploadStatus) return null;
    
    const availableDbs = uploadStatus.document.available_dbs;
    if (!availableDbs) return null;
    
    const allDatabases: DatabaseType[] = ['faiss', 'chroma', 'weaviate', 'mongo', 'pgvector', 'milvus'];
    
    return (
      <div className="mt-4 text-sm">
        <h4 className="font-medium mb-2">Available Vector Databases:</h4>
        <div className="grid grid-cols-2 gap-2">
          {allDatabases.map(db => (
            <div 
              key={db}
              className={`px-3 py-2 rounded-md flex items-center ${
                availableDbs[db] 
                  ? 'bg-green-50 text-green-700 border border-green-200' 
                  : 'bg-gray-50 text-gray-400 border border-gray-200'
              }`}
            >
              <span className={`w-2 h-2 rounded-full mr-2 ${availableDbs[db] ? 'bg-green-500' : 'bg-gray-400'}`}></span>
              <span className="capitalize">{db}</span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  // Render indexing performance after upload
  const renderIndexingPerformance = () => {
    if (!uploadStatus) return null;
    
    const { indexing_times } = uploadStatus.document;
    
    // Only show databases that were successfully indexed
    const availableDatabases = Object.entries(indexing_times)
      .filter(([_, time]) => time >= 0)
      .sort(([_, timeA], [__, timeB]) => timeA - timeB);
    
    if (availableDatabases.length === 0) return null;
    
    return (
      <div className="mt-4">
        <h4 className="font-medium mb-2 text-sm">Indexing Performance:</h4>
        <div className="overflow-hidden bg-white rounded-md border border-gray-200">
          {availableDatabases.map(([db, time]) => (
            <div 
              key={db}
              className="flex justify-between px-3 py-2 border-b last:border-b-0 text-sm"
            >
              <span className="font-medium capitalize">{db}</span>
              <span className="text-gray-600">{time.toFixed(3)}s</span>
            </div>
          ))}
        </div>
        <div className="mt-2 text-xs text-gray-500">
          Fastest: {availableDatabases[0][0].toUpperCase()} ({availableDatabases[0][1].toFixed(3)}s)
        </div>
      </div>
    );
  };

  return (
    <div className="border rounded-lg p-4">
      <h3 className="text-lg font-semibold mb-3">Upload Document</h3>
      
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Select a PDF to process with vector databases:
        </label>
        <input
          type="file"
          accept=".pdf"
          onChange={handleFileChange}
          disabled={isUploading}
          className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
        />
        {selectedFile && (
          <p className="mt-2 text-sm text-gray-600">
            Selected: <span className="font-semibold">{selectedFile.name}</span> ({Math.round(selectedFile.size / 1024)} KB)
          </p>
        )}
      </div>
      
      {error && (
        <div className="mb-4 p-2 bg-red-50 border border-red-200 rounded text-red-600 text-sm">
          {error}
        </div>
      )}
      
      <button
        onClick={handleUpload}
        disabled={!selectedFile || isUploading}
        className={`w-full py-2 px-4 rounded-md text-white font-medium ${
          !selectedFile || isUploading
            ? 'bg-gray-400 cursor-not-allowed'
            : 'bg-blue-600 hover:bg-blue-700'
        }`}
      >
        {isUploading ? (
          <div className="flex items-center justify-center">
            <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Processing Document...
          </div>
        ) : (
          'Upload & Process'
        )}
      </button>
      
      {uploadStatus && uploadStatus.success && (
        <div className="mt-4 pt-4 border-t">
          <div className="text-green-600 font-medium mb-2">
            Document uploaded and processed successfully!
          </div>
          <div className="text-sm text-gray-700">
            <div>Filename: <span className="font-medium">{uploadStatus.document.filename}</span></div>
            <div>Chunks: <span className="font-medium">{uploadStatus.document.chunk_count}</span></div>
          </div>
          
          {/* Show database availability */}
          {renderDatabaseStatus()}
          
          {/* Show indexing performance */}
          {renderIndexingPerformance()}
        </div>
      )}
    </div>
  );
};

export default DocumentUpload;