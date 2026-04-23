import { createRouter, createWebHashHistory } from "vue-router";

import UploadPage from "../pages/UploadPage.vue";
import ComparePage from "../pages/ComparePage.vue";
import RecordsPage from "../pages/RecordsPage.vue";
import SystemSettingsPage from "../pages/SystemSettingsPage.vue";

export const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: "/", redirect: "/upload" },
    { path: "/upload", component: UploadPage },
    { path: "/compare", component: ComparePage },
    { path: "/records", component: RecordsPage },
    {
      path: "/tasks",
      redirect: (to) => ({ path: "/records", query: { ...to.query, tab: "running" } }),
    },
    {
      path: "/reports",
      redirect: (to) => ({ path: "/records", query: { ...to.query, tab: "completed" } }),
    },
    {
      path: "/issues",
      redirect: (to) => ({ path: "/records", query: { ...to.query, tab: "issues" } }),
    },
    { path: "/settings", component: SystemSettingsPage },
  ],
});
