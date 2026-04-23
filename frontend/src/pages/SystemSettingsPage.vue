<template>
  <main class="app-page settings-page settings-workbench">
    <section class="surface-card page-head settings-head">
      <div class="page-head-row">
        <div>
          <h1>系统设置</h1>
          <p class="page-subtitle">把运行状态、存储占用和维护动作收在一个巡检工作台里，方便长期本地使用时快速定位问题。</p>
        </div>
        <div class="action-row">
          <button class="secondary-button" :disabled="loading" @click="refreshStatus">
            {{ loading ? refreshLoadingLabel : refreshLabel }}
          </button>
        </div>
      </div>

      <div class="status-strip">
        <div class="status-cell" :data-tone="status?.ok ? 'ok' : 'warn'">
          <span class="status-caption">系统状态</span>
          <strong class="status-main">{{ status?.ok ? okLabel : attentionLabel }}</strong>
        </div>
        <div class="status-cell">
          <span class="status-caption">任务存储</span>
          <strong class="status-main">{{ status?.task_store || "--" }}</strong>
        </div>
        <div class="status-cell">
          <span class="status-caption">执行器</span>
          <strong class="status-main">{{ status?.pipeline_executor || "--" }}</strong>
        </div>
        <div class="status-cell emphasis">
          <span class="status-caption">输出组数</span>
          <strong class="status-main">{{ pairCountText }}</strong>
        </div>
      </div>
    </section>

    <section class="settings-overview-grid">
      <article class="surface-card health-hero" :data-tone="healthTone">
        <div class="panel-head compact-head">
          <div>
            <h2>运行概览</h2>
            <p class="helper-text">先看是否健康、下一个建议动作是什么，再决定是否要跳去记录页或执行维护。</p>
          </div>
        </div>

        <div v-if="error" class="feedback-inline">{{ error }}</div>
        <div v-else-if="loading && !status" class="feedback-state" data-tone="loading">
          <strong class="feedback-state-title">状态加载中</strong>
          <span class="feedback-state-copy">正在读取本地环境信息，请稍候。</span>
        </div>
        <template v-else>
          <div class="hero-main">
            <span class="hero-kicker">健康中心</span>
            <strong class="hero-title">{{ headlineTitle }}</strong>
            <p class="hero-copy">{{ headlineSummary }}</p>
          </div>

          <div class="hero-meta">
            <span>建议动作：{{ headlineAction }}</span>
            <span>最后检查：{{ checkedAtText }}</span>
          </div>

          <div class="hero-metrics">
            <div class="hero-metric" data-tone="danger">
              <span>紧急问题</span>
              <strong>{{ urgentCount }}</strong>
            </div>
            <div class="hero-metric" data-tone="warn">
              <span>需要关注</span>
              <strong>{{ warnCount }}</strong>
            </div>
            <div class="hero-metric" data-tone="ok">
              <span>正常项</span>
              <strong>{{ passCount }}</strong>
            </div>
          </div>
        </template>
      </article>

      <article class="surface-card settings-shortcuts-card">
        <div class="panel-head compact-head">
          <div>
            <h2>快捷入口</h2>
            <p class="helper-text">发现异常后，直接跳去最相关的工作区处理，不用来回切菜单。</p>
          </div>
        </div>

        <div class="shortcut-stack">
          <button class="shortcut-card" type="button" @click="goToRecords">
            <strong>打开分析记录</strong>
            <span>{{ tasksShortcutCopy }}</span>
          </button>
          <button class="shortcut-card" type="button" @click="goToRecordsCompleted">
            <strong>打开已完成记录</strong>
            <span>{{ reportsShortcutCopy }}</span>
          </button>
          <button class="shortcut-card" type="button" @click="goToCompare">
            <strong>回到开始分析</strong>
            <span>{{ compareShortcutCopy }}</span>
          </button>
        </div>
      </article>
    </section>

    <section class="settings-detail-grid">
      <article class="surface-card">
        <div class="panel-head compact-head">
          <div>
            <h2>环境检查</h2>
            <p class="helper-text">直接看关键依赖是否在线，包括运行目录、磁盘、模型、数据库和队列服务。</p>
          </div>
        </div>

        <div class="settings-card-grid">
          <div
            v-for="item in checkItems"
            :key="item.key"
            class="list-item-card settings-check-card"
            :data-tone="item.tone"
          >
            <div class="task-item-head">
              <strong>{{ item.label }}</strong>
              <span class="tag" :class="item.tone">{{ item.statusText }}</span>
            </div>
            <span class="helper-text">{{ item.detail }}</span>
          </div>
        </div>
      </article>

      <article class="surface-card">
        <div class="panel-head compact-head">
          <div>
            <h2>异常提示</h2>
            <p class="helper-text">把原始检查结果翻译成更直接的风险说明和处理建议。</p>
          </div>
        </div>

        <div v-if="!insightItems.length" class="feedback-state" data-tone="empty">
          <strong class="feedback-state-title">当前没有高优先级异常</strong>
          <span class="feedback-state-copy">主要服务和数据目录状态稳定，可以继续使用。</span>
        </div>
        <div v-else class="settings-card-grid">
          <div
            v-for="item in insightItems"
            :key="item.key"
            class="list-item-card settings-insight-card"
            :data-tone="item.tone"
          >
            <div class="task-item-head">
              <strong>{{ item.title }}</strong>
              <span class="tag" :class="item.tone">{{ item.level }}</span>
            </div>
            <span class="helper-text">{{ item.summary }}</span>
            <span class="helper-text settings-insight-action">{{ item.action }}</span>
          </div>
        </div>
      </article>
    </section>

    <section class="settings-detail-grid">
      <article class="surface-card">
        <div class="panel-head compact-head">
          <div>
            <h2>数据占用</h2>
            <p class="helper-text">重点关注上传目录、输出目录和关键点缓存，避免长期使用后体积失控。</p>
          </div>
        </div>

        <div class="settings-card-grid storage-card-grid">
          <div v-for="item in storageItems" :key="item.key" class="list-item-card settings-storage-card">
            <strong>{{ item.label }}</strong>
            <span class="settings-storage-value">{{ formatSize(item.bytes) }}</span>
            <span class="helper-text">{{ item.path }}</span>
          </div>
        </div>
      </article>

      <article class="surface-card">
        <div class="panel-head compact-head">
          <div>
            <h2>运行路径</h2>
            <p class="helper-text">这些目录决定了素材、输出和模型实际落在哪里，排查问题时最常用。</p>
          </div>
        </div>

        <div class="settings-path-list">
          <div v-for="item in pathItems" :key="item.key" class="summary-row">
            <span>{{ item.label }}</span>
            <strong class="settings-path-value">{{ item.value }}</strong>
          </div>
        </div>
      </article>
    </section>

    <section class="surface-card">
      <div class="panel-head compact-head">
        <div>
          <h2>数据维护</h2>
          <p class="helper-text">把最高频的维护动作保留在这里，适合定期瘦身、修复历史报告和清理调试产物。</p>
        </div>
      </div>

      <div class="settings-maintenance-grid">
        <div class="list-item-card settings-maintenance-card">
          <strong>重建历史报告</strong>
          <span class="helper-text">重新扫描已落盘的分析结果，修复报告表里的分数、可信度和摘要信息。</span>
          <div class="settings-maintenance-foot">
            <span class="field-help">{{ rebuildHint }}</span>
            <button :disabled="actionLoading" @click="runRebuildReports">
              {{ actionLoading ? actionLoadingLabel : rebuildLabel }}
            </button>
          </div>
        </div>

        <div class="list-item-card settings-maintenance-card">
          <strong>裁剪旧输出</strong>
          <span class="helper-text">只保留最近若干组分析输出，用来控制 <code>outputs</code> 目录的长期增长。</span>
          <div class="settings-inline-field">
            <label class="field-label">保留组数</label>
            <input v-model.number="keepPairs" type="number" min="1" max="50" step="1" />
          </div>
          <div class="settings-maintenance-foot">
            <span class="field-help">{{ trimHint }}</span>
            <button :disabled="actionLoading" @click="runTrimOutputs">
              {{ actionLoading ? actionLoadingLabel : trimLabel }}
            </button>
          </div>
        </div>

        <div class="list-item-card settings-maintenance-card">
          <strong>清理调试产物</strong>
          <span class="helper-text">删除调试目录和辅助图表，保留报告、时间轴和骨架视频等主要结果。</span>
          <div class="settings-maintenance-foot">
            <span class="field-help">{{ cleanupHint }}</span>
            <button :disabled="actionLoading" @click="runCleanupDebug">
              {{ actionLoading ? actionLoadingLabel : cleanupLabel }}
            </button>
          </div>
        </div>
      </div>

      <div
        v-if="actionResult"
        class="feedback-state maintenance-result"
        :data-tone="actionResult.ok ? 'loading' : 'error'"
      >
        <strong class="feedback-state-title">{{ actionResult.ok ? actionDoneTitle : actionFailTitle }}</strong>
        <span class="feedback-state-copy">{{ actionResult.message }}</span>
        <span v-if="actionResult.affected_count != null" class="helper-text">
          {{ affectedCountLabel }}{{ actionResult.affected_count }}
        </span>
        <span v-if="actionResult.freed_bytes != null" class="helper-text">
          {{ freedSpaceLabel }}{{ formatSize(actionResult.freed_bytes || 0) }}
        </span>
        <span v-if="actionResult.report_count != null" class="helper-text">
          {{ reportCountLabel }}{{ actionResult.report_count }}
        </span>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import {
  cleanupDebugArtifacts,
  getSystemStatus,
  rebuildAnalysisReports,
  trimOutputPairs,
} from "../api/pipelines";
import type { SystemActionResponse, SystemStatusResponse } from "../types/video";

