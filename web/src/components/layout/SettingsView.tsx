"use client";

import { useState } from "react";
import { Settings, User, Bell, Shield, Palette, Globe } from "lucide-react";

export function SettingsView() {
  const [activeTab, setActiveTab] = useState("general");

  const tabs = [
    { id: "general", label: "通用", icon: Settings },
    { id: "account", label: "账户", icon: User },
    { id: "notifications", label: "通知", icon: Bell },
    { id: "privacy", label: "隐私", icon: Shield },
    { id: "appearance", label: "外观", icon: Palette },
    { id: "language", label: "语言", icon: Globe },
  ];

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <div className="p-4 bg-white border-b border-gray-100">
        <h2 className="text-lg font-bold text-gray-800">设置</h2>
        <p className="text-sm text-gray-500">自定义你的Agent动物园体验</p>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar tabs */}
        <div className="w-48 bg-white border-r border-gray-100 p-2">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  activeTab === tab.id
                    ? "bg-blue-50 text-blue-600 font-medium"
                    : "text-gray-600 hover:bg-gray-50"
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === "general" && (
            <div className="space-y-6">
              <div>
                <h3 className="text-base font-semibold text-gray-800 mb-4">通用设置</h3>
                <div className="bg-white rounded-xl p-4 space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-800">自动连接</p>
                      <p className="text-sm text-gray-500">启动时自动连接WebSocket</p>
                    </div>
                    <Toggle defaultChecked />
                  </div>
                  <div className="border-t border-gray-100 pt-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-gray-800">消息通知</p>
                        <p className="text-sm text-gray-500">收到新消息时显示通知</p>
                      </div>
                      <Toggle defaultChecked />
                    </div>
                  </div>
                  <div className="border-t border-gray-100 pt-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-gray-800">声音提示</p>
                        <p className="text-sm text-gray-500">播放提示音</p>
                      </div>
                      <Toggle />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "account" && (
            <div className="space-y-6">
              <div>
                <h3 className="text-base font-semibold text-gray-800 mb-4">账户信息</h3>
                <div className="bg-white rounded-xl p-4">
                  <p className="text-gray-500 text-sm">账户管理功能即将推出</p>
                </div>
              </div>
            </div>
          )}

          {activeTab === "notifications" && (
            <div className="space-y-6">
              <div>
                <h3 className="text-base font-semibold text-gray-800 mb-4">通知设置</h3>
                <div className="bg-white rounded-xl p-4 space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-800">桌面通知</p>
                      <p className="text-sm text-gray-500">允许桌面通知权限</p>
                    </div>
                    <Toggle defaultChecked />
                  </div>
                  <div className="border-t border-gray-100 pt-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-gray-800">声音提醒</p>
                        <p className="text-sm text-gray-500">新消息播放提示音</p>
                      </div>
                      <Toggle />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "privacy" && (
            <div className="space-y-6">
              <div>
                <h3 className="text-base font-semibold text-gray-800 mb-4">隐私与安全</h3>
                <div className="bg-white rounded-xl p-4 space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-800">记录对话历史</p>
                      <p className="text-sm text-gray-500">保存对话记录到本地</p>
                    </div>
                    <Toggle defaultChecked />
                  </div>
                  <div className="border-t border-gray-100 pt-4">
                    <button className="text-sm text-red-500 hover:text-red-600">
                      清除所有对话历史
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "appearance" && (
            <div className="space-y-6">
              <div>
                <h3 className="text-base font-semibold text-gray-800 mb-4">外观设置</h3>
                <div className="bg-white rounded-xl p-4">
                  <p className="text-gray-500 text-sm">更多主题选项即将推出</p>
                </div>
              </div>
            </div>
          )}

          {activeTab === "language" && (
            <div className="space-y-6">
              <div>
                <h3 className="text-base font-semibold text-gray-800 mb-4">语言设置</h3>
                <div className="bg-white rounded-xl p-4">
                  <p className="text-gray-500 text-sm">当前仅支持简体中文</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Simple toggle switch component
function Toggle({ defaultChecked = false }: { defaultChecked?: boolean }) {
  const [checked, setChecked] = useState(defaultChecked);

  return (
    <button
      onClick={() => setChecked(!checked)}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
        checked ? "bg-blue-500" : "bg-gray-300"
      }`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
          checked ? "translate-x-6" : "translate-x-1"
        }`}
      />
    </button>
  );
}
