import React from 'react';
import { DocumentResult } from '../types';

interface RagResultsProps {
  results: DocumentResult[];
  queryTime: number;
}

const RagResults: React.FC<RagResultsProps> = ({ results, queryTime }) => {
  if (!results || results.length === 0) {
    return (
      <div className="p-4 border rounded-lg bg-gray-50 text-center text-gray-500">
        No results found
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="text-sm text-gray-500">
        Retrieved {results.length} result(s) in {queryTime.toFixed(4)} seconds
      </div>

      <div className="space-y-3 max-h-[400px] overflow-y-auto">
        {results.map((doc, index) => (
          <div key={index} className="p-3 border rounded-lg bg-gray-50">
            <div className="mb-1 flex justify-between items-start">
              <span className="font-medium text-sm">Document {index + 1}</span>
              {doc.metadata && (
                <span className="text-xs text-gray-500">
                  {doc.metadata.source && `Source: ${doc.metadata.source}`}
                  {doc.metadata.page !== undefined && ` (Page ${doc.metadata.page})`}
                </span>
              )}
            </div>
            <p className="text-sm whitespace-pre-wrap border-t pt-2 mt-1">
              {doc.content}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default RagResults;