type CheckItem = {
  key: string;
  label: string;
  statusText: string;
  tone: string;
  detail: string;
};

type InsightItem = {
  key: string;
  title: string;
  level: string;
  tone: string;
  summary: string;
  action: string;
};

type StorageItem = {
  key: string;
  label: string;
  path: string;
  bytes: number;
};

const router = useRouter();

const okLabel = "健康";
const attentionLabel = "需关注";
const refreshLabel = "刷新状态";
const refreshLoadingLabel = "刷新中...";
const actionLoadingLabel = "执行中...";
const rebuildLabel = "重建报告";
const trimLabel = "裁剪输出";
const cleanupLabel = "清理调试产物";
const actionDoneTitle = "维护动作已完成";
const actionFailTitle = "维护动作执行失败";
const affectedCountLabel = "影响项数：";
const freedSpaceLabel = "释放空间：";
const reportCountLabel = "报告记录数：";
const loadErrorText = "系统状态加载失败";
const maintenanceErrorText = "维护动作执行失败";
const rebuildHint = "适合在补入新字段或修复旧报告后执行。";
const trimHint = "建议先保留 5 到 10 组，在可回看性和空间占用之间做平衡。";
const cleanupHint = "适合在长时间调试后执行，不会碰主要输出文件。";
const checkedAtFallback = "尚未记录";

