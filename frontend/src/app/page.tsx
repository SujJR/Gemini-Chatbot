"use client";
import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Message as MessageType } from './types';
import Message from './components/Message';
import ChatInput from './components/ChatInput';

export default function Home() {
  const [messages, setMessages] = useState<MessageType[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

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
        setMessages(prev => [
          ...prev,
          { text: response.data.reply, sender: 'bot' }
        ]);
      } else {
        throw new Error(response.data.error || 'Failed to get response');
      }
    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [
        ...prev,
        {
          text: 'Sorry, I encountered an error. Please try again.',
          sender: 'bot'
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', backgroundColor: '#fff', color: '#000' }}>
      <header style={{ padding: '16px', borderBottom: '1px solid #ddd', textAlign: 'center' }}>
        <h1 style={{ margin: 0, fontSize: '20px', fontWeight: '600' }}>Chatbot</h1>
      </header>

      <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
          {messages.length === 0 ? (
            <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', color: '#555' }}>
              <p style={{ fontSize: '16px', marginBottom: '8px' }}>Welcome to the Gemini Chatbot!</p>
              <p style={{ fontSize: '14px' }}>Start a conversation by typing a message below.</p>
            </div>
          ) : (
            messages.map((message, index) => <Message key={index} message={message} />)
          )}

          {isLoading && (
            <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: '16px' }}>
              <div style={{ backgroundColor: '#f0f0f0', color: '#000', padding: '8px 12px', borderRadius: '8px', maxWidth: '70%' }}>
                <div style={{ display: 'flex', gap: '4px' }}>
                  <div style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#aaa', animation: 'bounce 1s infinite' }} />
                  <div style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#aaa', animation: 'bounce 1s infinite', animationDelay: '0.2s' }} />
                  <div style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#aaa', animation: 'bounce 1s infinite', animationDelay: '0.4s' }} />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />
      </div>
    </div>
  );
}