"use client";

import { useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MessageBubble } from "./MessageBubble";
import { TypingIndicator } from "./TypingIndicator";
import type { Message, AnimalAgent } from "@/types";

interface MessageListProps {
  messages: Message[];
  isTyping: boolean;
  typingAnimals?: AnimalAgent[];
}

export function MessageList({ messages, isTyping, typingAnimals }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isTyping]);

  return (
    <div
      ref={containerRef}
      className="flex-1 min-h-0 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-transparent"
    >
      <AnimatePresence mode="popLayout">
        {messages.map((message, index) => {
          if (message.private) {
            const isRecipient = message.sender.animalId ? message.mentions?.includes(message.sender.animalId) : false;
            const isSender = message.sender.id === "user";
            if (!isSender && !isRecipient) return null;
          }
          return (
            <motion.div
              key={message.id}
              layout
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9 }}
              transition={{ duration: 0.3, delay: index * 0.05 }}
              className="mb-4"
            >
              <MessageBubble message={message} />
            </motion.div>
          );
        })}
      </AnimatePresence>

      {/* Typing indicator */}
      {isTyping && typingAnimals && typingAnimals.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
        >
          <TypingIndicator animals={typingAnimals} />
        </motion.div>
      )}

      {/* Scroll anchor */}
      <div ref={bottomRef} />
    </div>
  );
}
