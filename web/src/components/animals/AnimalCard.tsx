"use client";

import { motion } from "framer-motion";
import { Star } from "lucide-react";
import { useAnimalStore } from "@/stores/animalStore";
import type { AnimalAgent } from "@/types";
import { AnimalAvatar } from "./AnimalAvatar";
import { StatusIndicator } from "./StatusIndicator";

interface AnimalCardProps {
  animal: AnimalAgent;
  isSelected?: boolean;
  onClick?: () => void;
  showFavorite?: boolean;
  compact?: boolean;
}

export function AnimalCard({ 
  animal, 
  isSelected = false, 
  onClick, 
  showFavorite = true,
  compact = false 
}: AnimalCardProps) {
  const { toggleFavorite } = useAnimalStore();
  
  // Defensive check for undefined animal
  if (!animal || !animal.id) {
    return null;
  }

  return (
    <motion.div
      whileHover={{ scale: 1.02, y: -2 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
      className={`
        relative cursor-pointer rounded-cartoon-lg overflow-hidden
        transition-shadow duration-300
        ${isSelected ? "ring-4 ring-cartoon-primary shadow-cartoon-lg" : "shadow-cartoon hover:shadow-cartoon-lg"}
        ${compact ? "p-3" : "p-4"}
        bg-white
      `}
    >
      {/* Background color accent */}
      <div 
        className="absolute inset-0 opacity-10"
        style={{ backgroundColor: animal.color }}
      />
      
      <div className="relative flex items-center gap-3">
        {/* Avatar with status */}
        <div className="relative">
          <AnimalAvatar animal={animal} size={compact ? "sm" : "md"} />
          <div className="absolute -bottom-1 -right-1">
            <StatusIndicator status={animal.status} size="sm" />
          </div>
        </div>
        
        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className={`font-bold text-gray-800 truncate ${compact ? "text-sm" : "text-base"}`}>
              {animal.name}
            </h3>
            {animal.isFavorite && showFavorite && (
              <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
            )}
          </div>
          <p className={`text-gray-500 truncate ${compact ? "text-xs" : "text-sm"}`}>
            {animal.species}
          </p>
          {!compact && (
            <p className="text-xs text-gray-400 mt-1 line-clamp-1">
              {animal.personality}
            </p>
          )}
        </div>
        
        {/* Selection indicator */}
        {isSelected && (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className="flex-shrink-0 w-6 h-6 rounded-full bg-cartoon-primary flex items-center justify-center"
          >
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
            </svg>
          </motion.div>
        )}
      </div>
      
      {/* Favorite button */}
      {showFavorite && !compact && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            toggleFavorite(animal.id);
          }}
          className="absolute top-2 right-2 p-1 rounded-full hover:bg-gray-100 transition-colors"
        >
          <Star 
            className={`w-5 h-5 transition-colors ${
              animal.isFavorite ? "fill-yellow-400 text-yellow-400" : "text-gray-300"
            }`}
          />
        </button>
      )}
    </motion.div>
  );
}
