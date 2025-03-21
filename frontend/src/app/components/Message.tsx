import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Message as MessageType } from '../types';

interface MessageProps {
  message: MessageType;
}

const Message: React.FC<MessageProps> = ({ message }) => {
  return (
    <div className={`message ${message.sender === 'user' ? 'flex justify-end' : 'flex justify-start'} mb-4`}>
      <div 
        className={`max-w-[70%] px-4 py-3 rounded-2xl ${
          message.sender === 'user' 
            ? 'bg-blue-600 text-white rounded-br-none' 
            : 'bg-gray-200 text-gray-800 rounded-bl-none'
        }`}
      >
        {message.sender === 'bot' ? (
          <div className="prose dark:prose-invert prose-sm">
            <ReactMarkdown>
              {message.text}
            </ReactMarkdown>
          </div>
        ) : (
          <p className="whitespace-pre-wrap break-words">{message.text}</p>
        )}
      </div>
    </div>
  );
};

export default Message;