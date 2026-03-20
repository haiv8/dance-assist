import { createRouter, createWebHashHistory } from "vue-router";

import UploadPage from "../pages/UploadPage.vue";
import ComparePage from "../pages/ComparePage.vue";
import TaskCenterPage from "../pages/TaskCenterPage.vue";
import ReportCenterPage from "../pages/ReportCenterPage.vue";
import IssueReplayPage from "../pages/IssueReplayPage.vue";
import SystemSettingsPage from "../pages/SystemSettingsPage.vue";

export const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: "/", redirect: "/upload" },
    { path: "/upload", component: UploadPage },
    { path: "/compare", component: ComparePage },
    { path: "/tasks", component: TaskCenterPage },
    { path: "/reports", component: ReportCenterPage },
    { path: "/issues", component: IssueReplayPage },
    { path: "/settings", component: SystemSettingsPage },
  ],
});
