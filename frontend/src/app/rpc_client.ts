import axios from 'axios';

/**
 * Class for making JSON-RPC requests to the backend
 */
class RPCClient {
  private apiUrl: string;
  private axiosInstance;
  private id: number;
  private retryCount: number;
  private retryDelay: number;

  /**
   * Create a new RPC client
   * @param url RPC endpoint URL
   * @param retryCount Number of retries for failed requests
   * @param retryDelay Delay between retries in ms
   */
  constructor(
    url: string = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001/rpc',
    retryCount = 2,
    retryDelay = 1000
  ) {
    this.apiUrl = url;
    this.id = 1;
    this.retryCount = retryCount;
    this.retryDelay = retryDelay;
    
    console.log(`RPC Client initialized with URL: ${this.apiUrl}`);
    
    // Create an axios instance with custom settings
    this.axiosInstance = axios.create({
      timeout: 30000, // Increase timeout to 30 seconds
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  private async callRPC(method: string, params: any = {}): Promise<any> {
    try {
      // Construct the JSON-RPC request
      const payload = {
        jsonrpc: '2.0',
        method,
        params,
        id: Date.now(),
      };

      // Make the request
      const response = await this.axiosInstance.post(this.apiUrl, payload);
      
      // Check for errors in the response
      if (response.data.error) {
        throw new Error(response.data.error.message || 'RPC Error');
      }
      
      return response.data.result;
    } catch (error: any) {
      if (error.code === 'ECONNABORTED') {
        console.error('Connection timeout. The server might be down or unreachable.');
      } else if (error.response) {
        // The server responded with a non-2xx status code
        console.error('Server error:', error.response.status, error.response.data);
      } else if (error.request) {
        // The request was made but no response was received
        console.error('No response received from server. Check if server is running.');
      } else {
        // Other errors
        console.error('Error:', error.message);
      }
      throw error;
    }
  }

  /**
   * Make a JSON-RPC call
   * @param method The method name to call
   * @param params The parameters to pass to the method
   * @returns Promise with the result
   */
  async call<T>(method: string, params: any = {}): Promise<T> {
    let retries = 0;
    let lastError: any = null;

    while (retries <= this.retryCount) {
      try {
        console.log(`Making RPC call to ${this.apiUrl}: ${method}`, 
          retries > 0 ? `(retry ${retries}/${this.retryCount})` : '');
        
        const result = await this.callRPC(method, params);
        
        return result as T;
      } catch (error: any) {
        lastError = error;
        
        // Log the error with details to help debugging
        if (error.response) {
          // The request was made and the server responded with a status code outside of 2xx
          console.error('RPC server error:', {
            status: error.response.status,
            data: error.response.data,
            headers: error.response.headers
          });
        } else if (error.request) {
          // The request was made but no response was received
          console.error('RPC network error: No response received');
        } else {
          // Something happened in setting up the request
          console.error('RPC error:', error.message);
        }
        
        if (retries >= this.retryCount) {
          break;
        }
        
        // Wait before retry
        await new Promise(resolve => setTimeout(resolve, this.retryDelay));
        retries++;
      }
    }
    
    // If all retries failed, throw the last error
    console.error(`RPC call failed after ${retries} retries:`, lastError);
    throw lastError || new Error('RPC call failed with unknown error');
  }

  /**
   * Check if the server is reachable
   * @returns Promise resolving to true if server is reachable
   */
  async ping(): Promise<boolean> {
    try {
      // Try a direct GET request to the /api/test endpoint instead of RPC
      const serverUrl = this.apiUrl.replace('/rpc', '/api/test');
      await this.axiosInstance.get(serverUrl, { timeout: 3000 });
      return true;
    } catch (error) {
      console.error('Server ping failed:', error);
      return false;
    }
  }

  /**
   * Send a chat message
   * @param message The message to send
   * @returns Promise with the chat response
   */
  async chat(message: string): Promise<{ response: string }> {
    return this.call<{ response: string }>('chat', { message });
  }

  /**
   * Upload a document
   * @param file The file to upload
   * @returns Promise with the upload response
   */
  async uploadDocument(file: File): Promise<any> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      
      reader.onload = async (event) => {
        try {
          // Get base64 encoded content
          const base64Data = (event.target?.result as string).split(',')[1];
          
          // Call the RPC method
          const result = await this.call('upload_document', {
            file_data: base64Data,
            filename: file.name
          });
          
          resolve(result);
        } catch (error) {
          reject(error);
        }
      };
      
      reader.onerror = () => {
        reject(new Error('Error reading file'));
      };
      
      reader.readAsDataURL(file);
    });
  }

  /**
   * Make a RAG query
   * @param query The query text
   * @param dbType The database type to use
   * @param compareAll Whether to compare all databases
   * @returns Promise with the query response
   */
  async ragQuery(query: string, dbType: string, compareAll: boolean = false): Promise<any> {
    return this.call('rag_query', { 
      query, 
      db_type: dbType,
      compare_all: compareAll
    });
  }

  /**
   * Get available databases
   * @returns Promise with the list of available databases
   */
  async getAvailableDatabases(): Promise<{ available_databases: string[] }> {
    return this.call<{ available_databases: string[] }>('get_available_dbs');
  }
}

// Export a singleton instance
export const rpcClient = new RPCClient();
export default rpcClient; 