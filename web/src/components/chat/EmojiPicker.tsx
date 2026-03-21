"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";

interface EmojiPickerProps {
  isOpen: boolean;
  onSelect: (emoji: string) => void;
  onClose: () => void;
}

type EmojiCategory = {
  id: string;
  name: string;
  emojis: string[];
};

const emojiCategories: EmojiCategory[] = [
  {
    id: "expressions",
    name: "表情",
    emojis: ["😀", "😊", "😂", "🥰", "😎", "🤔", "😴", "😇"],
  },
  {
    id: "animals",
    name: "Agent",
    emojis: ["🐶", "🐱", "🐼", "🦊", "🦁", "🐯", "🐨", "🐸"],
  },
  {
    id: "food",
    name: "食物",
    emojis: ["🍎", "🍕", "🍔", "🍦", "🍰", "☕", "🍵", "🍜"],
  },
  {
    id: "symbols",
    name: "符号",
    emojis: ["👍", "👎", "❤️", "⭐", "🔥", "✨", "💯", "🎉"],
  },
];

export function EmojiPicker({ isOpen, onSelect, onClose }: EmojiPickerProps) {
  const [activeCategory, setActiveCategory] = useState<string>("expressions");
  const pickerRef = useRef<HTMLDivElement>(null);

  // Handle click outside to close
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (pickerRef.current && !pickerRef.current.contains(event.target as Node)) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen, onClose]);

  // Handle escape key to close
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
    }

    return () => {
      document.removeEventListener("keydown", handleEscape);
    };
  }, [isOpen, onClose]);

  const handleEmojiClick = (emoji: string) => {
    onSelect(emoji);
  };

  const currentCategory = emojiCategories.find((cat) => cat.id === activeCategory);

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 bg-black/20 z-40"
            onClick={onClose}
          />

          {/* Picker */}
          <motion.div
            ref={pickerRef}
            initial={{ opacity: 0, scale: 0.9, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 10 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="fixed bottom-20 left-4 z-50 w-80 bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-cartoon-primary/10 to-cartoon-secondary/10 border-b border-gray-100">
              <h3 className="text-sm font-semibold text-gray-700">选择表情</h3>
              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                onClick={onClose}
                className="p-1 rounded-full hover:bg-gray-200 text-gray-500 transition-colors"
              >
                <X className="w-4 h-4" />
              </motion.button>
            </div>

            {/* Category Tabs */}
            <div className="flex border-b border-gray-100">
              {emojiCategories.map((category) => (
                <motion.button
                  key={category.id}
                  onClick={() => setActiveCategory(category.id)}
                  whileHover={{ backgroundColor: "rgba(0,0,0,0.02)" }}
                  whileTap={{ scale: 0.95 }}
                  className={`
                    flex-1 py-2 px-3 text-sm font-medium transition-colors relative
                    ${activeCategory === category.id ? "text-cartoon-primary" : "text-gray-500 hover:text-gray-700"}
                  `}
                >
                  {category.name}
                  {activeCategory === category.id && (
                    <motion.div
                      layoutId="activeTab"
                      className="absolute bottom-0 left-0 right-0 h-0.5 bg-cartoon-primary"
                      initial={false}
                      transition={{ type: "spring", stiffness: 500, damping: 30 }}
                    />
                  )}
                </motion.button>
              ))}
            </div>

            {/* Emoji Grid */}
            <div className="p-4 max-h-48 overflow-y-auto scrollbar-thin">
              <AnimatePresence mode="wait">
                <motion.div
                  key={activeCategory}
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -10 }}
                  transition={{ duration: 0.15 }}
                  className="grid grid-cols-8 gap-2"
                >
                  {currentCategory?.emojis.map((emoji, index) => (
                    <motion.button
                      key={emoji}
                      initial={{ opacity: 0, scale: 0 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: index * 0.03 }}
                      whileHover={{ scale: 1.2, backgroundColor: "rgba(255, 107, 157, 0.1)" }}
                      whileTap={{ scale: 0.9 }}
                      onClick={() => handleEmojiClick(emoji)}
                      className="w-8 h-8 flex items-center justify-center text-2xl rounded-lg hover:bg-cartoon-primary/10 transition-colors"
                    >
                      {emoji}
                    </motion.button>
                  ))}
                </motion.div>
              </AnimatePresence>
            </div>

            {/* Footer */}
            <div className="px-4 py-2 bg-gray-50 text-xs text-gray-400 text-center border-t border-gray-100">
              点击表情添加到消息
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
