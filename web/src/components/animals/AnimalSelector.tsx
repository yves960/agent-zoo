"use client";

import { motion, AnimatePresence } from "framer-motion";
import { X, Users, Sparkles } from "lucide-react";
import { useEffect } from "react";
import { useAnimalStore } from "@/stores/animalStore";
import { useConversationStore } from "@/stores/conversationStore";
import { useUIStore } from "@/stores/uiStore";
import { AnimalCard } from "./AnimalCard";
import { Button } from "@/components/ui/Button";
import type { AnimalType } from "@/types";

interface AnimalSelectorProps {
  isOpen: boolean;
  onClose: () => void;
}

export function AnimalSelector({ isOpen, onClose }: AnimalSelectorProps) {
  const { animals, selectedAnimals, selectAnimal, deselectAnimal, clearSelection, getFavoriteAnimals, fetchAnimals } = useAnimalStore();
  
  useEffect(() => {
    if (isOpen) {
      fetchAnimals();
    }
  }, [isOpen, fetchAnimals]);
  const { createConversation } = useConversationStore();
  const { setCurrentView } = useUIStore();
  
  const favoriteAnimals = getFavoriteAnimals();
  const otherAnimals = animals.filter(a => !a.isFavorite);

  const handleStartChat = () => {
    if (selectedAnimals.length === 0) return;
    
    const selectedAnimalObjects = animals.filter(a => selectedAnimals.includes(a.id));
    const animalNames = selectedAnimalObjects.map(a => a.name).join("、");
    
    createConversation(
      `与 ${animalNames} 的对话`,
      selectedAnimalObjects
    );
    
    clearSelection();
    onClose();
    setCurrentView("chat");
  };

  const toggleAnimal = (id: AnimalType) => {
    if (selectedAnimals.includes(id)) {
      deselectAnimal(id);
    } else {
      selectAnimal(id);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-black/40 backdrop-blur-sm"
          />
          
          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            className="relative w-full max-w-2xl max-h-[85vh] bg-white rounded-cartoon-xl shadow-cartoon-lg overflow-hidden"
          >
            {/* Header */}
            <div className="sticky top-0 z-10 bg-gradient-to-r from-cartoon-xueqiu/10 via-cartoon-liuliu/10 to-cartoon-xiaohuang/10 p-6 border-b border-gray-100">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-cartoon-primary/20 rounded-cartoon">
                    <Users className="w-6 h-6 text-cartoon-primary" />
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-gray-800">选择协作Agent</h2>
                    <p className="text-sm text-gray-500">选择你想一起聊天的Agent</p>
                  </div>
                </div>
                <button
                  onClick={onClose}
                  className="p-2 hover:bg-gray-100 rounded-full transition-colors"
                >
                  <X className="w-5 h-5 text-gray-500" />
                </button>
              </div>
              
              {/* Selection count */}
              {selectedAnimals.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mt-4 flex items-center gap-2 text-sm text-cartoon-primary"
                >
                  <Sparkles className="w-4 h-4" />
                  <span>已选择 {selectedAnimals.length} 个Agent</span>
                </motion.div>
              )}
            </div>
            
            {/* Content */}
            <div className="p-6 overflow-y-auto max-h-[50vh]">
              {/* Favorites */}
              {favoriteAnimals.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-sm font-semibold text-gray-500 mb-3 flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-yellow-400" />
                    收藏的Agent
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {favoriteAnimals.map((animal) => (
                      <AnimalCard
                        key={animal.id}
                        animal={animal}
                        isSelected={selectedAnimals.includes(animal.id)}
                        onClick={() => toggleAnimal(animal.id)}
                        showFavorite={false}
                      />
                    ))}
                  </div>
                </div>
              )}
              
              {/* All animals */}
              <div>
                <h3 className="text-sm font-semibold text-gray-500 mb-3">
                  所有Agent
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {otherAnimals.map((animal) => (
                    <AnimalCard
                      key={animal.id}
                      animal={animal}
                      isSelected={selectedAnimals.includes(animal.id)}
                      onClick={() => toggleAnimal(animal.id)}
                    />
                  ))}
                </div>
              </div>
            </div>
            
            {/* Footer */}
            <div className="sticky bottom-0 bg-white p-6 border-t border-gray-100 flex gap-3">
              <Button
                variant="outline"
                onClick={() => {
                  clearSelection();
                  onClose();
                }}
                className="flex-1"
              >
                取消
              </Button>
              <Button
                variant="primary"
                onClick={handleStartChat}
                disabled={selectedAnimals.length === 0}
                className="flex-1"
              >
                开始聊天
              </Button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
