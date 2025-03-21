import React, { useState, KeyboardEvent } from 'react';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  isLoading: boolean;
}

const ChatInput: React.FC<ChatInputProps> = ({ onSendMessage, isLoading }) => {
  const [input, setInput] = useState('');

  const handleSend = () => {
    if (input.trim() && !isLoading) {
      onSendMessage(input);
      setInput('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex items-center p-4 border-t border-gray-200 dark:border-gray-700">
      <textarea
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Type a message..."
        disabled={isLoading}
        className="flex-1 py-2 px-4 resize-none outline-none border border-gray-300 dark:border-gray-600 rounded-3xl focus:border-blue-500 dark:focus:border-blue-400 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 min-h-[50px] max-h-[150px]"
        rows={1}
      />
      <button
        onClick={handleSend}
        disabled={isLoading || !input.trim()}
        className="ml-3 px-5 py-2 bg-blue-600 text-white font-medium rounded-full disabled:bg-gray-400 disabled:cursor-not-allowed hover:bg-blue-700 transition-colors"
      >
        Send
      </button>
    </div>
  );
};

export default ChatInput;