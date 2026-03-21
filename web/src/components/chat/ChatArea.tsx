"use client";

import { useState, useCallback } from "react";
import { motion } from "framer-motion";
import { MessageSquare, Sparkles, Lock, Unlock, ChevronDown } from "lucide-react";
import { ChatHeader } from "@/components/chat/ChatHeader";
import { MessageList } from "@/components/chat/MessageList";
import { ChatInput } from "@/components/chat/ChatInput";
import { AnimalSelector } from "@/components/animals/AnimalSelector";
import { Button } from "@/components/ui/Button";
import { useConversationStore } from "@/stores/conversationStore";
import { useWebSocket } from "@/hooks/useWebSocket";
import type { Message, AnimalType } from "@/types";

export function ChatArea() {
  const [isSelectorOpen, setIsSelectorOpen] = useState(false);
  const [isPrivate, setIsPrivate] = useState(false);
  const [privateTarget, setPrivateTarget] = useState<string | null>(null);
  const { getActiveConversation, addMessage, isTyping } = useConversationStore();
  const { sendMessage, isConnected } = useWebSocket();

  const conversation = getActiveConversation();

  const handleSendMessage = useCallback(
    (content: string) => {
      if (!conversation) return;

      const userMessage: Message = {
        id: Date.now().toString(),
        type: "message",
        content,
        sender: {
          id: "user",
          name: "我",
          isAnimal: false,
        },
        timestamp: new Date(),
        threadId: conversation.id,
        private: isPrivate,
      };

      addMessage(conversation.id, userMessage);

      let animalIds: string[];
      if (isPrivate && privateTarget) {
        animalIds = [privateTarget];
      } else {
        animalIds = conversation.participants.map((p) => p.id);
      }
      sendMessage(content, animalIds as AnimalType[], conversation.id, isPrivate);
    },
    [conversation, addMessage, sendMessage, isPrivate, privateTarget]
  );

  const togglePrivate = () => {
    if (isPrivate) {
      setIsPrivate(false);
      setPrivateTarget(null);
    } else {
      setIsPrivate(true);
      if (conversation && conversation.participants.length > 0) {
        setPrivateTarget(conversation.participants[0].id);
      }
    }
  };

  // Empty state
  if (!conversation) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-gradient-to-br from-cartoon-bgLight to-white p-8">
        <motion.div
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: "spring", stiffness: 200, damping: 20 }}
          className="text-center"
        >
          <div className="w-24 h-24 mx-auto mb-6 rounded-cartoon-xl bg-gradient-to-br from-cartoon-xueqiu via-cartoon-liuliu to-cartoon-xiaohuang flex items-center justify-center shadow-cartoon-lg">
            <Sparkles className="w-12 h-12 text-white" />
          </div>
          <h2 className="text-2xl font-bold text-gray-800 mb-2">
            欢迎来到Agent动物园
          </h2>
          <p className="text-gray-500 mb-6 max-w-md">
            与可爱的动物伙伴们一起聊天、协作，让工作变得更有趣！
          </p>
          <Button
            variant="primary"
            size="lg"
            onClick={() => setIsSelectorOpen(true)}
            className="shadow-cartoon-lg"
          >
            <MessageSquare className="w-5 h-5 mr-2" />
            开始新对话
          </Button>
        </motion.div>

        <AnimalSelector isOpen={isSelectorOpen} onClose={() => setIsSelectorOpen(false)} />
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-h-0 bg-white">
      {/* Header */}
      <ChatHeader
        title={conversation.title}
        participants={conversation.participants}
      />

      {/* Messages */}
      <MessageList
        messages={conversation.messages}
        isTyping={isTyping[conversation.id] || false}
        typingAnimals={conversation.participants.filter((p) => p.status === "available")}
      />

      <div className="border-t border-gray-100 p-3">
        {isPrivate && conversation && (
          <div className="flex items-center gap-2 mb-2">
            <Lock className="w-4 h-4 text-cartoon-meiqiu" />
            <span className="text-sm text-gray-500">私聊发送给:</span>
            <div className="relative">
              <select
                value={privateTarget || ""}
                onChange={(e) => setPrivateTarget(e.target.value)}
                className="appearance-none bg-cartoon-meiqiu/10 text-cartoon-meiqiu font-medium px-3 py-1 pr-7 rounded-full text-sm cursor-pointer border border-cartoon-meiqiu/20 focus:outline-none"
              >
                {conversation.participants.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
              <ChevronDown className="w-3 h-3 text-cartoon-meiqiu absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>
          </div>
        )}
        <div className="flex items-center gap-2">
          <button
            onClick={togglePrivate}
            title={isPrivate ? "关闭私聊" : "私聊模式"}
            className={`p-2 rounded-full transition-colors ${
              isPrivate
                ? "bg-cartoon-meiqiu/10 text-cartoon-meiqiu"
                : "text-gray-400 hover:text-gray-600 hover:bg-gray-100"
            }`}
          >
            {isPrivate ? <Lock className="w-5 h-5" /> : <Unlock className="w-5 h-5" />}
          </button>
          <div className="flex-1">
            <ChatInput
              onSend={handleSendMessage}
              disabled={!isConnected}
              placeholder={
                isPrivate
                  ? `私聊发送给 ${privateTarget ? conversation?.participants.find(p => p.id === privateTarget)?.name : "请选择"}...`
                  : isConnected
                  ? "输入消息..."
                  : "连接中..."
              }
            />
          </div>
        </div>
      </div>

      <AnimalSelector isOpen={isSelectorOpen} onClose={() => setIsSelectorOpen(false)} />
    </div>
  );
}
