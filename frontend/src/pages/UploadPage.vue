<template>
  <main class="app-page upload-page">
    <section class="surface-card page-head">
      <div class="page-head-row">
        <div>
          <h1>&#32032;&#26448;&#31649;&#29702;</h1>
          <p class="page-subtitle">&#26412;&#39029;&#21482;&#20570;&#19977;&#20214;&#20107;&#65306;&#19978;&#20256;&#12289;&#31649;&#29702;&#12289;&#24555;&#36895;&#24102;&#20837;&#20998;&#26512;&#12290;</p>
        </div>
        <div class="action-row">
          <RouterLink class="link-button secondary-button" to="/compare">&#21069;&#24448;&#21160;&#20316;&#20998;&#26512;</RouterLink>
        </div>
      </div>

      <div class="status-strip">
        <div class="status-cell"><span class="status-caption">&#32032;&#26448;&#24635;&#25968;</span><strong class="status-main">{{ items.length }}</strong></div>
        <div class="status-cell"><span class="status-caption">&#25945;&#24072;&#32032;&#26448;</span><strong class="status-main">{{ teacherItems.length }}</strong></div>
        <div class="status-cell"><span class="status-caption">&#23398;&#21592;&#32032;&#26448;</span><strong class="status-main">{{ userItems.length }}</strong></div>
        <div class="status-cell emphasis"><span class="status-caption">&#25512;&#33616;&#29366;&#24577;</span><strong class="status-main">{{ inventoryHint }}</strong></div>
      </div>
    </section>

    <section class="selection-grid upload-grid">
      <article class="surface-card">
        <div class="panel-head compact-head">
          <div>
            <h2>&#26412;&#27425;&#19978;&#20256;</h2>
            <p class="helper-text">&#26032;&#19978;&#20256;&#21482;&#24433;&#21709;&#21491;&#20391;&#30340;&#26412;&#27425;&#32467;&#26524;&#65292;&#19981;&#20250;&#20882;&#20805;&#21382;&#21490;&#32032;&#26448;&#12290;</p>
          </div>
        </div>

        <div class="field-grid two-col-fields">
          <div class="field-block">
            <label class="field-label">&#35282;&#33394;</label>
            <select v-model="role">
              <option value="teacher">&#25945;&#24072;&#31034;&#33539;</option>
              <option value="user">&#23398;&#21592;&#32451;&#20064;</option>
            </select>
          </div>
          <div class="field-block">
            <label class="field-label">&#32032;&#26448;&#21517;&#31216;</label>
            <input v-model.trim="name" type="text" :placeholder="namePlaceholder" />
          </div>
        </div>

        <input :key="fileInputKey" class="file-input" type="file" accept=".mp4,.mov,.avi,.mkv,.m4v" @change="onFileChange" />
        <p class="helper-text" style="margin-top: 10px;">{{ draftState }}</p>

        <div class="action-row" style="margin-top: 16px;">
          <button :disabled="uploading || !file" @click="submitUpload">{{ uploading ? uploadLoadingText : uploadActionText }}</button>
          <button class="secondary-button" :disabled="listing" @click="loadAllContext">{{ listing ? syncLoadingText : syncActionText }}</button>
          <button class="secondary-button" :disabled="uploading" @click="resetDraft">{{ resetActionText }}</button>
        </div>

        <div v-if="error" class="feedback-inline" style="margin-top: 12px;">{{ error }}</div>
        <div v-else-if="actionMessage" class="feedback-state" data-tone="loading" style="margin-top: 12px;">
          <strong class="feedback-state-title">{{ actionDoneTitle }}</strong>
          <span class="feedback-state-copy">{{ actionMessage }}</span>
        </div>
      </article>

      <article class="surface-card">
        <div class="panel-head compact-head">
          <div>
            <h2>&#26412;&#27425;&#32467;&#26524;&#19982;&#25512;&#33616;</h2>
            <p class="helper-text">&#21487;&#20197;&#30452;&#25509;&#29992;&#26368;&#26032;&#19978;&#20256;&#12289;&#26368;&#36817;&#20351;&#29992;&#25110;&#25512;&#33616;&#37197;&#23545;&#36827;&#20837;&#20998;&#26512;&#12290;</p>
          </div>
        </div>

        <div class="summary-stack">
          <div class="summary-row"><span>&#26412;&#27425;&#19978;&#20256;</span><strong>{{ result?.filename || emptyText }}</strong></div>
          <div class="summary-row"><span>&#26368;&#36817;&#20351;&#29992;</span><strong>{{ recentTask?.pair_name || emptyText }}</strong></div>
          <div class="summary-row"><span>&#25512;&#33616;&#25945;&#24072;</span><strong>{{ newestTeacher?.filename || emptyTeacherText }}</strong></div>
          <div class="summary-row"><span>&#25512;&#33616;&#23398;&#21592;</span><strong>{{ newestUser?.filename || emptyUserText }}</strong></div>
        </div>

        <div class="action-row" style="margin-top: 16px;">
          <button class="secondary-button" :disabled="!canUseRecentTask" @click="useRecentTaskPair">&#29992;&#26368;&#36817;&#37197;&#23545;</button>
          <button class="secondary-button" :disabled="!canUseRecommendedPair" @click="useRecommendedPair">&#29992;&#25512;&#33616;&#37197;&#23545;</button>
          <button class="secondary-button" :disabled="!result" @click="openLatestInCompare">&#29992;&#26412;&#27425;&#32467;&#26524;</button>
        </div>
      </article>
    </section>

    <section class="selection-grid library-grid">
      <article class="surface-card">
        <div class="panel-head compact-head"><h2>&#25945;&#24072;&#32032;&#26448;&#24211;</h2></div>
        <div v-if="!teacherItems.length" class="feedback-state" data-tone="empty">
          <strong class="feedback-state-title">&#26242;&#26080;&#25945;&#24072;&#32032;&#26448;</strong>
        </div>
        <ul v-else class="list-clean asset-list-simple">
          <li v-for="item in teacherItems" :key="item.video_id" class="asset-item-simple">
            <div class="asset-main">
              <template v-if="editingVideoId === item.video_id">
                <input v-model.trim="editingName" type="text" class="asset-input" :placeholder="renamePlaceholder" />
              </template>
              <template v-else>
                <strong>{{ item.filename }}</strong>
              </template>
              <span class="helper-text">{{ formatDate(item.uploaded_at) }} · {{ formatBytes(item.size_bytes) }}</span>
            </div>
            <div class="asset-actions">
              <button class="secondary-button" @click="openInCompare(item)">{{ useInCompareText }}</button>
              <a class="link-button secondary-button" :href="absMediaUrl(item.url)" target="_blank">{{ openText }}</a>
              <button v-if="editingVideoId !== item.video_id" class="secondary-button" :disabled="busyVideoId === item.video_id" @click="startRename(item)">{{ renameText }}</button>
              <button v-else class="secondary-button" :disabled="busyVideoId === item.video_id || !editingName" @click="saveRename(item)">{{ saveText }}</button>
              <button v-if="editingVideoId === item.video_id" class="ghost-button" :disabled="busyVideoId === item.video_id" @click="cancelRename">{{ cancelText }}</button>
              <button class="ghost-button danger-text" :disabled="busyVideoId === item.video_id" @click="removeItem(item)">{{ deleteText }}</button>
            </div>
          </li>
        </ul>
      </article>

      <article class="surface-card">
        <div class="panel-head compact-head"><h2>&#23398;&#21592;&#32032;&#26448;&#24211;</h2></div>
        <div v-if="!userItems.length" class="feedback-state" data-tone="empty">
          <strong class="feedback-state-title">&#26242;&#26080;&#23398;&#21592;&#32032;&#26448;</strong>
        </div>
        <ul v-else class="list-clean asset-list-simple">
          <li v-for="item in userItems" :key="item.video_id" class="asset-item-simple">
            <div class="asset-main">
              <template v-if="editingVideoId === item.video_id">
                <input v-model.trim="editingName" type="text" class="asset-input" :placeholder="renamePlaceholder" />
              </template>
              <template v-else>
                <strong>{{ item.filename }}</strong>
              </template>
              <span class="helper-text">{{ formatDate(item.uploaded_at) }} · {{ formatBytes(item.size_bytes) }}</span>
            </div>
            <div class="asset-actions">
              <button class="secondary-button" @click="openInCompare(item)">{{ useInCompareText }}</button>
              <a class="link-button secondary-button" :href="absMediaUrl(item.url)" target="_blank">{{ openText }}</a>
              <button v-if="editingVideoId !== item.video_id" class="secondary-button" :disabled="busyVideoId === item.video_id" @click="startRename(item)">{{ renameText }}</button>
              <button v-else class="secondary-button" :disabled="busyVideoId === item.video_id || !editingName" @click="saveRename(item)">{{ saveText }}</button>
              <button v-if="editingVideoId === item.video_id" class="ghost-button" :disabled="busyVideoId === item.video_id" @click="cancelRename">{{ cancelText }}</button>
              <button class="ghost-button danger-text" :disabled="busyVideoId === item.video_id" @click="removeItem(item)">{{ deleteText }}</button>
            </div>
          </li>
        </ul>
      </article>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";
