import React from 'react';
import { IndexingTimes } from '../types';

interface QueryTimes {
  [key: string]: number;
}

interface DatabasePerformanceProps {
  indexingTimes: IndexingTimes;
  queryTimes: QueryTimes;
}

const DatabasePerformance: React.FC<DatabasePerformanceProps> = ({ 
  indexingTimes, 
  queryTimes 
}) => {
  const allDatabases = Object.keys(indexingTimes).filter(db => indexingTimes[db as keyof IndexingTimes] >= 0);
  
  const renderPerformanceData = () => {
    return (
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Database
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Indexing Time (s)
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Query Time (s)
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {allDatabases.map((db) => (
            <tr key={db}>
              <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                {db.toUpperCase()}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {indexingTimes[db as keyof IndexingTimes].toFixed(4)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {queryTimes[db] 
                  ? queryTimes[db].toFixed(4) 
                  : 'N/A'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  };

  return (
    <div className="overflow-hidden shadow-md border rounded-lg">
      <div className="px-4 py-5 sm:px-6 bg-gray-50">
        <h3 className="text-lg leading-6 font-medium text-gray-900">
          Database Performance Comparison
        </h3>
      </div>
      <div className="overflow-x-auto">
        {renderPerformanceData()}
      </div>
    </div>
  );
};

export default DatabasePerformance;