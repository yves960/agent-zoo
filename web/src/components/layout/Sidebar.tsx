"use client";

import { motion } from "framer-motion";
import { MessageSquare, History, Users, Settings, Plus } from "lucide-react";
import { useUIStore } from "@/stores/uiStore";
import { Button } from "@/components/ui/Button";
import type { ViewType } from "@/types";

interface NavItem {
  id: ViewType;
  label: string;
  icon: React.ElementType;
}

const navItems: NavItem[] = [
  { id: "chat", label: "对话", icon: MessageSquare },
  { id: "history", label: "历史", icon: History },
  { id: "animals", label: "Agent", icon: Users },
];

interface SidebarProps {
  onNewChat: () => void;
}

export function Sidebar({ onNewChat }: SidebarProps) {
  const { currentView, setCurrentView, sidebarOpen } = useUIStore();

  return (
    <motion.aside
      initial={false}
      animate={{ x: 0, opacity: 1 }}
      className={`
        fixed left-0 top-0 h-full bg-white border-r border-gray-100 z-40
        flex flex-col transition-all duration-300
        ${sidebarOpen ? "w-64" : "w-0 overflow-hidden"}
      `}
    >
      {/* Header */}
      <div className="p-4 border-b border-gray-100">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-10 h-10 rounded-cartoon bg-gradient-to-br from-cartoon-xueqiu via-cartoon-liuliu to-cartoon-xiaohuang flex items-center justify-center">
            <span className="text-2xl">🐾</span>
          </div>
          <div>
            <h1 className="font-bold text-gray-800">Agent动物园</h1>
            <p className="text-xs text-gray-500">Zoo Multi-Agent</p>
          </div>
        </div>
        
        <Button
          variant="primary"
          size="md"
          onClick={onNewChat}
          className="w-full"
        >
          <Plus className="w-4 h-4 mr-2" />
          新对话
        </Button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentView === item.id;
          
          return (
            <motion.button
              key={item.id}
              whileHover={{ x: 4 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setCurrentView(item.id)}
              className={`
                w-full flex items-center gap-3 px-4 py-3 rounded-cartoon
                transition-all duration-200
                ${isActive 
                  ? "bg-cartoon-primary/10 text-cartoon-primary font-medium" 
                  : "text-gray-600 hover:bg-gray-50"
                }
              `}
            >
              <Icon className="w-5 h-5" />
              <span>{item.label}</span>
            </motion.button>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-gray-100">
        <button className="w-full flex items-center gap-3 px-4 py-3 rounded-cartoon text-gray-600 hover:bg-gray-50 transition-colors">
          <Settings className="w-5 h-5" />
          <span>设置</span>
        </button>
      </div>
    </motion.aside>
  );
}
