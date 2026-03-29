"use client";

import { motion } from "framer-motion";
import { AnimalAvatar } from "@/components/animals/AnimalAvatar";
import type { Message } from "@/types";
import { formatTime } from "@/lib/utils";

interface MessageBubbleProps {
  message: Message;
}

function highlightMentions(content: string): React.ReactNode {
  const mentionRegex = /(@\w+)/g;
  const parts = content.split(mentionRegex);
  
  return parts.map((part, index) => {
    if (part.match(mentionRegex)) {
      return <span key={index} className="mention">{part}</span>;
    }
    return part;
  });
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = !message.sender.isAnimal;
  const animal = message.sender.isAnimal ? {
    id: message.sender.animalId!,
    name: message.sender.name,
    species: "",
    cli: "",
    color: message.sender.animalId === "xueqiu" ? "#4A90E2" : message.sender.animalId === "liuliu" ? "#50C8E6" : "#7ED321",
    personality: "",
    avatar: "",
    status: "available" as const,
    isFavorite: false,
    traits: [],
    specialties: [],
    greetings: [],
    description: "",
    source: "local" as const,
  } : undefined;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: "spring", stiffness: 300, damping: 25 }}
      className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}
    >
      {/* Avatar */}
      <div className="flex-shrink-0">
        <AnimalAvatar animal={animal} size="md" fallback="user" />
      </div>

      {/* Message content */}
      <div className={`flex flex-col ${isUser ? "items-end" : "items-start"} max-w-[70%]`}>
        {/* Sender name */}
        <span className="text-xs text-gray-500 mb-1 px-2">
          {message.sender.name}
        </span>

        {/* Bubble */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          className={`
            relative px-4 py-3 rounded-cartoon-lg shadow-sm
            ${isUser 
              ? "bg-cartoon-primary text-white rounded-tr-none" 
              : "bg-white text-gray-800 rounded-tl-none border border-gray-100"
            }
          `}
          style={!isUser && animal ? { 
            borderLeftColor: animal.color,
            borderLeftWidth: "4px" 
          } : {}}
        >
          {/* Message text */}
          <p className="text-sm leading-relaxed whitespace-pre-wrap">
            {highlightMentions(message.content)}
          </p>

          {/* Timestamp */}
          <span className={`
            text-xs mt-1 block
            ${isUser ? "text-white/70" : "text-gray-400"}
          `}>
            {formatTime(message.timestamp)}
          </span>
        </motion.div>
      </div>
    </motion.div>
  );
}