const status = ref<SystemStatusResponse | null>(null);
const loading = ref(false);
const error = ref("");
const actionLoading = ref(false);
const actionResult = ref<SystemActionResponse | null>(null);
const keepPairs = ref(5);

const pairCountText = computed(() => {
  const value = status.value?.output_pair_count;
  if (value == null) return "--";
  return `${value} 组`;
});

const checkItems = computed<CheckItem[]>(() => {
  const checks = status.value?.checks || {};
  const items: CheckItem[] = [
    makeCheckItem("app_home", "运行目录", checks.app_home),
    makeCheckItem("disk", "磁盘空间", checks.disk),
    makeCheckItem("model_file", "模型文件", checks.model_file),
    makeCheckItem("postgresql", "PostgreSQL", checks.postgresql),
    makeCheckItem("redis", "Redis", checks.redis),
  ];

  if (checks.redis?.required !== undefined) {
    items.push({
      key: "redis_worker",
      label: "Worker 心跳",
      statusText: checks.redis?.required
        ? checks.redis?.worker_alive === false
          ? "异常"
          : "正常"
        : "未启用",
      tone: checks.redis?.required ? (checks.redis?.worker_alive === false ? "danger" : "ok") : "neutral",
      detail: checks.redis?.required
        ? checks.redis?.worker_alive === false
          ? "当前执行器需要 Redis Worker 在线，但最近没有收到有效心跳。"
          : "Redis Worker 心跳正常。"
        : "当前执行器不依赖 Redis Worker。",
    });
  }

  return items;
});

