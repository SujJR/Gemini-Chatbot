import React, { useState, FormEvent, ChangeEvent } from 'react';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  isLoading: boolean;
  placeholder?: string;
  buttonText?: string;
}

const ChatInput: React.FC<ChatInputProps> = ({ 
  onSendMessage, 
  isLoading,
  placeholder = "Type your message...",
  buttonText = "Send"
}) => {
  const [message, setMessage] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (message.trim() && !isLoading) {
      onSendMessage(message);
      setMessage('');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="p-4 border-t border-gray-200">
      <div className="flex items-center">
        <input
          type="text"
          value={message}
          onChange={(e: ChangeEvent<HTMLInputElement>) => setMessage(e.target.value)}
          placeholder={placeholder}
          disabled={isLoading}
          className="flex-1 p-2 border border-gray-300 rounded-l-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          type="submit"
          disabled={isLoading || !message.trim()}
          className={`p-2 px-4 rounded-r-lg ${
            isLoading || !message.trim() ? 'bg-gray-300' : 'bg-blue-600 text-white'
          }`}
        >
          {isLoading ? 'Sending...' : buttonText}
        </button>
      </div>
    </form>
  );
};

export default ChatInput;