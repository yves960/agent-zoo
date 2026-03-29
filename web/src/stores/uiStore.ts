import { create } from "zustand";
import type { ViewType, Toast } from "@/types";

interface UIState {
  currentView: ViewType;
  sidebarOpen: boolean;
  toasts: Toast[];
  searchQuery: string;
  selectedAnimalFilter: string | null;
  animalSelectorOpen: boolean;
}

interface UIActions {
  setCurrentView: (view: ViewType) => void;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  
  // Toast notifications
  addToast: (toast: Omit<Toast, "id">) => void;
  removeToast: (id: string) => void;
  clearToasts: () => void;
  
  // Search and filter
  setSearchQuery: (query: string) => void;
  setAnimalFilter: (animalId: string | null) => void;
  clearFilters: () => void;

  // Animal selector
  openAnimalSelector: () => void;
  closeAnimalSelector: () => void;
}

const generateId = () => Math.random().toString(36).substring(2, 15);

export const useUIStore = create<UIState & UIActions>((set, get) => ({
  currentView: "chat",
  sidebarOpen: true,
  toasts: [],
  searchQuery: "",
  selectedAnimalFilter: null,
  animalSelectorOpen: false,

  setCurrentView: (view) => set({ currentView: view }),
  
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  
  setSidebarOpen: (open) => set({ sidebarOpen: open }),

  addToast: (toast) => {
    const id = generateId();
    const newToast = { ...toast, id };
    set((state) => ({ toasts: [...state.toasts, newToast] }));
    
    // Auto-remove after duration
    const duration = toast.duration || 5000;
    setTimeout(() => {
      get().removeToast(id);
    }, duration);
  },

  removeToast: (id) => {
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    }));
  },

  clearToasts: () => set({ toasts: [] }),

  setSearchQuery: (query) => set({ searchQuery: query }),

  setAnimalFilter: (animalId) => set({ selectedAnimalFilter: animalId }),

  clearFilters: () => set({ searchQuery: "", selectedAnimalFilter: null }),

  openAnimalSelector: () => set({ animalSelectorOpen: true }),
  closeAnimalSelector: () => set({ animalSelectorOpen: false }),
}));
