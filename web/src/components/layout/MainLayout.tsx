"use client";

import { motion } from "framer-motion";
import { Menu } from "lucide-react";
import { useEffect } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { ChatArea } from "@/components/chat/ChatArea";
import { ConversationHistory } from "@/components/history/ConversationHistory";
import { AnimalsView } from "@/components/animals/AnimalsView";
import { AnimalSelector } from "@/components/animals/AnimalSelector";
import { ToastContainer } from "@/components/ui/ToastContainer";
import { AppInit } from "@/components/AppInit";
import { WebSocketProvider } from "@/contexts/WebSocketContext";
import { useUIStore } from "@/stores/uiStore";
import { useState } from "react";
import { SettingsView } from "@/components/layout/SettingsView";

export default function MainLayout() {
  const { currentView, sidebarOpen, toggleSidebar, animalSelectorOpen, closeAnimalSelector } = useUIStore();
  const [isSelectorOpen, setIsSelectorOpen] = useState(false);

  // Combine local state and store state
  const selectorOpen = isSelectorOpen || animalSelectorOpen;
  const closeSelector = () => {
    setIsSelectorOpen(false);
    closeAnimalSelector();
  };

  // Reset selector modal when changing views
  useEffect(() => {
    if (isSelectorOpen) {
      setIsSelectorOpen(false);
    }
  }, [currentView, isSelectorOpen]);

  const renderContent = () => {
    switch (currentView) {
      case "chat":
        return <ChatArea />;
      case "history":
        return <ConversationHistory />;
      case "animals":
        return <AnimalsView onOpenSelector={() => setIsSelectorOpen(true)} />;
      case "settings":
        return <SettingsView />;
      default:
        return <ChatArea />;
    }
  };

  return (
    <WebSocketProvider>
      <AppInit />
      
      <div className="flex h-screen bg-gray-50 overflow-hidden">
        {/* Sidebar */}
        <Sidebar onNewChat={() => setIsSelectorOpen(true)} />

        {/* Main content */}
        <motion.main
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className={`
            flex-1 flex flex-col min-h-0 transition-all duration-300
            ${sidebarOpen ? "ml-64" : "ml-0"}
          `}
        >
          {/* Mobile menu button */}
          <button
            onClick={toggleSidebar}
            className="lg:hidden fixed top-4 left-4 z-50 p-2 bg-white rounded-cartoon shadow-md"
          >
            <Menu className="w-5 h-5" />
          </button>

          {/* Content */}
          {renderContent()}
        </motion.main>
      </div>

      {/* Animal Selector Modal - inside WebSocketProvider */}
      <AnimalSelector isOpen={selectorOpen} onClose={closeSelector} />

      {/* Toast notifications */}
      <ToastContainer />
    </WebSocketProvider>
  );
}
