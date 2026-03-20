import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { AnimalAgent, AnimalType, AnimalStatus } from "@/types";

// Fallback details for agents not fully configured in backend
// These supplement what comes from /api/animals
const ANIMAL_DETAILS: Partial<Record<AnimalType, { personality: string; avatar: string; traits: string[]; specialties: string[]; greetings: string[]; description: string }>> = {
  xueqiu: {
    traits: ["聪明", "友善", "可靠", "细心"],
    specialties: ["代码审查", "架构设计", "问题诊断"],
    greetings: ["汪汪！我是雪球，很高兴见到你！", "需要我帮忙吗？我会尽力协助你！"],
    description: "雪球是一只可爱的雪纳瑞犬，拥有蓬松的白色毛发和聪明的大眼睛。他是团队的主架构师，擅长代码审查和系统设计。",
    personality: "聪明、友善、喜欢帮助别人",
    avatar: "/avatars/xueqiu.svg",
  },
  liuliu: {
    traits: ["活泼", "好奇", "爱唱歌", "机智"],
    specialties: ["代码审查", "创意建议", "问题分析"],
    greetings: ["啾啾！我是六六，准备好一起工作了！", "嗨！有什么有趣的问题要讨论吗？"],
    description: "六六是一只蓝色的虎皮鹦鹉，羽毛像天空一样美丽。她喜欢唱歌，总是充满好奇心，擅长代码审查和提供创意建议。",
    personality: "活泼、好奇、喜欢唱歌",
    avatar: "/avatars/liuliu.svg",
  },
  xiaohuang: {
    traits: ["开朗", "乐观", "充满活力", "热情"],
    specialties: ["视觉设计", "用户体验", "创意灵感"],
    greetings: ["唧唧！我是小黄，让我们一起创造奇迹吧！", "你好！准备好开始精彩的对话了吗？"],
    description: "小黄是一只黄绿相间的虎皮鹦鹉，像阳光一样温暖。他是团队的视觉设计师，擅长UI/UX设计和提供创意灵感。",
    personality: "开朗、乐观、充满活力",
    avatar: "/avatars/xiaohuang.svg",
  },
  meiqiu: {
    traits: ["全能", "勤快", "靠谱"],
    specialties: ["任务规划", "多领域协助", "问题解决"],
    greetings: ["嗨！我是煤球，有什么需要帮忙的吗？", "煤球在此，随时待命！"],
    description: "煤球是一只忠诚的田园犬，是团队的全能助手。",
    personality: "忠诚、勤快、全能",
    avatar: "/avatars/meiqiu.svg",
  },
};

interface AnimalState {
  animals: AnimalAgent[];
  selectedAnimals: AnimalType[];
  favorites: AnimalType[];
  isLoading: boolean;
  lastFetched: number | null;
}

interface AnimalActions {
  setAnimalStatus: (id: AnimalType, status: AnimalStatus) => void;
  toggleFavorite: (id: AnimalType) => void;
  selectAnimal: (id: AnimalType) => void;
  deselectAnimal: (id: AnimalType) => void;
  clearSelection: () => void;
  getAnimalById: (id: AnimalType) => AnimalAgent | undefined;
  getFavoriteAnimals: () => AnimalAgent[];
  getAvailableAnimals: () => AnimalAgent[];
  fetchAnimals: () => Promise<void>;
}

const mergeAnimalData = (
  apiAnimals: Record<string, {
    id: string;
    name: string;
    species: string;
    description: string;
    color: string;
    cli: string;
    model: string;
    enabled: boolean;
    mention_patterns?: string[];
  }>
): AnimalAgent[] => {
  return Object.values(apiAnimals).map((animal) => {
    const details = ANIMAL_DETAILS[animal.id as AnimalType];
    const id = animal.id as AnimalType;

    return {
      id,
      name: animal.name,
      species: animal.species,
      description: animal.description || details?.description || "",
      color: animal.color,
      personality: details?.personality || "友善、乐于助人",
      avatar: details?.avatar || `/avatars/${id}.svg`,
      status: "available" as AnimalStatus,
      isFavorite: false,
      traits: details?.traits || [],
      specialties: details?.specialties || [],
      greetings: details?.greetings || [`你好！我是${animal.name}，很高兴认识你！`],
      cli: animal.cli,
      model: animal.model,
    };
  });
};

export const useAnimalStore = create<AnimalState & AnimalActions>()(
  persist(
    (set, get) => ({
      animals: [],
      selectedAnimals: [],
      favorites: [],
      isLoading: false,
      lastFetched: null,

      setAnimalStatus: (id, status) => {
        set((state) => ({
          animals: state.animals.map((animal) =>
            animal.id === id ? { ...animal, status } : animal
          ),
        }));
      },

      toggleFavorite: (id) => {
        set((state) => {
          const isFav = state.favorites.includes(id);
          return {
            favorites: isFav
              ? state.favorites.filter((f) => f !== id)
              : [...state.favorites, id],
            animals: state.animals.map((animal) =>
              animal.id === id ? { ...animal, isFavorite: !isFav } : animal
            ),
          };
        });
      },

      selectAnimal: (id) => {
        set((state) => ({
          selectedAnimals: state.selectedAnimals.includes(id)
            ? state.selectedAnimals
            : [...state.selectedAnimals, id],
        }));
      },

      deselectAnimal: (id) => {
        set((state) => ({
          selectedAnimals: state.selectedAnimals.filter((a) => a !== id),
        }));
      },

      clearSelection: () => {
        set({ selectedAnimals: [] });
      },

      getAnimalById: (id) => {
        return get().animals.find((animal) => animal.id === id);
      },

      getFavoriteAnimals: () => {
        return get().animals.filter((animal) => animal.isFavorite);
      },

      getAvailableAnimals: () => {
        return get().animals.filter((animal) => animal.status === "available");
      },

      fetchAnimals: async () => {
        const { isLoading, lastFetched } = get();
        // Avoid duplicate concurrent fetches; cache for 30 seconds
        if (isLoading || (lastFetched && Date.now() - lastFetched < 30_000)) {
          return;
        }

        set({ isLoading: true });
        try {
          const res = await fetch("/api/animals");
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const data = await res.json();
          const apiAnimals = data.animals || {};

          set({
            animals: mergeAnimalData(apiAnimals),
            lastFetched: Date.now(),
            isLoading: false,
          });
        } catch (err) {
          console.error("[animalStore] fetchAnimals failed:", err);
          set({ isLoading: false });
        }
      },
    }),
    {
      name: "animal-store",
      partialize: (state) => ({ favorites: state.favorites }),
    }
  )
);
