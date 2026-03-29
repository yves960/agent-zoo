import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Message, Conversation, AnimalAgent, AnimalType } from "@/types";

const API_BASE_URL = "http://localhost:8001";

interface ConversationState {
  conversations: Conversation[];
  activeConversationId: string | null;
  isTyping: Record<string, boolean>;
  hydrated: boolean;
  loading: boolean;
  error: string | null;
}

interface ConversationActions {
  createConversation: (title: string, participants: AnimalAgent[]) => Conversation;
  updateConversation: (id: string, updates: Partial<Conversation>) => void;
  deleteConversation: (id: string) => void;
  renameConversation: (id: string, newTitle: string) => void;
  toggleFavorite: (id: string) => void;
  
  addMessage: (conversationId: string, message: Message) => void;
  setTyping: (conversationId: string, isTyping: boolean) => void;
  
  setActiveConversation: (id: string | null) => void;
  endConversation: (id: string, saveToHistory?: boolean) => void;
  getConversationById: (id: string) => Conversation | undefined;
  getActiveConversation: () => Conversation | undefined;
  
  getConversationsByAnimal: (animalId: AnimalType) => Conversation[];
  getFavoriteConversations: () => Conversation[];
  searchConversations: (query: string) => Conversation[];
  getSortedConversations: () => Conversation[];

  initializeStore: () => Promise<void>;
  clearError: () => void;
}

const generateId = () => Math.random().toString(36).substring(2, 15);

async function fetchConversationsFromBackend(): Promise<Conversation[]> {
  const response = await fetch(`${API_BASE_URL}/api/conversations`);
  if (!response.ok) {
    throw new Error(`Failed to fetch conversations: ${response.status}`);
  }
  const data = await response.json();
  return data.conversations || [];
}

async function createConversationOnBackend(conversation: Conversation): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/conversations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(conversation),
  });
  if (!response.ok) {
    throw new Error(`Failed to create conversation: ${response.status}`);
  }
}

async function updateConversationOnBackend(id: string, updates: Partial<Conversation>): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/conversations/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!response.ok) {
    throw new Error(`Failed to update conversation: ${response.status}`);
  }
}

async function deleteConversationOnBackend(id: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/conversations/${id}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(`Failed to delete conversation: ${response.status}`);
  }
}

export const useConversationStore = create<ConversationState & ConversationActions>()(
  persist(
    (set, get) => ({
      conversations: [],
      activeConversationId: null,
      isTyping: {},
      hydrated: false,
      loading: false,
      error: null,

      initializeStore: async () => {
        set({ loading: true, error: null });
        try {
          const backendConversations = await fetchConversationsFromBackend();
          set({
            conversations: backendConversations,
            hydrated: true,
            loading: false,
          });
        } catch (err) {
          console.error("Failed to fetch conversations from backend:", err);
          set({
            error: err instanceof Error ? err.message : "Failed to load conversations",
            loading: false,
            hydrated: true,
          });
        }
      },

      clearError: () => set({ error: null }),

      createConversation: (title, participants) => {
        const newConversation: Conversation = {
          id: generateId(),
          title,
          participants,
          messages: [],
          status: "active",
          createdAt: new Date(),
          updatedAt: new Date(),
          isFavorite: false,
          unreadCount: 0,
        };
        
        set((state) => ({
          conversations: [newConversation, ...state.conversations],
          activeConversationId: newConversation.id,
        }));

        createConversationOnBackend(newConversation).catch((err) => {
          console.error("Failed to sync createConversation to backend:", err);
        });
        
        return newConversation;
      },

      updateConversation: (id, updates) => {
        set((state) => ({
          conversations: state.conversations.map((conv) =>
            conv.id === id ? { ...conv, ...updates, updatedAt: new Date() } : conv
          ),
        }));

        updateConversationOnBackend(id, updates).catch((err) => {
          console.error("Failed to sync updateConversation to backend:", err);
        });
      },

      deleteConversation: (id) => {
        set((state) => ({
          conversations: state.conversations.filter((conv) => conv.id !== id),
          activeConversationId: state.activeConversationId === id ? null : state.activeConversationId,
        }));

        deleteConversationOnBackend(id).catch((err) => {
          console.error("Failed to sync deleteConversation to backend:", err);
        });
      },

      renameConversation: (id, newTitle) => {
        get().updateConversation(id, { title: newTitle });
      },

      toggleFavorite: (id) => {
        const conv = get().getConversationById(id);
        if (conv) {
          get().updateConversation(id, { isFavorite: !conv.isFavorite });
        }
      },

      addMessage: (conversationId, message) => {
        set((state) => ({
          conversations: state.conversations.map((conv) =>
            conv.id === conversationId
              ? {
                  ...conv,
                  messages: [...conv.messages, message],
                  updatedAt: new Date(),
                }
              : conv
          ),
        }));
      },

      setTyping: (conversationId, isTyping) => {
        set((state) => ({
          isTyping: { ...state.isTyping, [conversationId]: isTyping },
        }));
      },

      setActiveConversation: (id) => {
        set({ activeConversationId: id });
        if (id) {
          set((state) => ({
            conversations: state.conversations.map((conv) =>
              conv.id === id ? { ...conv, unreadCount: 0 } : conv
            ),
          }));
        }
      },

      endConversation: (id, saveToHistory = true) => {
        if (saveToHistory) {
          get().updateConversation(id, { status: "ended" });
        } else {
          get().deleteConversation(id);
        }
        if (get().activeConversationId === id) {
          set({ activeConversationId: null });
        }
      },

      getConversationById: (id) => {
        return get().conversations.find((conv) => conv.id === id);
      },

      getActiveConversation: () => {
        const id = get().activeConversationId;
        return id ? get().getConversationById(id) : undefined;
      },

      getConversationsByAnimal: (animalId) => {
        return get().conversations.filter((conv) =>
          conv.participants.some((p) => p.id === animalId)
        );
      },

      getFavoriteConversations: () => {
        return get().conversations.filter((conv) => conv.isFavorite);
      },

      searchConversations: (query) => {
        const lowerQuery = query.toLowerCase();
        return get().conversations.filter(
          (conv) =>
            conv.title.toLowerCase().includes(lowerQuery) ||
            conv.messages.some((m) =>
              m.content.toLowerCase().includes(lowerQuery)
            )
        );
      },

      getSortedConversations: () => {
        return [...get().conversations].sort((a, b) => {
          if (a.isFavorite !== b.isFavorite) {
            return a.isFavorite ? -1 : 1;
          }
          return new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime();
        });
      },
    }),
    {
      name: "conversation-store",
    }
  )
);
