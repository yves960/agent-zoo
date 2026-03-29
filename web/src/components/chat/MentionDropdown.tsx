"use client";

import { useEffect, useRef, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { AnimalAgent } from "@/types";
import { AnimalAvatar } from "@/components/animals/AnimalAvatar";

interface MentionDropdownProps {
  animals: AnimalAgent[];
  filter: string;
  position: { top: number; left: number };
  onSelect: (animal: AnimalAgent) => void;
  onClose: () => void;
}

export function MentionDropdown({
  animals,
  filter,
  position,
  onSelect,
  onClose,
}: MentionDropdownProps) {
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [selectedIndex, setSelectedIndex] = useState(0);

  const filteredAnimals = useMemo(() => {
    const normalizedFilter = filter.toLowerCase().trim();
    if (!normalizedFilter) return animals;
    
    return animals.filter((animal) =>
      animal.name.toLowerCase().includes(normalizedFilter) ||
      animal.id.toLowerCase().includes(normalizedFilter) ||
      animal.species.toLowerCase().includes(normalizedFilter)
    );
  }, [animals, filter]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [filteredAnimals]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "ArrowDown") {
        event.preventDefault();
        setSelectedIndex((prev) =>
          prev < filteredAnimals.length - 1 ? prev + 1 : prev
        );
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        setSelectedIndex((prev) => (prev > 0 ? prev - 1 : prev));
      } else if (event.key === "Enter" && filteredAnimals.length > 0) {
        event.preventDefault();
        onSelect(filteredAnimals[selectedIndex]);
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [filteredAnimals, selectedIndex, onSelect]);

  // Handle click outside to close
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        onClose();
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [onClose]);

  // Handle escape key to close
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("keydown", handleEscape);
    };
  }, [onClose]);

  const handleSelect = (animal: AnimalAgent) => {
    onSelect(animal);
  };

  // If no matches, don't show dropdown
  if (filteredAnimals.length === 0) {
    return null;
  }

  return (
    <AnimatePresence>
      <motion.div
        ref={dropdownRef}
        initial={{ opacity: 0, y: -10, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: -10, scale: 0.95 }}
        transition={{ duration: 0.15, ease: "easeOut" }}
        className="fixed z-50 w-72 bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden"
        style={{
          top: position.top,
          left: position.left,
        }}
      >
        {/* Header */}
        <div className="px-3 py-2 bg-gradient-to-r from-cartoon-primary/10 to-cartoon-secondary/10 border-b border-gray-100">
          <h3 className="text-xs font-semibold text-gray-600 uppercase tracking-wide">
            提及Agent
          </h3>
        </div>

        {/* Animal List */}
        <div className="max-h-60 overflow-y-auto scrollbar-thin py-1">
          {filteredAnimals.map((animal, index) => (
            <motion.button
              key={animal.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.03 }}
              whileHover={{ backgroundColor: "rgba(255, 107, 157, 0.08)" }}
              whileTap={{ scale: 0.98 }}
              onClick={() => handleSelect(animal)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 text-left transition-colors hover:bg-cartoon-primary/5 ${
                index === selectedIndex
                  ? "bg-cartoon-primary/10 ring-2 ring-cartoon-primary/30"
                  : ""
              }`}
            >
              <AnimalAvatar animal={animal} size="sm" />
              
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="font-medium text-sm text-gray-800 truncate">
                    {animal.name}
                  </span>
                  <span 
                    className="text-xs px-1.5 py-0.5 rounded-full font-medium"
                    style={{ 
                      backgroundColor: `${animal.color}20`,
                      color: animal.color 
                    }}
                  >
                    @{animal.id}
                  </span>
                </div>
                <span className="text-xs text-gray-500 truncate block">
                  {animal.species}
                </span>
              </div>
            </motion.button>
          ))}
        </div>

        {/* Footer hint */}
        <div className="px-3 py-1.5 bg-gray-50 text-xs text-gray-400 text-center border-t border-gray-100">
          {filteredAnimals.length} 个匹配
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
