import React from 'react';
import { IndexingTimes } from '../types';

interface DatabasePerformanceProps {
  indexingTimes: IndexingTimes;
  queryTimes?: Record<string, number>;
}

const DatabasePerformance: React.FC<DatabasePerformanceProps> = ({ 
  indexingTimes, 
  queryTimes 
}) => {
  // Find fastest indexing database
  const indexingEntries = Object.entries(indexingTimes);
  const fastestIndexing = [...indexingEntries].sort((a, b) => a[1] - b[1])[0];
  
  // Find fastest query database (if available)
  let fastestQuery: [string, number] | null = null;
  if (queryTimes && Object.keys(queryTimes).length > 0) {
    const queryEntries = Object.entries(queryTimes);
    fastestQuery = [...queryEntries].sort((a, b) => a[1] - b[1])[0];
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="font-semibold mb-2">Indexing Performance</h3>
        <div className="space-y-2">
          {indexingEntries.map(([db, time]) => (
            <div 
              key={db}
              className={`flex items-center justify-between p-2 rounded-md ${
                db === fastestIndexing[0] ? 'bg-green-50 border-l-4 border-green-500' : 'bg-gray-50'
              }`}
            >
              <div className="flex items-center">
                {db === fastestIndexing[0] && <span className="text-green-500 mr-1">⚡</span>}
                <span className={`capitalize ${db === fastestIndexing[0] ? 'font-medium' : ''}`}>{db}</span>
              </div>
              <div className={db === fastestIndexing[0] ? 'font-semibold text-green-700' : ''}>
                {time.toFixed(4)}s
              </div>
            </div>
          ))}
        </div>
      </div>

      {fastestQuery && (
        <div>
          <h3 className="font-semibold mb-2">Query Performance</h3>
          <div className="space-y-2">
            {Object.entries(queryTimes || {}).map(([db, time]) => (
              <div 
                key={db}
                className={`flex items-center justify-between p-2 rounded-md ${
                  db === fastestQuery![0] ? 'bg-blue-50 border-l-4 border-blue-500' : 'bg-gray-50'
                }`}
              >
                <div className="flex items-center">
                  {db === fastestQuery![0] && <span className="text-blue-500 mr-1">⚡</span>}
                  <span className={`capitalize ${db === fastestQuery![0] ? 'font-medium' : ''}`}>{db}</span>
                </div>
                <div className={db === fastestQuery![0] ? 'font-semibold text-blue-700' : ''}>
                  {time.toFixed(4)}s
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default DatabasePerformance;