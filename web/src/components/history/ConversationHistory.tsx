"use client";

import { motion } from "framer-motion";
import { Search, Clock, MessageCircle, Star, Trash2, MoreHorizontal } from "lucide-react";
import { useState } from "react";
import { useConversationStore } from "@/stores/conversationStore";
import { useUIStore } from "@/stores/uiStore";
import { AnimalAvatar } from "@/components/animals/AnimalAvatar";
import type { Conversation } from "@/types";
import { formatDateTime } from "@/lib/utils";

export function ConversationHistory() {
  const { conversations, setActiveConversation, deleteConversation, toggleFavorite, renameConversation } = useConversationStore();
  const { searchQuery, setSearchQuery, setCurrentView } = useUIStore();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");

  const filteredConversations = searchQuery
    ? conversations.filter(
        (conv) =>
          conv.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
          conv.messages.some((m) =>
            m.content.toLowerCase().includes(searchQuery.toLowerCase())
          )
      )
    : conversations;

  const sortedConversations = [...filteredConversations].sort((a, b) => {
    // Favorites first
    if (a.isFavorite !== b.isFavorite) {
      return a.isFavorite ? -1 : 1;
    }
    // Then by updated time (newest first)
    return new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime();
  });

  const handleRename = (id: string, currentTitle: string) => {
    setEditingId(id);
    setEditTitle(currentTitle);
  };

  const handleSaveRename = (id: string) => {
    if (editTitle.trim()) {
      renameConversation(id, editTitle.trim());
    }
    setEditingId(null);
    setEditTitle("");
  };

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <div className="p-4 bg-white border-b border-gray-100">
        <h2 className="text-lg font-bold text-gray-800 mb-4">对话历史</h2>
        
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索对话..."
            className="w-full pl-10 pr-4 py-2 rounded-cartoon border border-gray-200 focus:border-cartoon-primary focus:outline-none focus:ring-2 focus:ring-cartoon-primary/20"
          />
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {sortedConversations.length === 0 ? (
          <div className="text-center py-12">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-100 flex items-center justify-center">
              <Clock className="w-8 h-8 text-gray-400" />
            </div>
            <p className="text-gray-500">暂无对话历史</p>
          </div>
        ) : (
          sortedConversations.map((conversation) => (
            <ConversationItem
              key={conversation.id}
              conversation={conversation}
              isEditing={editingId === conversation.id}
              editTitle={editTitle}
              onEditChange={setEditTitle}
              onSaveEdit={() => handleSaveRename(conversation.id)}
              onRename={() => handleRename(conversation.id, conversation.title)}
              onDelete={() => deleteConversation(conversation.id)}
              onToggleFavorite={() => toggleFavorite(conversation.id)}
              onClick={() => { setActiveConversation(conversation.id); setCurrentView("chat"); }}
            />
          ))
        )}
      </div>
    </div>
  );
}

interface ConversationItemProps {
  conversation: Conversation;
  isEditing: boolean;
  editTitle: string;
  onEditChange: (value: string) => void;
  onSaveEdit: () => void;
  onRename: () => void;
  onDelete: () => void;
  onToggleFavorite: () => void;
  onClick: () => void;
}

function ConversationItem({
  conversation,
  isEditing,
  editTitle,
  onEditChange,
  onSaveEdit,
  onRename,
  onDelete,
  onToggleFavorite,
  onClick,
}: ConversationItemProps) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-cartoon-lg p-4 shadow-sm hover:shadow-md transition-shadow cursor-pointer group"
      onClick={onClick}
    >
      {/* Header row */}
      <div className="flex items-start justify-between mb-2">
        {isEditing ? (
          <input
            type="text"
            value={editTitle}
            onChange={(e) => onEditChange(e.target.value)}
            onBlur={onSaveEdit}
            onKeyDown={(e) => e.key === "Enter" && onSaveEdit()}
            className="flex-1 px-2 py-1 text-sm border border-cartoon-primary rounded"
            autoFocus
            onClick={(e) => e.stopPropagation()}
          />
        ) : (
          <h3 className="font-semibold text-gray-800 line-clamp-1 flex-1">
            {conversation.title}
          </h3>
        )}
        
        {/* Actions */}
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onToggleFavorite();
            }}
            className="p-1 rounded hover:bg-gray-100"
          >
            <Star
              className={`w-4 h-4 ${
                conversation.isFavorite
                  ? "fill-yellow-400 text-yellow-400"
                  : "text-gray-400"
              }`}
            />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onRename();
            }}
            className="p-1 rounded hover:bg-gray-100"
          >
            <MoreHorizontal className="w-4 h-4 text-gray-400" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="p-1 rounded hover:bg-gray-100"
          >
            <Trash2 className="w-4 h-4 text-gray-400 hover:text-red-500" />
          </button>
        </div>
      </div>

      {/* Participants */}
      <div className="flex items-center gap-2 mb-2">
        <div className="flex -space-x-1">
          {conversation.participants.slice(0, 3).map((animal) => (
            <div key={animal.id} className="w-6 h-6 rounded-full ring-1 ring-white">
              <AnimalAvatar animal={animal} size="xs" />
            </div>
          ))}
        </div>
        <span className="text-xs text-gray-500">
          {conversation.participants.length} 个Agent
        </span>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between text-xs text-gray-400">
        <div className="flex items-center gap-1">
          <MessageCircle className="w-3 h-3" />
          <span>{conversation.messages.length} 条消息</span>
        </div>
        <span>{formatDateTime(conversation.updatedAt)}</span>
      </div>
    </motion.div>
  );
}
