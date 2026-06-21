import { useState, useCallback } from 'react';

export function useAgentStream() {
  const [isRunning, setIsRunning] = useState(false);
  const [currentNode, setCurrentNode] = useState(null);
  const [payload, setPayload] = useState(null);
  const [error, setError] = useState(null);

  const processStream = async (response) => {
    if (!response.body) throw new Error("No response body");
    
    setIsRunning(true);
    setCurrentNode("Initializing...");
    setError(null);
    setPayload(null);

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        
        // SSE messages are separated by \n\n
        const messages = buffer.split('\n\n');
        buffer = messages.pop() || ""; // Keep the last incomplete message in the buffer

        for (const message of messages) {
          if (message.startsWith('data: ')) {
            const dataStr = message.replace('data: ', '').trim();
            if (!dataStr) continue;

            try {
              const data = JSON.parse(dataStr);
              
              if (data.type === 'node_update') {
                setCurrentNode(data.node);
              } else if (data.type === 'execution_complete') {
                setPayload(data.payload);
              } else if (data.type === 'error' || data.type === 'fatal_error') {
                setError(data.message);
              } else if (data.type === 'paused') {
                // Graph is waiting for user input
                setIsRunning(false);
              }
            } catch (err) {
              console.error("Failed to parse SSE JSON:", err, dataStr);
            }
          }
        }
      }
    } finally {
      setIsRunning(false);
      reader.releaseLock();
    }
  };

  const startSession = useCallback(async (token, threadId) => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/agent/start', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ 
          thread_id: threadId
        })
      });

      await processStream(response);
    } catch (err) {
      setError(err.message);
      setIsRunning(false);
    }
  }, []);

  const submitAnswer = useCallback(async (token, threadId, answerText) => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/agent/reply', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ 
          thread_id: threadId,
          answer: answerText
        })
      });

      await processStream(response);
    } catch (err) {
      setError(err.message);
      setIsRunning(false);
    }
  }, []);

  return { startSession, submitAnswer, isRunning, currentNode, payload, error };
}
