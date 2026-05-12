<template>
  <main class="app-page upload-page upload-workbench">
    <section class="surface-card page-head upload-head">
      <div class="page-head-row">
        <div>
          <h1>素材库 <InfoHint text="上传教师示范和学员练习，整理后可直接带入动作分析。" /></h1>
          <p class="page-subtitle">管理素材，准备分析组合。</p>
        </div>
        <div class="action-row">
          <button class="secondary-button" :disabled="listing" @click="loadAllContext">
            {{ listing ? syncLoadingText : syncActionText }}
          </button>
          <RouterLink class="link-button" to="/compare">开始分析</RouterLink>
        </div>
      </div>

      <div class="status-strip">
        <div class="status-cell">
          <span class="status-caption">素材总数</span>
          <strong class="status-main">{{ items.length }}</strong>
        </div>
        <div class="status-cell">
          <span class="status-caption">教师素材</span>
          <strong class="status-main">{{ teacherItems.length }}</strong>
        </div>
        <div class="status-cell">
          <span class="status-caption">学员素材</span>
          <strong class="status-main">{{ userItems.length }}</strong>
        </div>
        <div class="status-cell emphasis">
          <span class="status-caption">当前建议</span>
          <strong class="status-main">{{ inventoryHint }}</strong>
        </div>
      </div>
    </section>

    <section class="upload-workspace">
      <article class="surface-card upload-composer">
        <div class="panel-head compact-head">
          <div>
            <h2>新增素材 <InfoHint text="填写角色、名称并选择视频文件；上传后会进入素材库和推荐配对。" /></h2>
            <p class="helper-text">选择角色、名称和视频。</p>
          </div>
        </div>

        <div class="field-grid upload-fields">
          <div class="field-block">
            <label class="field-label">角色</label>
            <select v-model="role">
              <option value="teacher">教师示范</option>
              <option value="user">学员练习</option>
            </select>
          </div>
          <div class="field-block">
            <label class="field-label">素材名称</label>
            <input v-model.trim="name" type="text" :placeholder="namePlaceholder" />
          </div>
        </div>

        <div class="field-block">
          <label class="field-label">视频文件</label>
          <input
            :key="fileInputKey"
            class="file-input"
            type="file"
            accept=".mp4,.mov,.avi,.mkv,.m4v"
            @change="onFileChange"
          />
        </div>

        <div class="draft-banner">
          <strong>本次草稿</strong>
          <span>{{ draftState }}</span>
        </div>

        <div class="action-row">
          <button :disabled="uploading || !file" @click="submitUpload">
            {{ uploading ? uploadLoadingText : uploadActionText }}
          </button>
          <button class="secondary-button" :disabled="uploading" @click="resetDraft">
            {{ resetActionText }}
          </button>
        </div>

        <div v-if="error" class="feedback-inline">{{ error }}</div>
        <div v-else-if="actionMessage" class="feedback-state" data-tone="loading">
          <strong class="feedback-state-title">{{ actionDoneTitle }}</strong>
          <span class="feedback-state-copy">{{ actionMessage }}</span>
        </div>
      </article>

      <article class="surface-card upload-brief">
        <div class="panel-head compact-head">
          <div>
            <h2>快速带入分析 <InfoHint text="可以复用最近配对、使用推荐配对，或把本次上传直接带到分析页。" /></h2>
            <p class="helper-text">选择一组素材进入分析。</p>
          </div>
        </div>

        <div class="brief-grid">
          <div class="brief-card">
            <span>本次上传</span>
            <strong>{{ result?.filename || emptyText }}</strong>
          </div>
          <div class="brief-card">
            <span>最近配对</span>
            <strong>{{ recentTask?.pair_name || emptyText }}</strong>
          </div>
          <div class="brief-card">
            <span>推荐教师</span>
            <strong>{{ newestTeacher?.filename || emptyTeacherText }}</strong>
          </div>
          <div class="brief-card">
            <span>推荐学员</span>
            <strong>{{ newestUser?.filename || emptyUserText }}</strong>
          </div>
        </div>

        <div class="quick-action-stack">
          <button class="secondary-button" :disabled="!canUseRecentTask" @click="useRecentTaskPair">
            使用最近配对
          </button>
          <button class="secondary-button" :disabled="!canUseRecommendedPair" @click="useRecommendedPair">
            使用推荐配对
          </button>
          <button class="secondary-button" :disabled="!result" @click="openLatestInCompare">
            用本次上传继续
          </button>
        </div>
      </article>
    </section>

    <section class="surface-card library-workspace">
      <div class="panel-head compact-head library-head">
        <div>
          <h2>素材工作区 <InfoHint text="素材按教师和学员分组，可打开预览、重命名、删除或直接用于分析。" /></h2>
          <p class="helper-text">整理素材，保持可用。</p>
        </div>
        <div class="library-summary">
          <span>教师 {{ teacherItems.length }}</span>
          <span>学员 {{ userItems.length }}</span>
        </div>
      </div>

      <div class="library-columns">
        <article class="library-panel">
          <div class="library-panel-head">
            <strong>教师素材</strong>
            <span class="helper-text">用于左侧示范对照。</span>
          </div>

          <EmptyState
            v-if="!teacherItems.length"
            title="教师素材为空"
            copy="上传教师视频后可作为左侧标准输入。"
          >
            <template #actions>
              <button class="secondary-button" type="button" @click="role = 'teacher'">上传教师视频</button>
            </template>
          </EmptyState>

          <ul v-else class="list-clean asset-list-dense">
            <li v-for="item in teacherItems" :key="item.video_id" class="asset-row">
              <div class="asset-row-main">
                <template v-if="editingVideoId === item.video_id">
                  <input
                    v-model.trim="editingName"
                    type="text"
                    class="asset-input"
                    :placeholder="renamePlaceholder"
                  />
                </template>
                <template v-else>
                  <strong>{{ item.filename }}</strong>
                </template>
                <span class="helper-text">{{ formatDate(item.uploaded_at) }} · {{ formatBytes(item.size_bytes) }}</span>
              </div>

              <div class="asset-row-actions">
                <button class="secondary-button" @click="openInCompare(item)">{{ useInCompareText }}</button>
                <a class="link-button secondary-button" :href="absMediaUrl(item.url)" target="_blank">{{ openText }}</a>
                <button
                  v-if="editingVideoId !== item.video_id"
                  class="secondary-button"
                  :disabled="busyVideoId === item.video_id"
                  @click="startRename(item)"
                >
                  {{ renameText }}
                </button>
                <button
                  v-else
                  class="secondary-button"
                  :disabled="busyVideoId === item.video_id || !editingName"
                  @click="saveRename(item)"
                >
                  {{ saveText }}
                </button>
                <button
                  v-if="editingVideoId === item.video_id"
                  class="ghost-button"
                  :disabled="busyVideoId === item.video_id"
                  @click="cancelRename"
                >
                  {{ cancelText }}
                </button>
                <button
                  class="ghost-button danger-text"
                  :disabled="busyVideoId === item.video_id"
                  @click="removeItem(item)"
                >
                  {{ deleteText }}
                </button>
              </div>
            </li>
          </ul>
        </article>

        <article class="library-panel">
          <div class="library-panel-head">
            <strong>学员素材</strong>
            <span class="helper-text">用于右侧练习对照。</span>
          </div>

          <EmptyState
            v-if="!userItems.length"
            title="学员素材为空"
            copy="上传学员视频后可与教师视频配对。"
          >
            <template #actions>
              <button class="secondary-button" type="button" @click="role = 'user'">上传学员视频</button>
            </template>
          </EmptyState>

          <ul v-else class="list-clean asset-list-dense">
            <li v-for="item in userItems" :key="item.video_id" class="asset-row">
              <div class="asset-row-main">
                <template v-if="editingVideoId === item.video_id">
                  <input
                    v-model.trim="editingName"
                    type="text"
                    class="asset-input"
                    :placeholder="renamePlaceholder"
                  />
                </template>
                <template v-else>
                  <strong>{{ item.filename }}</strong>
                </template>
                <span class="helper-text">{{ formatDate(item.uploaded_at) }} · {{ formatBytes(item.size_bytes) }}</span>
              </div>

              <div class="asset-row-actions">
                <button class="secondary-button" @click="openInCompare(item)">{{ useInCompareText }}</button>
                <a class="link-button secondary-button" :href="absMediaUrl(item.url)" target="_blank">{{ openText }}</a>
                <button
                  v-if="editingVideoId !== item.video_id"
                  class="secondary-button"
                  :disabled="busyVideoId === item.video_id"
                  @click="startRename(item)"
                >
                  {{ renameText }}
                </button>
                <button
                  v-else
                  class="secondary-button"
                  :disabled="busyVideoId === item.video_id || !editingName"
                  @click="saveRename(item)"
                >
                  {{ saveText }}
                </button>
                <button
                  v-if="editingVideoId === item.video_id"
                  class="ghost-button"
                  :disabled="busyVideoId === item.video_id"
                  @click="cancelRename"
                >
                  {{ cancelText }}
                </button>
                <button
                  class="ghost-button danger-text"
                  :disabled="busyVideoId === item.video_id"
                  @click="removeItem(item)"
                >
                  {{ deleteText }}
                </button>
              </div>
            </li>
          </ul>
        </article>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";