const insightItems = computed<InsightItem[]>(() => {
  const checks = status.value?.checks || {};
  const storage = status.value?.storage || {};
  const items: InsightItem[] = [];

  if (checks.redis?.status === "fail") {
    items.push({
      key: "redis",
      title: "Redis 连接失败",
      level: "高优先级",
      tone: "danger",
      summary: checks.redis?.detail || "Redis 不可用时，队列执行和任务调度会受到影响。",
      action: "先恢复 Redis，再继续提交新的分析任务。",
    });
  }

  if (checks.postgresql?.status === "fail") {
    items.push({
      key: "postgresql",
      title: "PostgreSQL 异常",
      level: "高优先级",
      tone: "danger",
      summary: checks.postgresql?.detail || "任务和报告的持久化会受影响。",
      action: "先启动或修复 PostgreSQL，再回到分析记录页确认历史记录是否正常。",
    });
  }

  if (checks.model_file?.status === "fail") {
    items.push({
      key: "model_file",
      title: "模型文件缺失",
      level: "高优先级",
      tone: "danger",
      summary: checks.model_file?.detail || "姿态提取所需模型文件不完整，新的分析任务无法正常执行。",
      action: "检查 models 目录和相关配置，确认模型文件已经就位。",
    });
  }

  if (checks.disk?.status === "fail") {
    const freeGb = checks.disk?.free_gb ?? "--";
    const minGb = checks.disk?.min_free_gb ?? "--";
    items.push({
      key: "disk",
      title: "可用磁盘空间不足",
      level: "高优先级",
      tone: "danger",
      summary: `当前可用空间约 ${freeGb} GB，低于阈值 ${minGb} GB。`,
      action: "优先执行“裁剪旧输出”或“清理调试产物”，再继续处理大批量任务。",
    });
  }

  const outputBytes = Number(storage.outputs?.bytes || 0);
  if (outputBytes >= 2 * 1024 ** 3) {
    items.push({
      key: "outputs_size",
      title: "分析输出体积偏大",
      level: "中优先级",
      tone: "warn",
      summary: `outputs 目录当前约为 ${formatSize(outputBytes)}，长期累积会影响桌面端管理体验。`,
      action: "适当降低保留组数，定期裁剪旧输出。",
    });
  }

  const redisPendingJobs = Number(checks.redis?.pending_jobs || 0);
  const redisDeadLetterJobs = Number(checks.redis?.dead_letter_jobs || 0);

  if (redisDeadLetterJobs > 0) {
    items.push({
      key: "redis_dead_letter",
      title: "存在死信任务",
      level: redisDeadLetterJobs >= 3 ? "高优先级" : "中优先级",
      tone: redisDeadLetterJobs >= 3 ? "danger" : "warn",
      summary: `当前死信队列中有 ${redisDeadLetterJobs} 条任务，说明有部分分析任务已经重试耗尽。`,
      action: "先去分析记录里查看失败任务，再结合日志定位素材或算法执行问题。",
    });
  }

  if (checks.redis?.required && checks.redis?.worker_alive === false) {
    items.push({
      key: "redis_worker_stale",
      title: "Redis Worker 心跳丢失",
      level: "高优先级",
      tone: "danger",
      summary: checks.redis?.detail || "当前执行模式需要 Redis Worker 在线，但最近没有收到有效心跳。",
      action: "先重启 Worker，再回来确认状态恢复正常。",
    });
  }

  if (redisPendingJobs >= 5 && redisDeadLetterJobs === 0) {
    items.push({
      key: "redis_backlog",
      title: "任务队列出现积压",
      level: "中优先级",
      tone: "warn",
      summary: `当前待处理任务约 ${redisPendingJobs} 条，说明分析请求正在排队。`,
      action: "确认 Worker 是否正常工作，必要时错峰提交大批量任务。",
    });
  }

  if (status.value && !status.value.ok && !items.length) {
    items.push({
      key: "generic",
      title: "存在待处理项",
      level: "中优先级",
      tone: "warn",
      summary: "系统未完全通过健康检查，但基础能力仍然可用。",
      action: "先逐项检查上方结果，优先处理最影响运行稳定性的异常。",
    });
  }

  return items;
});

const urgentCount = computed(() => insightItems.value.filter((item) => item.tone === "danger").length);
const warnCount = computed(() => insightItems.value.filter((item) => item.tone === "warn").length);
const passCount = computed(() => checkItems.value.filter((item) => item.tone === "ok").length);
const healthTone = computed(() => {
  if (urgentCount.value > 0) return "danger";
  if (warnCount.value > 0 || !status.value?.ok) return "warn";
  return "ok";
});

const headlineTitle = computed(() => {
  if (healthTone.value === "ok") return "当前环境整体可用";
  if (healthTone.value === "danger") return "当前环境存在高风险项";
  return "当前环境需要关注";
});

const headlineSummary = computed(() => {
  if (healthTone.value === "ok") {
    return "主要服务和数据目录状态稳定，可以继续进行分析和历史结果管理。";
  }
  if (healthTone.value === "danger") {
    return "检测到会影响执行或持久化的关键问题，建议先处理再继续长时间使用。";
  }
  return "系统还能继续工作，但最好先把风险项清掉，避免后续任务堆积。";
});