import { absMediaUrl } from "../api/http";
import { listPipelineTasks } from "../api/pipelines";
import { deleteVideo, listVideos, renameVideo, uploadVideo } from "../api/videos";
import type { PipelineTaskListItem, RoleType, VideoItem, VideoUploadResponse } from "../types/video";

const uploadActionText = "提交素材";
const uploadLoadingText = "上传中...";
const syncActionText = "同步素材库";
const syncLoadingText = "同步中...";
const resetActionText = "清空本次表单";
const actionDoneTitle = "素材操作已完成";
const renamePlaceholder = "输入新的素材名称";
const useInCompareText = "用于分析";
const openText = "打开";
const renameText = "重命名";
const saveText = "保存";
const cancelText = "取消";
const deleteText = "删除";
const emptyText = "暂无";
const emptyTeacherText = "暂无教师素材";
const emptyUserText = "暂无学员素材";

const router = useRouter();
const role = ref<RoleType>("teacher");
const name = ref("");
const file = ref<File | null>(null);
const fileInputKey = ref(0);
const uploading = ref(false);
const listing = ref(false);
const error = ref("");
const actionMessage = ref("");
const result = ref<VideoUploadResponse | null>(null);
const items = ref<VideoItem[]>([]);
const recentTask = ref<PipelineTaskListItem | null>(null);
const editingVideoId = ref("");
const editingName = ref("");
const busyVideoId = ref("");

