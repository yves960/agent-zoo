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
  sendMessage: (content: string, animalIds: AnimalType[], threadId?: string, privateMessage?: boolean) => void;
  connect: () => void;
  disconnect: () => void;
}

export function useWebSocket(): UseWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const shouldReconnectRef = useRef(true);
  const isManualDisconnectRef = useRef(false);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Select store state individually to minimize re-renders
  const addMessage = useConversationStore((state) => state.addMessage);
  const setTyping = useConversationStore((state) => state.setTyping);
  const activeConversationId = useConversationStore((state) => state.activeConversationId);
  const getConversationById = useConversationStore((state) => state.getConversationById);
  const addToast = useUIStore((state) => state.addToast);

  const activeConversationIdRef = useRef(activeConversationId);
  activeConversationIdRef.current = activeConversationId;

  const disconnect = useCallback(() => {
    isManualDisconnectRef.current = true;
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
    const currentConversationId = activeConversationIdRef.current;
    if (!currentConversationId) return;

    // Always get the conversation fresh from the store to avoid stale closures
    const currentConversation = getConversationById(currentConversationId);
    if (!currentConversation) return;

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
            threadId: data.thread_id || currentConversation.id,
            mentions: (data.mentions as AnimalType[]) || [],
            private: data.private || false,
          };
          addMessage(currentConversation.id, message);
        }
        break;

      case "typing":
        setTyping(currentConversation.id, true);
        setTimeout(() => setTyping(currentConversation.id, false), 3000);
        break;

      case "done":
        setTyping(currentConversation.id, false);
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
  }, [addMessage, setTyping, addToast, getConversationById]);

  const handleWebSocketMessageRef = useRef(handleWebSocketMessage);
  handleWebSocketMessageRef.current = handleWebSocketMessage;

  const handleMessage = useCallback((data: WebSocketMessage) => {
    handleWebSocketMessageRef.current(data);
  }, []);

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
      };

      ws.onmessage = (event) => {
        try {
          const data: WebSocketMessage = JSON.parse(event.data);
          handleMessage(data);
        } catch (err) {
          console.error("Failed to parse WebSocket message:", err);
        }
      };

      ws.onerror = () => {
        console.error("WebSocket error");
        setError("连接出错，正在重试...");
        setIsConnected(false);
      };

      ws.onclose = () => {
        setIsConnected(false);
        setIsConnecting(false);

        // Only attempt reconnection if not explicitly disconnected
        if (shouldReconnectRef.current && !isManualDisconnectRef.current) {
          reconnectTimeoutRef.current = setTimeout(() => {
            if (shouldReconnectRef.current && !isManualDisconnectRef.current) {
              connect();
            }
          }, 3000);
        }
      };
    } catch {
      setError("无法建立连接");
      setIsConnecting(false);
    }
  }, [handleMessage]);

  const sendMessage = useCallback((content: string, animalIds: AnimalType[], threadId?: string, privateMessage?: boolean) => {
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
      ...(privateMessage && { private: true }),
    };

    wsRef.current.send(JSON.stringify(message));
  }, [addToast]);

  // Initial connection
  useEffect(() => {
    connect();
    return () => {
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
    };
  }, [connect]);

  // Notify server of active conversation changes
  useEffect(() => {
    if (!activeConversationId) return;

    const sendConnect = () => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: "connect",
          animal_id: "user",
          thread_id: activeConversationId,
        }));
      }
    };

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      sendConnect();
    }

    const ws = wsRef.current;
    if (ws) {
      ws.addEventListener("open", sendConnect);
      return () => ws.removeEventListener("open", sendConnect);
    }
  }, [activeConversationId]);

  return {
    isConnected,
    isConnecting,
    error,
    sendMessage,
    connect,
    disconnect,
  };
}