const headlineAction = computed(() => insightItems.value[0]?.action || "保持当前配置，并定期裁剪旧输出。");

const checkedAtText = computed(() => {
  const value = status.value?.checked_at;
  if (!value) return checkedAtFallback;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return checkedAtFallback;
  return parsed.toLocaleString("zh-CN", { hour12: false });
});

const tasksShortcutCopy = computed(() =>
  urgentCount.value > 0 ? "优先查看失败或卡住的记录，确认问题是否已经影响任务执行。" : "集中查看全部记录、失败任务和异常输出。"
);

const reportsShortcutCopy = computed(() =>
  warnCount.value > 0 ? "重点复核最新完成记录，确认报告摘要和产物是否正常生成。" : "快速回看最近完成的分析结果和报告质量。"
);

const compareShortcutCopy = computed(() =>
  healthTone.value === "ok" ? "环境状态稳定，可以继续发起新的动作分析。" : "处理完关键异常后，再继续提交新的分析任务更稳妥。"
);

const storageItems = computed<StorageItem[]>(() => {
  const storage = status.value?.storage || {};
  return [
    makeStorageItem("uploads", "上传目录", storage.uploads),
    makeStorageItem("outputs", "分析输出", storage.outputs),
    makeStorageItem("cache_keypoints", "关键点缓存", storage.cache_keypoints),
    makeStorageItem("models", "模型目录", storage.models),
    makeStorageItem("app_home", "运行根目录", storage.app_home),
  ];
});

const pathItems = computed(() => {
  const paths = status.value?.paths || {};
  return [
    { key: "app_home", label: "运行根目录", value: paths.app_home || "--" },
    { key: "uploads", label: "上传目录", value: paths.uploads || "--" },
    { key: "outputs", label: "输出目录", value: paths.outputs || "--" },
    { key: "data", label: "数据目录", value: paths.data || "--" },
    { key: "models", label: "模型目录", value: paths.models || "--" },
  ];
});

function makeCheckItem(key: string, label: string, value: any): CheckItem {
  const rawStatus = String(value?.status || "disabled");
  const statusTextMap: Record<string, string> = {
    pass: "正常",
    fail: "异常",
    disabled: "未启用",
  };
  const toneMap: Record<string, string> = {
    pass: "ok",
    fail: "danger",
    disabled: "neutral",
  };
  return {
    key,
    label,
    statusText: statusTextMap[rawStatus] || rawStatus,
    tone: toneMap[rawStatus] || "neutral",
    detail: value?.detail || value?.path || "--",
  };
}

function makeStorageItem(key: string, label: string, value: any): StorageItem {
  return {
    key,
    label,
    path: value?.path || "--",
    bytes: Number(value?.bytes || 0),
  };
}

function formatSize(bytes: number) {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 MB";
  const gb = bytes / 1024 ** 3;
  if (gb >= 1) return `${gb.toFixed(2)} GB`;
  const mb = bytes / 1024 ** 2;
  return `${mb.toFixed(1)} MB`;
}

function goToRecords() {
  void router.push("/records");
}

function goToRecordsCompleted() {
  void router.push({ path: "/records", query: { tab: "completed" } });
}

function goToCompare() {
  void router.push("/compare");
}

async function loadStatus() {
  loading.value = true;
  error.value = "";
  try {
    status.value = await getSystemStatus();
    if ((status.value?.retain_output_pairs || 0) > 0) {
      keepPairs.value = Number(status.value?.retain_output_pairs || 5);
    }
  } catch (err: any) {
    error.value = err?.response?.data?.detail ?? err?.message ?? loadErrorText;
  } finally {
    loading.value = false;
  }
}

async function refreshStatus() {
  await loadStatus();
}

async function runRebuildReports() {
  await runMaintenance(() => rebuildAnalysisReports());
}

async function runTrimOutputs() {
  const keep = Math.max(1, Number(keepPairs.value) || 5);
  await runMaintenance(() => trimOutputPairs(keep));
}

async function runCleanupDebug() {
  await runMaintenance(() => cleanupDebugArtifacts());
}

