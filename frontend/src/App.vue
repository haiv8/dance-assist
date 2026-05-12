<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, RouterView, useRoute } from "vue-router";

const route = useRoute();

type NavIcon = "folder" | "play" | "records" | "status";

interface NavItem {
  to: string;
  label: string;
  description: string;
  topbarCopy: string;
  icon: NavIcon;
  aliases?: string[];
}

const navItems: NavItem[] = [
  {
    to: "/upload",
    label: "素材库",
    description: "教师 / 学员视频",
    topbarCopy: "整理教师示范和学员练习视频，准备后续动作分析。",
    icon: "folder",
  },
  {
    to: "/compare",
    label: "开始分析",
    description: "选择视频并运行",
    topbarCopy: "选择一组视频，运行姿态提取、动作对齐和评分分析。",
    icon: "play",
  },
  {
    to: "/records",
    label: "分析记录",
    description: "报告与问题片段",
    topbarCopy: "查看历史报告、评分说明、问题片段和训练建议。",
    icon: "records",
  },
  {
    to: "/settings",
    label: "系统状态",
    description: "模型、磁盘和服务",
    topbarCopy: "检查模型文件、运行目录、磁盘空间和本地服务状态。",
    icon: "status",
  },
];

const iconPaths: Record<NavIcon, string[]> = {
  folder: [
    "M3.75 6.75A2.25 2.25 0 0 1 6 4.5h3.15c.58 0 1.12.28 1.46.75l.64.9H18A2.25 2.25 0 0 1 20.25 9v6.75A2.25 2.25 0 0 1 18 18H6a2.25 2.25 0 0 1-2.25-2.25v-9Z",
    "M5.25 9h13.5",
  ],
  play: [
    "M7.5 5.8v12.4c0 .62.68 1 1.21.67l9.7-6.2a.8.8 0 0 0 0-1.34l-9.7-6.2A.8.8 0 0 0 7.5 5.8Z",
    "M4.5 12a7.5 7.5 0 1 0 15 0 7.5 7.5 0 0 0-15 0Z",
  ],
  records: [
    "M5.25 5.25h13.5v13.5H5.25V5.25Z",
    "M8.25 9h7.5M8.25 12h7.5M8.25 15h4.5",
  ],
  status: [
    "M4.5 13.5h3l2.1-5.25 3.15 8.25 2.1-4.5h4.65",
    "M12 21a9 9 0 1 0-9-9",
  ],
};

function matchesPath(basePath: string) {
  return route.path === basePath || route.path.startsWith(`${basePath}/`);
}

function isActiveNav(item: NavItem) {
  const paths = [item.to, ...(item.aliases || [])];
  return paths.some((path) => matchesPath(path));
}

const currentSection = computed(() => navItems.find((item) => isActiveNav(item)) ?? navItems[1]);

const shellClasses = computed(() => [
  "app-shell",
  "compact-shell",
  { "compare-shell": matchesPath("/compare") },
]);
</script>

<template>
  <div :class="shellClasses">
    <aside class="sidebar compact-sidebar app-sidebar">
      <div class="brand-block compact-brand">
        <div class="brand-mark">DA</div>
        <div class="brand-copy-block">
          <span class="brand-kicker">Dance Assist</span>
          <h1>舞蹈动作分析</h1>
          <p class="brand-copy">本地视频复盘工具</p>
        </div>
      </div>

      <nav class="nav-list app-nav" aria-label="主导航">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          :class="{ active: isActiveNav(item) }"
        >
          <span class="nav-active-bar" aria-hidden="true"></span>
          <span class="nav-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" focusable="false">
              <path
                v-for="path in iconPaths[item.icon]"
                :key="path"
                :d="path"
              />
            </svg>
          </span>
          <span class="nav-copy">
            <span class="nav-label">{{ item.label }}</span>
            <span class="nav-description">{{ item.description }}</span>
          </span>
        </RouterLink>
      </nav>

      <RouterLink class="sidebar-note compact-note workspace-note" to="/settings">
        <span class="workspace-note-title">本地工作台</span>
        <span class="workspace-note-copy">前往系统状态检查</span>
        <span class="workspace-note-current">模型、磁盘和服务</span>
      </RouterLink>
    </aside>

    <div class="shell-main">
      <header class="topbar simple-topbar compact-topbar app-topbar">
        <div class="topbar-copy-block">
          <span class="topbar-kicker">当前位置</span>
          <h2>{{ currentSection.label }}</h2>
          <p class="helper-text topbar-copy">{{ currentSection.topbarCopy }}</p>
        </div>
      </header>

      <main class="content-area">
        <RouterView />
      </main>
    </div>
  </div>
</template>