import { absMediaUrl } from "../api/http";
import EmptyState from "../components/EmptyState.vue";
import InfoHint from "../components/InfoHint.vue";
import { listPipelineTasks } from "../api/pipelines";
import { deleteVideo, listVideos, renameVideo, uploadVideo } from "../api/videos";
import { friendlyError } from "../utils/errors";
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
  if (!teacherItems.value.length) return "缺教师 · 去上传";
  if (!userItems.value.length) return "缺学员 · 去上传";
  return "素材就绪 · 可分析";
});
const draftState = computed(() => {
  if (!file.value) return "未选择视频文件。";
  return `已选择 ${file.value.name}，将作为${roleText(role.value)}入库。`;
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
    error.value = friendlyError(err, "素材重命名失败");
    busyVideoId.value = "";
  }
}

async function removeItem(item: VideoItem) {
  if (!window.confirm(`确定删除素材“${item.filename}”吗？`)) return;
  busyVideoId.value = item.video_id;
  error.value = "";
  actionMessage.value = "";
  try {
    const response = await deleteVideo({ videoId: item.video_id, role: item.role });
    if (result.value?.video_id === item.video_id) result.value = null;
    if (editingVideoId.value === item.video_id) clearEditing();
    actionMessage.value = response.message;
    await loadAllContext();
  } catch (err: any) {
    error.value = friendlyError(err, "素材删除失败");
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
    actionMessage.value = "上传完成，素材库已更新。";
    await loadAllContext();
  } catch (err: any) {
    error.value = friendlyError(err, "上传失败");
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
    error.value = friendlyError(err, "素材库加载失败");
  } finally {
    listing.value = false;
  }
}