const teacherItems = computed(() => [...items.value].filter((item) => item.role === "teacher").sort(byTime));
const userItems = computed(() => [...items.value].filter((item) => item.role === "user").sort(byTime));
const newestTeacher = computed(() => teacherItems.value[0] ?? null);
const newestUser = computed(() => userItems.value[0] ?? null);
const canUseRecommendedPair = computed(() => Boolean(newestTeacher.value && newestUser.value));
const canUseRecentTask = computed(() => Boolean(recentTask.value?.teacher_video_id && recentTask.value?.user_video_id));
const namePlaceholder = computed(() => (role.value === "teacher" ? "例如：教师-八拍示范01" : "例如：学员-基础练习01"));
const inventoryHint = computed(() => {
  if (!teacherItems.value.length) return "先补入教师示范";
  if (!userItems.value.length) return "再补入学员练习";
  return "已可直接开始对照";
});
const draftState = computed(() => {
  if (!file.value) return "当前还没有选择文件，右侧不会再拿历史素材冒充本次上传结果。";
  return `当前将以“${roleText(role.value)}”角色入库：${file.value.name}`;
});

function byTime(a: VideoItem, b: VideoItem) {
  return String(b.uploaded_at || "").localeCompare(String(a.uploaded_at || ""));
}

function roleText(value: RoleType) {
  return value === "teacher" ? "教师示范" : "学员练习";
}

function onFileChange(event: Event) {
  const target = event.target as HTMLInputElement;
  file.value = target.files?.[0] ?? null;
}

function resetDraft() {
  role.value = "teacher";
  name.value = "";
  file.value = null;
  result.value = null;
  error.value = "";
  actionMessage.value = "";
  fileInputKey.value += 1;
}

function clearEditing() {
  editingVideoId.value = "";
  editingName.value = "";
  busyVideoId.value = "";
}

function startRename(item: VideoItem) {
  editingVideoId.value = item.video_id;
  editingName.value = stripStem(item.filename, item.video_id);
  error.value = "";
  actionMessage.value = "";
}

function cancelRename() {
  clearEditing();
}

async function saveRename(item: VideoItem) {
  const nextName = editingName.value.trim();
  if (!nextName) {
    error.value = "素材名称不能为空";
    return;
  }
  busyVideoId.value = item.video_id;
  try {
    const response = await renameVideo({ videoId: item.video_id, role: item.role, name: nextName });
    if (result.value?.video_id === item.video_id && response.item) {
      result.value = { ...result.value, filename: response.item.filename, url: response.item.url };
    }
    clearEditing();
    actionMessage.value = response.message;
    await loadAllContext();
  } catch (err: any) {
    error.value = err?.response?.data?.detail ?? err?.message ?? "素材重命名失败";
    busyVideoId.value = "";
  }
}

