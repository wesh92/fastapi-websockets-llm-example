import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent } from './ui/card';

const ChatComponent = () => {
    const [messages, setMessages] = useState([]);
    const [currentResponse, setCurrentResponse] = useState('');
    const [input, setInput] = useState('');
    const wsRef = useRef(null);
  
    useEffect(() => {
      // Create WebSocket connection
      wsRef.current = new WebSocket('ws://localhost:8000/websockets/chat/session123');
  
      wsRef.current.onmessage = (event) => {
        const response = JSON.parse(event.data);
        
        // Accumulate the streaming response
        setCurrentResponse(prev => prev + response.message);
      };
  
      return () => {
        if (wsRef.current) {
          wsRef.current.close();
        }
      };
    }, []);
  
    const sendMessage = (content) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        // Clear the previous response before sending new message
        setCurrentResponse('');
        
        wsRef.current.send(JSON.stringify({
          message: content
        }));
        
        // Add user message to chat
        setMessages(prev => [...prev, { role: 'user', content }]);
      }
    };
  
    const handleSubmit = (e) => {
        e.preventDefault();
        if (input.trim()) {
            sendMessage(input);
            setInput('');
        }
    };
  
    return (
      <Card className="w-full max-w-2xl mx-auto">
        <CardContent className="p-4">
          <div className="space-y-4">
            {messages.map((msg, i) => (
              <div key={i} className={`p-2 rounded ${
                msg.role === 'user' ? 'bg-blue-100 ml-8' : 'bg-gray-100 mr-8'
              }`}>
                {msg.content}
              </div>
            ))}
            {currentResponse && (
              <div className="p-2 rounded bg-gray-100 mr-8">
                {currentResponse}
              </div>
            )}
          </div>
          <form onSubmit={handleSubmit} className="mt-4">
            <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                className="w-full p-2 border rounded"
                placeholder="Type a message..."
            />
          </form>
        </CardContent>
      </Card>
    );
  };
  
  export default ChatComponent;