function routeToCompare(teacherId?: string | null, userId?: string | null, pipelineId?: string | null) {
  if (!teacherId || !userId) {
    error.value = "配对不完整，请补齐教师和学员素材。";
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
.upload-workbench,
.upload-workspace,
.library-workspace,
.library-columns {
  display: grid;
  gap: 16px;
}

.upload-workspace {
  grid-template-columns: minmax(0, 1.1fr) minmax(320px, 0.9fr);
}

.upload-fields {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.file-input {
  width: 100%;
}

.draft-banner {
  display: grid;
  gap: 6px;
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(247, 249, 252, 0.88);
}

.brief-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.brief-card {
  display: grid;
  gap: 6px;
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.82);
}

.brief-card span {
  color: var(--muted);
  font-size: 0.84rem;
}

.quick-action-stack {
  display: grid;
  gap: 10px;
}

.library-head {
  align-items: center;
}

.library-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  color: var(--muted);
  font-size: 0.92rem;
  font-weight: 700;
}

.library-columns {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.library-panel {
  display: grid;
  gap: 12px;
}

.library-panel-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
}

.asset-list-dense {
  gap: 10px;
}

.asset-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 14px;
  padding: 14px 0;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
}

.asset-row:last-child {
  border-bottom: 0;
}

.asset-row-main {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.asset-row-main strong {
  word-break: break-all;
}

.asset-row-actions {
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

@media (max-width: 1120px) {
  .upload-workspace,
  .library-columns {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .upload-fields,
  .brief-grid,
  .asset-row {
    grid-template-columns: 1fr;
  }

  .asset-row-actions {
    justify-content: flex-start;
  }

  .library-panel-head {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
