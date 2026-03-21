/**
 * Core type definitions for the Animal Collaboration System
 */

// Animal types from backend
export type AnimalType = "xueqiu" | "liuliu" | "xiaohuang" | "meiqiu" | "openai";

export interface AnimalConfig {
  id: AnimalType;
  name: string;
  species: string;
  cli: string;
  color: string;
  personality: string;
  description: string;
  avatar: string;
  traits: string[];
  specialties: string[];
  greetings: string[];
  model?: string;
}

export type AnimalStatus = "available" | "busy" | "offline";

export type AgentSource = "local" | "h-agent" | "opencode-session" | "network";

export interface AnimalAgent {
  id: AnimalType;
  name: string;
  species: string;
  avatar: string;
  color: string;
  personality: string;
  status: AnimalStatus;
  isFavorite: boolean;
  description: string;
  traits: string[];
  specialties: string[];
  greetings: string[];
  cli?: string;
  model?: string;
  source: AgentSource;
  sourceUrl?: string;
  sessionId?: string;
  discoveredAt?: string;
}

// Message types
export type MessageRole = "user" | "assistant" | "system" | "tool";
export type MessageType = "message" | "typing" | "done" | "error" | "system";

export interface Message {
  id: string;
  type: MessageType;
  content: string;
  sender: {
    id: string;
    name: string;
    avatar?: string;
    isAnimal: boolean;
    animalId?: AnimalType;
  };
  timestamp: Date;
  threadId: string;
  mentions?: AnimalType[];
  metadata?: Record<string, unknown>;
}

// Conversation/Thread types
export type ConversationStatus = "active" | "paused" | "ended";

export interface Conversation {
  id: string;
  title: string;
  participants: AnimalAgent[];
  messages: Message[];
  status: ConversationStatus;
  createdAt: Date;
  updatedAt: Date;
  isFavorite: boolean;
  unreadCount: number;
}

// WebSocket types
export interface WebSocketMessage {
  type: MessageType;
  content?: string;
  animal_id?: string;
  thread_id?: string;
  timestamp?: string;
  mentions?: string[];
  metadata?: Record<string, unknown>;
}

// API types
export interface SendMessageRequest {
  content: string;
  animal_ids: AnimalType[];
  thread_id?: string;
}

export interface SendMessageResponse {
  success: boolean;
  message_id?: string;
  thread_id?: string;
  content?: string;
  error?: string;
}

export interface ThreadResponse {
  success: boolean;
  thread_id: string;
  title?: string;
  participant_animals?: AnimalType[];
  messages?: Message[];
  created_at?: string;
  error?: string;
}

export interface AnimalsResponse {
  animals: Record<string, {
    id: string;
    name: string;
    species: string;
    description: string;
    color: string;
    cli: string;
    model: string;
    enabled: boolean;
    mention_patterns?: string[];
  }>;
}

// UI types
export type ViewType = "chat" | "history" | "animals";

export interface Toast {
  id: string;
  type: "success" | "error" | "info" | "warning";
  message: string;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}
