"use client";

import { motion } from "framer-motion";
import { MoreHorizontal, Video, X } from "lucide-react";
import { AnimalAvatar } from "@/components/animals/AnimalAvatar";
import type { AnimalAgent } from "@/types";
import { StatusIndicator } from "@/components/animals/StatusIndicator";
import { useUIStore } from "@/stores/uiStore";

interface ChatHeaderProps {
  title: string;
  participants: AnimalAgent[];
  onClose?: () => void;
  onVideoCall?: () => void;
  onMenuClick?: () => void;
}

export function ChatHeader({ title, participants, onClose, onVideoCall, onMenuClick }: ChatHeaderProps) {
  const activeParticipants = participants.filter(p => p.status === "available");
  const addToast = useUIStore((state) => state.addToast);

  return (
    <motion.div
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      className="flex items-center justify-between px-4 py-3 bg-white border-b border-gray-100 shadow-sm"
    >
      {/* Left: Participants */}
      <div className="flex items-center gap-3">
        {/* Participant avatars */}
        <div className="flex -space-x-2">
          {participants.slice(0, 3).map((animal, index) => (
            <motion.div
              key={animal.id}
              initial={{ scale: 0, x: -10 }}
              animate={{ scale: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              className="relative"
              style={{ zIndex: participants.length - index }}
            >
              <div className="ring-2 ring-white rounded-full">
                <AnimalAvatar animal={animal} size="sm" />
              </div>
            </motion.div>
          ))}
          {participants.length > 3 && (
            <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-xs text-gray-600 ring-2 ring-white">
              +{participants.length - 3}
            </div>
          )}
        </div>

        {/* Title and status */}
        <div>
          <h3 className="font-semibold text-gray-800 text-sm">{title}</h3>
          <div className="flex items-center gap-1 text-xs text-gray-500">
            <StatusIndicator status="available" size="sm" />
            <span>{activeParticipants.length} 个Agent在线</span>
          </div>
        </div>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-1">
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={() => {
            if (onVideoCall) {
              onVideoCall();
            } else {
              addToast({ type: "info", message: "即将推出" });
            }
          }}
          className="p-2 rounded-full hover:bg-gray-100 text-gray-500 transition-colors"
        >
          <Video className="w-5 h-5" />
        </motion.button>
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={() => {
            if (onMenuClick) {
              onMenuClick();
            } else {
              addToast({ type: "info", message: "即将推出" });
            }
          }}
          className="p-2 rounded-full hover:bg-gray-100 text-gray-500 transition-colors"
        >
          <MoreHorizontal className="w-5 h-5" />
        </motion.button>
        {onClose && (
          <motion.button
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            onClick={onClose}
            className="p-2 rounded-full hover:bg-gray-100 text-gray-500 transition-colors"
          >
            <X className="w-5 h-5" />
          </motion.button>
        )}
      </div>
    </motion.div>
  );
}
