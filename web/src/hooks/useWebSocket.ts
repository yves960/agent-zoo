"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { useConversationStore } from "@/stores/conversationStore";
import { useUIStore } from "@/stores/uiStore";
import type { WebSocketMessage, Message, AnimalType } from "@/types";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8001/api/ws";

interface UseWebSocketReturn {
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
  sendMessage: (content: string, animalIds: AnimalType[], threadId?: string) => void;
  connect: () => void;
  disconnect: () => void;
}

export function useWebSocket(): UseWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const shouldReconnectRef = useRef(true);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const addMessage = useConversationStore((state) => state.addMessage);
  const setTyping = useConversationStore((state) => state.setTyping);
  const conversations = useConversationStore((state) => state.conversations);
  const activeConversationId = useConversationStore((state) => state.activeConversationId);
  const addToast = useUIStore((state) => state.addToast);

  // Compute active conversation with stable reference
  const activeConversation = conversations.find((c) => c.id === activeConversationId);

  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false;
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
    setIsConnecting(false);
  }, []);

  const handleWebSocketMessage = useCallback((data: WebSocketMessage) => {
    if (!activeConversation) return;

    switch (data.type) {
      case "message":
        if (data.content && data.animal_id) {
          const message: Message = {
            id: Date.now().toString(),
            type: "message",
            content: data.content,
            sender: {
              id: data.animal_id,
              name: data.animal_id,
              isAnimal: true,
              animalId: data.animal_id as AnimalType,
            },
            timestamp: new Date(data.timestamp || Date.now()),
            threadId: data.thread_id || activeConversation.id,
            mentions: data.mentions as AnimalType[] || [],
          };
          addMessage(activeConversation.id, message);
        }
        break;

      case "typing":
        setTyping(activeConversation.id, true);
        setTimeout(() => setTyping(activeConversation.id, false), 3000);
        break;

      case "done":
        setTyping(activeConversation.id, false);
        break;

      case "error":
        addToast({
          type: "error",
          message: data.content || "发生错误",
        });
        break;

      case "system":
        console.log("System message:", data.content);
        break;
    }
  }, [activeConversation, addMessage, setTyping, addToast]);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    
    setIsConnecting(true);
    setError(null);

    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setIsConnecting(false);
        setError(null);
        
        // Send initial connection message
        ws.send(JSON.stringify({
          type: "connect",
          animal_id: "user",
        }));
      };

      ws.onmessage = (event) => {
        try {
          const data: WebSocketMessage = JSON.parse(event.data);
          handleWebSocketMessage(data);
        } catch (err) {
          console.error("Failed to parse WebSocket message:", err);
        }
      };

      ws.onerror = (err) => {
        console.error("WebSocket error:", err);
        setError("连接出错，正在重试...");
        setIsConnected(false);
      };

      ws.onclose = () => {
        setIsConnected(false);
        setIsConnecting(false);
        
        // Only attempt reconnection if not explicitly disconnected
        if (shouldReconnectRef.current && wsRef.current?.readyState !== WebSocket.OPEN) {
          reconnectTimeoutRef.current = setTimeout(() => {
            if (shouldReconnectRef.current && wsRef.current?.readyState !== WebSocket.OPEN) {
              connect();
            }
          }, 3000);
        }
      };
    } catch {
      setError("无法建立连接");
      setIsConnecting(false);
    }
  }, [handleWebSocketMessage]);

  const sendMessage = useCallback((content: string, animalIds: AnimalType[], threadId?: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      addToast({
        type: "error",
        message: "连接已断开，请刷新页面重试",
      });
      return;
    }

    const message: WebSocketMessage = {
      type: "message",
      content,
      animal_id: "user",
      thread_id: threadId,
      mentions: animalIds,
    };

    wsRef.current.send(JSON.stringify(message));
  }, [addToast]);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return {
    isConnected,
    isConnecting,
    error,
    sendMessage,
    connect,
    disconnect,
  };
}
