"use client";

import { useEffect } from "react";
import { useConversationStore } from "@/stores/conversationStore";
import { useUIStore } from "@/stores/uiStore";

export function AppInit() {
  const { initializeStore, activeConversationId, conversations, hydrated, setActiveConversation } = useConversationStore();
  const { currentView } = useUIStore();

  useEffect(() => {
    // Initialize store on mount
    initializeStore().catch((err) => {
      console.error("Failed to initialize conversation store:", err);
    });
  }, [initializeStore]);

  useEffect(() => {
    // After hydration, ensure the active conversation is valid
    if (hydrated && activeConversationId) {
      const activeConversation = conversations.find((c) => c.id === activeConversationId);
      
      // If the active conversation doesn't exist, reset it
      // but DON'T change the view - let the user stay in whatever view they're in
      if (!activeConversation) {
        console.warn("Active conversation not found, resetting:", activeConversationId);
        setActiveConversation(null);
      }
    }
  }, [hydrated, activeConversationId, conversations, setActiveConversation]);

  // Debug: log view changes
  useEffect(() => {
    console.log("Current view:", currentView, "Active conversation:", activeConversationId);
  }, [currentView, activeConversationId]);

  return null;
}
