import { useState, useRef, useEffect, useCallback } from 'react';
import * as api from '../api/client';

export const useChat = () => {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [isHistoryLoading, setIsHistoryLoading] = useState(true);
  const abortControllerRef = useRef(null);

  const fetchHistory = useCallback(async (retryCount = 0) => {
    try {
      const data = await api.fetchHistory();
      setMessages(data);
      setIsHistoryLoading(false);
    } catch (e) {
      console.error("Failed to fetch history", e);
      if (retryCount < 10) {
        setTimeout(() => fetchHistory(retryCount + 1), 2000);
      } else {
        setIsHistoryLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const addMessage = (message) => {
    setMessages(prev => [...prev, message]);
  };

  const handleSend = async (questionText, questionDifficulty) => {
    if (!questionText.trim() || isLoading) return;

    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const userMessage = { sender: 'user', text: questionText, timestamp };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setLoadingMessage('AIが思考中...');
    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch(api.API_URLS.ask, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: questionText, difficulty: questionDifficulty }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let botMessageAdded = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; 

        for (const line of lines) {
          if (!line.trim()) continue;
          
          try {
            const data = JSON.parse(line);

            if (data.type === 'status') {
              setLoadingMessage(data.content);
            } else if (data.type === 'error') {
              setMessages(prev => [...prev, { sender: 'bot', text: `❌ ${data.content}`, timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }]);
              setIsLoading(false);
              return;
            } else if (data.type === 'answer' || data.type === 'sources') {
              if (!botMessageAdded) {
                setMessages(prev => [...prev, { 
                  sender: 'bot', 
                  text: data.type === 'answer' ? data.content : '', 
                  sources: data.type === 'sources' ? data.content : [], 
                  timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) 
                }]);
                botMessageAdded = true;
                setLoadingMessage('回答を生成中...');
              } else {
                setMessages(prev => {
                  const newMessages = [...prev];
                  const lastMsg = newMessages[newMessages.length - 1];
                  if (lastMsg && lastMsg.sender === 'bot') {
                    if (data.type === 'answer') lastMsg.text += data.content;
                    if (data.type === 'sources') lastMsg.sources = data.content;
                  }
                  return newMessages;
                });
              }
            } else if (data.type === 'done') {
              setIsLoading(false);
            }
          } catch (e) {
            console.error('Failed to parse stream data:', e, 'line:', line);
          }
        }
      }
    } catch (error) {
      if (error.name !== 'AbortError') {
        setMessages(prev => [...prev, { sender: 'bot', text: `エラーが発生しました: ${error.message}` }]);
      }
    } finally {
      setIsLoading(false);
      setLoadingMessage('');
      abortControllerRef.current = null;
    }
  };

  const handleStop = () => abortControllerRef.current?.abort();

  const clearMessages = () => setMessages([]);

  return {
    messages, setMessages, addMessage, clearMessages,
    isLoading, loadingMessage, isHistoryLoading,
    handleSend, handleStop, fetchHistory
  };
};
