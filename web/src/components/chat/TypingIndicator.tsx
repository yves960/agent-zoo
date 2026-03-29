"use client";

import { motion } from "framer-motion";
import { AnimalAvatar } from "@/components/animals/AnimalAvatar";
import type { AnimalAgent } from "@/types";

interface TypingIndicatorProps {
  animals: AnimalAgent[];
}

export function TypingIndicator({ animals }: TypingIndicatorProps) {
  const animal = animals[0];

  // Don't render if no animals
  if (!animal) return null;

  return (
    <div className="flex items-center gap-3">
      {/* Avatar */}
      <div className="flex-shrink-0">
        <AnimalAvatar animal={animal} size="md" />
      </div>

      {/* Typing bubble */}
      <div className="flex flex-col">
        <span className="text-xs text-gray-500 mb-1 px-2">
          {animal.name} 正在输入...
        </span>
        
        <motion.div
          className="px-4 py-3 rounded-cartoon-lg bg-white border border-gray-100 rounded-tl-none shadow-sm"
          style={{ 
            borderLeftColor: animal.color,
            borderLeftWidth: "4px",
          }}
        >
          <div className="flex items-center gap-1">
            {[0, 1, 2].map((i) => (
              <motion.div
                key={i}
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: animal.color }}
                animate={{
                  y: [0, -6, 0],
                  opacity: [0.4, 1, 0.4],
                }}
                transition={{
                  duration: 0.6,
                  repeat: Infinity,
                  delay: i * 0.15,
                  ease: "easeInOut",
                }}
              />
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  );
}
