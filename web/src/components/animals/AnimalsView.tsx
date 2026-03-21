"use client";

import { useEffect } from "react";
import { useAnimalStore } from "@/stores/animalStore";
import { AnimalCard } from "@/components/animals/AnimalCard";
import { Sparkles } from "lucide-react";

const tabs = [
  { value: "all" as const, label: "全部" },
  { value: "local" as const, label: "本地" },
  { value: "h-agent" as const, label: "h-agent" },
  { value: "opencode-session" as const, label: "OpenCode" },
  { value: "network" as const, label: "网络" },
];

export function AnimalsView() {
  const { animals, sourceFilter, setSourceFilter, fetchAnimals } = useAnimalStore();
  
  useEffect(() => {
    fetchAnimals();
  }, [fetchAnimals]);
  
  const filteredAnimals = sourceFilter === "all" 
    ? animals 
    : animals.filter((a) => a.source === sourceFilter);
  
  const favoriteAnimals = filteredAnimals.filter((a) => a.isFavorite);
  const otherAnimals = filteredAnimals.filter((a) => !a.isFavorite);

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <div className="p-4 bg-white border-b border-gray-100">
        <h2 className="text-lg font-bold text-gray-800">Agent列表</h2>
        <p className="text-sm text-gray-500">认识你的协作Agent</p>
      </div>

      <div className="px-4 py-2 bg-white border-b border-gray-100 flex gap-1">
        {tabs.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setSourceFilter(tab.value)}
            className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
              sourceFilter === tab.value
                ? "bg-blue-500 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* Favorites */}
        {favoriteAnimals.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold text-gray-500 mb-3 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-yellow-400" />
              收藏的Agent
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {favoriteAnimals.map((animal) => (
                <AnimalCard key={animal.id} animal={animal} showFavorite />
              ))}
            </div>
          </div>
        )}

        {/* All animals */}
        <div>
          <h3 className="text-sm font-semibold text-gray-500 mb-3">所有Agent</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {otherAnimals.map((animal) => (
              <AnimalCard key={animal.id} animal={animal} showFavorite />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