async function removeItem(item: VideoItem) {
  if (!window.confirm(`确定删除素材“${item.filename}”吗？`)) return;
  busyVideoId.value = item.video_id;
  try {
    const response = await deleteVideo({ videoId: item.video_id, role: item.role });
    if (result.value?.video_id === item.video_id) result.value = null;
    if (editingVideoId.value === item.video_id) clearEditing();
    actionMessage.value = response.message;
    await loadAllContext();
  } catch (err: any) {
    error.value = err?.response?.data?.detail ?? err?.message ?? "素材删除失败";
  } finally {
    if (busyVideoId.value === item.video_id) busyVideoId.value = "";
  }
}

async function submitUpload() {
  if (!file.value) return;
  uploading.value = true;
  error.value = "";
  try {
    const data = await uploadVideo({ file: file.value, role: role.value, name: name.value });
    result.value = data;
    file.value = null;
    name.value = "";
    fileInputKey.value += 1;
    actionMessage.value = "素材已入库，素材库与推荐配对已同步更新。";
    await loadAllContext();
  } catch (err: any) {
    error.value = err?.response?.data?.detail ?? err?.message ?? "上传失败";
  } finally {
    uploading.value = false;
  }
}

async function loadRecentTask() {
  try {
    const data = await listPipelineTasks({ limit: 20, status: "done" });
    recentTask.value = data.items.find((item) => item.teacher_video_id && item.user_video_id) ?? null;
  } catch {
    recentTask.value = null;
  }
}

async function loadAllContext() {
  listing.value = true;
  error.value = "";
  try {
    const [videos] = await Promise.all([listVideos("all"), loadRecentTask()]);
    items.value = videos.items;
  } catch (err: any) {
    error.value = err?.response?.data?.detail ?? err?.message ?? "素材库加载失败";
  } finally {
    listing.value = false;
  }
}

function routeToCompare(teacherId?: string | null, userId?: string | null, pipelineId?: string | null) {
  if (!teacherId || !userId) {
    error.value = "当前配对还不完整，请先准备教师和学员素材。";
    return;
  }
  void router.push({ path: "/compare", query: { teacher: teacherId, user: userId, pipeline: pipelineId || undefined } });
}

function useRecentTaskPair() {
  routeToCompare(recentTask.value?.teacher_video_id, recentTask.value?.user_video_id, recentTask.value?.pipeline_id);
}

function useRecommendedPair() {
  routeToCompare(newestTeacher.value?.video_id, newestUser.value?.video_id);
}

function openLatestInCompare() {
  if (!result.value) return;
  openInCompare({
    video_id: result.value.video_id,
    role: result.value.role,
    filename: result.value.filename,
    url: result.value.url,
    uploaded_at: new Date().toISOString(),
    size_bytes: result.value.size_bytes,
  });
}

function openInCompare(item: VideoItem) {
  if (item.role === "teacher") {
    routeToCompare(item.video_id, newestUser.value?.video_id);
  } else {
    routeToCompare(newestTeacher.value?.video_id, item.video_id);
  }
}

function stripStem(filename: string, videoId: string) {
  const stem = String(filename || "").replace(/\.mp4$/i, "");
  const prefix = `${videoId}_`;
  return stem.startsWith(prefix) ? stem.slice(prefix.length) : stem;
}

function formatBytes(size: number) {
  if (!Number.isFinite(size) || size <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let value = size;
  let index = 0;
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024;
    index += 1;
  }
  return `${value.toFixed(value >= 100 || index === 0 ? 0 : 1)} ${units[index]}`;
}

function formatDate(value: string) {
  if (!value) return "--";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN", { hour12: false });
}

onMounted(() => {
  void loadAllContext();
});
</script>

<style scoped>
.upload-grid,
.library-grid {
  align-items: start;
}

.two-col-fields {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.file-input {
  width: 100%;
}

.summary-stack {
  display: grid;
  gap: 10px;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.06);
}

.summary-row:last-child {
  padding-bottom: 0;
  border-bottom: 0;
}

.asset-list-simple {
  gap: 10px;
}

.asset-item-simple {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  padding: 14px 0;
  border-bottom: 1px solid rgba(15, 23, 42, 0.06);
}

.asset-item-simple:last-child {
  border-bottom: 0;
}

.asset-main {
  display: grid;
  gap: 4px;
  min-width: 0;
  flex: 1;
}

.asset-main strong {
  word-break: break-all;
}

.asset-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.asset-input {
  width: 100%;
}

.danger-text {
  color: #b42318;
}

@media (max-width: 900px) {
  .two-col-fields {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .summary-row,
  .asset-item-simple {
    flex-direction: column;
    align-items: stretch;
  }

  .asset-actions {
    justify-content: flex-start;
  }
}
</style>
