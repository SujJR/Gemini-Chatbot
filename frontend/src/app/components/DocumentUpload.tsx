import { useState } from 'react';
import axios from 'axios';
import { UploadResponse } from '../types';

interface DocumentUploadProps {
  onUploadComplete: (response: UploadResponse) => void;
  isUploading: boolean;
  setIsUploading: (isUploading: boolean) => void;
}

const DocumentUpload: React.FC<DocumentUploadProps> = ({ 
  onUploadComplete, 
  isUploading, 
  setIsUploading 
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        setError('Please select a PDF file');
        setSelectedFile(null);
      } else {
        setSelectedFile(file);
        setError(null);
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

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await axios.post<UploadResponse>(
        'http://localhost:5000/api/upload',
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' }
        }
      );

      if (response.data.success) {
        onUploadComplete(response.data);
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
    </div>
  );
};

export default DocumentUpload;