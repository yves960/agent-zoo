"use client";

import { motion } from "framer-motion";
import type { AnimalStatus } from "@/types";

interface StatusIndicatorProps {
  status: AnimalStatus;
  size?: "sm" | "md" | "lg";
}

const statusConfig = {
  available: { color: "#00E676", label: "在线" },
  busy: { color: "#FFB74D", label: "忙碌" },
  offline: { color: "#9E9E9E", label: "离线" },
};

const sizeClasses = {
  sm: "w-2.5 h-2.5",
  md: "w-3 h-3",
  lg: "w-4 h-4",
};

export function StatusIndicator({ status, size = "md" }: StatusIndicatorProps) {
  const config = statusConfig[status] || statusConfig.offline;
  const sizeClass = sizeClasses[size];

  return (
    <motion.div
      initial={{ scale: 0 }}
      animate={{ scale: 1 }}
      className={`${sizeClass} rounded-full border-2 border-white`}
      style={{ backgroundColor: config.color }}
      title={config.label}
    />
  );
}
