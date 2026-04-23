<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, RouterView, useRoute } from "vue-router";

const route = useRoute();

const navItems = [
  {
    to: "/upload",
    label: "素材库",
    eyebrow: "Library",
    copy: "管理教师示范与学员练习素材。",
  },
  {
    to: "/compare",
    label: "开始分析",
    eyebrow: "Analyze",
    copy: "发起动作对照分析并查看结果。",
  },
  {
    to: "/records",
    label: "分析记录",
    eyebrow: "Records",
    copy: "统一查看任务、报告与问题片段。",
  },
  {
    to: "/settings",
    label: "系统设置",
    eyebrow: "Settings",
    copy: "检查环境状态与维护本地服务。",
  },
];

const currentSection = computed(() => {
  const path = route.path;
  if (path.startsWith("/tasks") || path.startsWith("/reports") || path.startsWith("/issues")) {
    return navItems[2];
  }
  return navItems.find((item) => path.startsWith(item.to)) ?? navItems[1];
});
</script>

<template>
  <div class="app-shell compact-shell">
    <aside class="sidebar compact-sidebar">
      <div class="brand-block editorial-brand compact-brand">
        <div class="brand-mark">DA</div>
        <div class="brand-copy-block">
          <span class="brand-kicker">Dance Assist</span>
          <h1>舞蹈动作分析工作台</h1>
          <p class="brand-copy">本地桌面版</p>
        </div>
      </div>

      <nav class="nav-list">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          :class="{ active: route.path.startsWith(item.to) || (item.to === '/records' && (route.path.startsWith('/tasks') || route.path.startsWith('/reports') || route.path.startsWith('/issues'))) }"
        >
          <span class="nav-label">{{ item.label }}</span>
          <span class="nav-kicker">{{ item.eyebrow }}</span>
        </RouterLink>
      </nav>

      <div class="sidebar-note editorial-note compact-note">
        <span class="status-pill online">本地服务在线</span>
        <div class="note-metrics">
          <div class="note-metric">
            <span>当前区域</span>
            <strong>{{ currentSection.label }}</strong>
          </div>
        </div>
      </div>
    </aside>

    <div class="shell-main">
      <header class="topbar simple-topbar editorial-topbar compact-topbar">
        <div class="topbar-copy-block">
          <span class="topbar-kicker">Workspace</span>
          <h2>{{ currentSection.label }}</h2>
          <p class="helper-text topbar-copy">{{ currentSection.copy }}</p>
        </div>
      </header>

      <main class="content-area">
        <RouterView />
      </main>
    </div>
  </div>
</template>