async function runMaintenance(action: () => Promise<SystemActionResponse>) {
  actionLoading.value = true;
  actionResult.value = null;
  try {
    actionResult.value = await action();
    await loadStatus();
  } catch (err: any) {
    actionResult.value = {
      ok: false,
      action: "maintenance",
      message: err?.response?.data?.detail ?? err?.message ?? maintenanceErrorText,
      report_count: null,
      affected_count: null,
      freed_bytes: null,
    };
  } finally {
    actionLoading.value = false;
  }
}

onMounted(() => {
  void loadStatus();
});
</script>

<style scoped>
.settings-workbench,
.settings-overview-grid,
.settings-detail-grid {
  display: grid;
  gap: 16px;
}

.settings-overview-grid {
  grid-template-columns: minmax(0, 1.1fr) minmax(320px, 0.9fr);
}

.settings-detail-grid {
  grid-template-columns: minmax(0, 1.05fr) minmax(320px, 0.95fr);
}

.health-hero,
.shortcut-card,
.settings-check-card,
.settings-insight-card,
.settings-maintenance-card {
  position: relative;
  overflow: hidden;
}

.health-hero {
  display: grid;
  gap: 16px;
  border: 1px solid var(--line);
}

.health-hero::before,
.settings-check-card::before,
.settings-insight-card::before {
  content: "";
  position: absolute;
  inset: 0 auto 0 0;
  width: 4px;
  background: rgba(15, 23, 42, 0.1);
}

.health-hero[data-tone="ok"]::before,
.settings-check-card[data-tone="ok"]::before,
.settings-insight-card[data-tone="ok"]::before {
  background: rgba(31, 143, 95, 0.88);
}

.health-hero[data-tone="warn"]::before,
.settings-check-card[data-tone="warn"]::before,
.settings-insight-card[data-tone="warn"]::before {
  background: rgba(182, 122, 16, 0.9);
}

.health-hero[data-tone="danger"]::before,
.settings-check-card[data-tone="danger"]::before,
.settings-insight-card[data-tone="danger"]::before {
  background: rgba(216, 76, 76, 0.9);
}

.hero-main {
  display: grid;
  gap: 8px;
}

.hero-kicker {
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
}

.hero-title {
  font-size: 1.24rem;
  line-height: 1.35;
}

.hero-copy,
.hero-meta {
  margin: 0;
  color: var(--muted);
}

.hero-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 18px;
  font-size: 0.92rem;
}

.hero-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.hero-metric {
  display: grid;
  gap: 6px;
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.86);
}

.hero-metric span {
  color: var(--muted);
  font-size: 0.84rem;
}

.hero-metric strong {
  font-size: 1.4rem;
  line-height: 1;
}

.shortcut-stack {
  display: grid;
  gap: 12px;
}

.shortcut-card {
  display: grid;
  gap: 8px;
  padding: 16px 18px;
  border-radius: 18px;
  border: 1px solid var(--line);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(247, 249, 252, 0.94) 100%);
  color: var(--text);
  text-align: left;
  box-shadow: none;
}

.shortcut-card:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.shortcut-card span {
  color: var(--muted);
  line-height: 1.6;
  font-weight: 500;
}

.settings-card-grid,
.settings-maintenance-grid {
  display: grid;
  gap: 12px;
}

.storage-card-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.settings-maintenance-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.settings-check-card,
.settings-insight-card {
  gap: 8px;
  border: 1px solid var(--line);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(247, 249, 252, 0.94) 100%);
}

.settings-storage-card {
  gap: 6px;
}

.settings-storage-value {
  font-size: 1.12rem;
  font-weight: 700;
}

.settings-path-list {
  display: grid;
  gap: 12px;
}

.settings-path-value {
  max-width: 70%;
  text-align: right;
  word-break: break-all;
}

.settings-check-card .helper-text,
.settings-storage-card .helper-text,
.settings-insight-card .helper-text,
.settings-maintenance-card .helper-text {
  line-height: 1.6;
  word-break: break-all;
}

.settings-inline-field {
  display: grid;
  gap: 8px;
  max-width: 180px;
  margin-top: 12px;
}

.settings-maintenance-card {
  display: grid;
  gap: 10px;
}

.settings-maintenance-foot {
  display: grid;
  gap: 10px;
  margin-top: auto;
}

.settings-insight-action {
  color: var(--text);
  font-weight: 600;
}

.maintenance-result {
  margin-top: 16px;
}

@media (max-width: 1180px) {
  .settings-overview-grid,
  .settings-detail-grid,
  .settings-maintenance-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .hero-metrics,
  .storage-card-grid {
    grid-template-columns: 1fr;
  }
}
</style>
