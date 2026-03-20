<template>
  <main class="app-page settings-page">
    <section class="surface-card page-head">
      <div class="page-head-row">
        <div>
          <h1>&#31995;&#32479;&#35774;&#32622;</h1>
          <p class="page-subtitle">
            &#25226;&#26412;&#22320;&#29615;&#22659;&#29366;&#24577;&#12289;&#31354;&#38388;&#21344;&#29992;&#21644;&#32500;&#25252;&#21160;&#20316;&#25910;&#36827;&#19968;&#20010;&#29420;&#31435;&#39029;&#38754;&#65292;
            &#26041;&#20415;&#26700;&#38754;&#31471;&#38271;&#26399;&#20351;&#29992;&#26102;&#36827;&#34892;&#25490;&#26597;&#21644;&#36731;&#37327;&#21270;&#31649;&#29702;&#12290;
          </p>
        </div>
        <div class="action-row">
          <button class="secondary-button" :disabled="loading" @click="refreshStatus">
            {{ loading ? refreshLoadingLabel : refreshLabel }}
          </button>
        </div>
      </div>

      <div class="status-strip">
        <div class="status-cell" :data-tone="status?.ok ? 'ok' : 'warn'">
          <span class="status-caption">&#31995;&#32479;&#29366;&#24577;</span>
          <strong class="status-main">{{ status?.ok ? okLabel : attentionLabel }}</strong>
        </div>
        <div class="status-cell">
          <span class="status-caption">&#20219;&#21153;&#23384;&#20648;</span>
          <strong class="status-main">{{ status?.task_store || '--' }}</strong>
        </div>
        <div class="status-cell">
          <span class="status-caption">&#25191;&#34892;&#22120;</span>
          <strong class="status-main">{{ status?.pipeline_executor || '--' }}</strong>
        </div>
        <div class="status-cell emphasis">
          <span class="status-caption">&#36755;&#20986;&#32452;&#25968;</span>
          <strong class="status-main">{{ pairCountText }}</strong>
        </div>
      </div>

      <div class="settings-overview">
        <div class="overview-hero" :data-tone="healthTone">
          <span class="overview-kicker">{{ headlineLabel }}</span>
          <strong class="overview-title">{{ headlineTitle }}</strong>
          <p class="overview-copy">{{ headlineSummary }}</p>
          <div class="overview-meta">
            <span>{{ nextActionLabel }}{{ headlineAction }}</span>
            <span>{{ checkedAtLabel }}{{ checkedAtText }}</span>
          </div>
        </div>

        <div class="overview-metrics">
          <div class="overview-metric" data-tone="danger">
            <span class="overview-metric-label">{{ urgentLabel }}</span>
            <strong class="overview-metric-value">{{ urgentCount }}</strong>
          </div>
          <div class="overview-metric" data-tone="warn">
            <span class="overview-metric-label">{{ attentionIssuesLabel }}</span>
            <strong class="overview-metric-value">{{ warnCount }}</strong>
          </div>
          <div class="overview-metric" data-tone="ok">
            <span class="overview-metric-label">{{ healthyItemsLabel }}</span>
            <strong class="overview-metric-value">{{ passCount }}</strong>
          </div>
        </div>
      </div>

      <div class="settings-shortcuts">
        <div class="settings-shortcuts-head">
          <strong>&#24555;&#25463;&#20837;&#21475;</strong>
          <span class="helper-text">&#30475;&#21040;&#24322;&#24120;&#21518;&#30452;&#25509;&#36339;&#21435;&#23545;&#24212;&#39029;&#38754;&#22788;&#29702;&#65292;&#20943;&#23569;&#26469;&#22238;&#20999;&#25442;&#12290;</span>
        </div>
        <div class="settings-shortcut-grid">
          <button class="shortcut-card" type="button" @click="goToTasks">
            <strong>&#25171;&#24320;&#20219;&#21153;&#20013;&#24515;</strong>
            <span>{{ tasksShortcutCopy }}</span>
          </button>
          <button class="shortcut-card" type="button" @click="goToReports">
            <strong>&#25171;&#24320;&#25253;&#21578;&#20013;&#24515;</strong>
            <span>{{ reportsShortcutCopy }}</span>
          </button>
          <button class="shortcut-card" type="button" @click="goToCompare">
            <strong>&#22238;&#21040;&#21160;&#20316;&#20998;&#26512;</strong>
            <span>{{ compareShortcutCopy }}</span>
          </button>
        </div>
      </div>
    </section>

    <section class="settings-layout">
      <article class="surface-card">
        <div class="panel-head compact-head">
          <div>
            <h2>&#29615;&#22659;&#26816;&#26597;</h2>
            <p class="helper-text">
              &#30452;&#25509;&#35835;&#21462;&#21518;&#31471;&#26816;&#26597;&#32467;&#26524;&#65292;&#24555;&#36895;&#30830;&#35748; PostgreSQL&#12289;Redis&#12289;
              &#27169;&#22411;&#25991;&#20214;&#21644;&#30913;&#30424;&#29366;&#24577;&#12290;
            </p>
          </div>
        </div>

        <div v-if="error" class="feedback-inline">{{ error }}</div>
        <div v-else-if="loading && !status" class="feedback-state" data-tone="loading">
          <strong class="feedback-state-title">&#29366;&#24577;&#21152;&#36733;&#20013;</strong>
          <span class="feedback-state-copy">&#27491;&#22312;&#21516;&#27493;&#26412;&#22320;&#29615;&#22659;&#20449;&#24687;&#65292;&#35831;&#31245;&#20505;&#12290;</span>
        </div>
        <div v-else class="settings-card-grid">
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
            <h2>&#24322;&#24120;&#25552;&#31034;</h2>
            <p class="helper-text">
              &#25226;&#21407;&#22987;&#26816;&#26597;&#32467;&#26524;&#32763;&#35793;&#25104;&#21487;&#30452;&#25509;&#22788;&#29702;&#30340;&#32467;&#35770;&#21644;&#24314;&#35758;&#65292;
              &#20943;&#23569;&#33258;&#24049;&#23545;&#30528;&#23383;&#27573;&#36880;&#26465;&#21028;&#26029;&#30340;&#25104;&#26412;&#12290;
            </p>
          </div>
        </div>

        <div v-if="!insightItems.length" class="feedback-state" data-tone="empty">
          <strong class="feedback-state-title">&#26242;&#26102;&#27809;&#26377;&#39640;&#20248;&#20808;&#32423;&#24322;&#24120;</strong>
          <span class="feedback-state-copy">&#24403;&#21069;&#29615;&#22659;&#26410;&#20986;&#29616;&#38656;&#35201;&#31435;&#21363;&#22788;&#29702;&#30340;&#31995;&#32479;&#32423;&#38382;&#39064;&#12290;</span>
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

    <section class="settings-layout">
      <article class="surface-card">
        <div class="panel-head compact-head">
          <div>
            <h2>&#25968;&#25454;&#21344;&#29992;</h2>
            <p class="helper-text">
              &#37325;&#28857;&#30475;&#19978;&#20256;&#30446;&#24405;&#12289;&#36755;&#20986;&#30446;&#24405;&#21644;&#20851;&#38190;&#28857;&#32531;&#23384;&#65292;
              &#36991;&#20813;&#26700;&#38754;&#31471;&#38271;&#26102;&#38388;&#20351;&#29992;&#21518;&#20307;&#31215;&#22833;&#25511;&#12290;
            </p>
          </div>
        </div>

        <div class="settings-card-grid">
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
            <h2>&#36816;&#34892;&#36335;&#24452;</h2>
            <p class="helper-text">
              &#36825;&#20123;&#30446;&#24405;&#20915;&#23450;&#20102;&#32032;&#26448;&#12289;&#36755;&#20986;&#21644;&#27169;&#22411;&#23454;&#38469;&#33853;&#22312;&#21738;&#37324;&#65292;
              &#20063;&#26041;&#20415;&#20320;&#29992; Navicat &#25110;&#36164;&#28304;&#31649;&#29702;&#22120;&#36827;&#34892;&#25490;&#26597;&#12290;
            </p>
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
          <h2>&#25968;&#25454;&#32500;&#25252;</h2>
          <p class="helper-text">
            &#25226;&#26368;&#39640;&#20215;&#20540;&#30340;&#32500;&#25252;&#21160;&#20316;&#25910;&#36827;&#30028;&#38754;&#12290;&#24403;&#21069;&#25903;&#25345;&#37325;&#24314;&#25253;&#21578;&#34920;&#12289;
            &#35009;&#21098;&#26087;&#36755;&#20986;&#21644;&#28165;&#29702;&#35843;&#35797;&#20135;&#29289;&#12290;
          </p>
        </div>
      </div>

      <div class="settings-maintenance-grid">
        <div class="list-item-card settings-maintenance-card">
          <strong>&#21382;&#21490;&#25253;&#21578;&#37325;&#24314;</strong>
          <span class="helper-text">
            &#37325;&#26032;&#25195;&#25551;&#24050;&#33853;&#30424;&#30340;&#20998;&#26512;&#32467;&#26524;&#65292;&#25226;&#25253;&#21578;&#34920;&#37324;&#30340;&#24471;&#20998;&#12289;&#21487;&#20449;&#24230;
            &#21644;&#25688;&#35201;&#38142;&#25509;&#20462;&#22797;&#40784;&#12290;
          </span>
          <div class="settings-maintenance-foot">
            <span class="field-help">{{ rebuildHint }}</span>
            <button :disabled="actionLoading" @click="runRebuildReports">
              {{ actionLoading ? actionLoadingLabel : rebuildLabel }}
            </button>
          </div>
        </div>

        <div class="list-item-card settings-maintenance-card">
          <strong>&#35009;&#21098;&#26087;&#36755;&#20986;</strong>
          <span class="helper-text">
            &#21482;&#20445;&#30041;&#26368;&#36817;&#33509;&#24178;&#32452;&#20998;&#26512;&#36755;&#20986;&#65292;&#29992;&#20110;&#25511;&#21046; <code>outputs</code> &#30446;&#24405;&#30340;&#38271;&#26399;&#22686;&#38271;&#12290;
          </span>
          <div class="settings-inline-field">
            <label class="field-label">&#20445;&#30041;&#32452;&#25968;</label>
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
          <strong>&#28165;&#29702;&#35843;&#35797;&#20135;&#29289;</strong>
          <span class="helper-text">
            &#21024;&#38500; debug &#30446;&#24405;&#21644;&#35843;&#35797;&#22270;&#34920;&#65292;&#20445;&#30041;&#25253;&#21578;&#12289;&#26102;&#38388;&#36724;&#21644;&#39592;&#26550;&#35270;&#39057;&#31561;&#20027;&#36755;&#20986;&#12290;
          </span>
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
const rebuildLabel = "重建报告表";
const trimLabel = "清理旧输出";
const cleanupLabel = "清理调试产物";
const actionDoneTitle = "维护动作已完成";
const actionFailTitle = "维护动作失败";
const affectedCountLabel = "影响项数：";
const freedSpaceLabel = "释放空间：";
const reportCountLabel = "当前报告记录数：";
const loadErrorText = "系统状态加载失败";
const maintenanceErrorText = "维护动作执行失败";
const headlineLabel = "健康中心";
const nextActionLabel = "建议下一步：";
const checkedAtLabel = "最后检查：";
const urgentLabel = "紧急问题";
const attentionIssuesLabel = "需关注项";
const healthyItemsLabel = "正常项";
const rebuildHint = "适合在补入新字段或修复旧报告后执行。";
const trimHint = "建议可先保留 5 到 10 组，兼顾可回看性和空间占用。";
const cleanupHint = "适合在长时间调试后执行，不会碰主输出文件。";
const checkedAtFallback = "尚未记录";
const headlineDefaultTitle = "当前环境整体可用";
const headlineWarnTitle = "当前环境存在风险项";
const headlineDefaultSummary = "主要服务和数据目录状态稳定，可以继续进行分析和历史结果管理。";
const headlineWarnSummary = "检测到一些影响运行体验或数据持久化的问题，建议先处理高优先级项再继续长时间使用。";
const headlineDefaultAction = "保持当前配置，定期清理旧输出即可。";

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
  return [
    makeCheckItem("app_home", "运行目录", checks.app_home),
    makeCheckItem("disk", "磁盘空间", checks.disk),
    makeCheckItem("model_file", "模型文件", checks.model_file),
    makeCheckItem("postgresql", "PostgreSQL", checks.postgresql),
    makeCheckItem("redis", "Redis", checks.redis),
  ];
});

const urgentCount = computed(() => insightItems.value.filter((item) => item.tone === "danger").length);
const warnCount = computed(() => insightItems.value.filter((item) => item.tone === "warn").length);
const passCount = computed(() => checkItems.value.filter((item) => item.tone === "ok").length);
const healthTone = computed(() => {
  if (urgentCount.value > 0) return "danger";
  if (warnCount.value > 0 || !status.value?.ok) return "warn";
  return "ok";
});
const headlineTitle = computed(() => (healthTone.value === "ok" ? headlineDefaultTitle : headlineWarnTitle));
const headlineSummary = computed(() => (healthTone.value === "ok" ? headlineDefaultSummary : headlineWarnSummary));
const headlineAction = computed(() => insightItems.value[0]?.action || headlineDefaultAction);
const checkedAtText = computed(() => {
  const value = status.value?.checked_at;
  if (!value) return checkedAtFallback;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return checkedAtFallback;
  return parsed.toLocaleString("zh-CN", { hour12: false });
});
const tasksShortcutCopy = computed(() => (urgentCount.value > 0 ? tasksShortcutRisk : tasksShortcutBase));
const reportsShortcutCopy = computed(() => (warnCount.value > 0 ? reportsShortcutRisk : reportsShortcutBase));
const compareShortcutCopy = computed(() => (healthTone.value === "ok" ? compareShortcutHealthy : compareShortcutRisk));

const insightItems = computed<InsightItem[]>(() => {
  const checks = status.value?.checks || {};
  const storage = status.value?.storage || {};
  const items: InsightItem[] = [];

  if (checks.redis?.status === "fail") {
    items.push({
      key: "redis",
      title: "Redis 未连接",
      level: "高优先级",
      tone: "danger",
      summary: checks.redis?.detail || "Redis 连接失败，当前队列执行会受影响。",
      action: "建议先启动本地 Redis 服务，再回到动作分析页发起新任务。",
    });
  }

  if (checks.postgresql?.status === "fail") {
    items.push({
      key: "postgresql",
      title: "PostgreSQL 异常",
      level: "高优先级",
      tone: "danger",
      summary:
        checks.postgresql?.detail ||
        "PostgreSQL 暂时不可用，任务和报告持久化会受影响。",
      action: "建议先启动本地 PostgreSQL，然后再刷新状态确认。",
    });
  }

  if (checks.model_file?.status === "fail") {
    items.push({
      key: "model_file",
      title: "模型文件缺失",
      level: "高优先级",
      tone: "danger",
      summary: checks.model_file?.detail || "检测到必要模型文件不存在，无法正常执行姿态提取。",
      action: "请先检查 models 目录和配置路径，确保模型已随项目就位。",
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
      summary: `当前可用空间 ${freeGb} GB，低于阈值 ${minGb} GB。`,
      action: "可以先用下方的“清理旧输出”和“清理调试产物”来释放空间。",
    });
  }

  const outputBytes = Number(storage.outputs?.bytes || 0);
  if (outputBytes >= 2 * 1024 ** 3) {
    items.push({
      key: "outputs_size",
      title: "分析输出体积偏大",
      level: "中优先级",
      tone: "warn",
      summary: `outputs 目录当前约为 ${formatSize(outputBytes)}，长期累积可能拖慢桌面端管理体验。`,
      action: "建议设定较低的输出保留组数，并定期裁剪旧输出。",
    });
  }

  if (status.value && !status.value.ok && !items.length) {
    items.push({
      key: "generic",
      title: "存在待处理项",
      level: "中优先级",
      tone: "warn",
      summary: "当前系统未全部通过健康检查，但主要基础能力仍可使用。",
      action: "可以优先对照上方检查项逐个确认详情。",
    });
  }

  return items;
});

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
  const rawStatus = String(value?.status || "disabled");
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

function goToTasks() {
  void router.push("/tasks");
}

function goToReports() {
  void router.push("/reports");
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
.settings-overview {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(280px, 0.7fr);
  gap: 14px;
  margin-top: 16px;
}

.overview-hero,
.overview-metric,
.settings-check-card,
.settings-insight-card,
.settings-maintenance-card {
  position: relative;
  overflow: hidden;
}

.overview-hero {
  display: grid;
  gap: 10px;
  padding: 18px 20px;
  border-radius: 18px;
  border: 1px solid var(--line);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96) 0%, rgba(247, 249, 252, 0.92) 100%);
}

.overview-hero::before {
  content: "";
  position: absolute;
  inset: 0 auto 0 0;
  width: 4px;
  background: rgba(226, 109, 61, 0.25);
}

.overview-hero[data-tone="ok"]::before {
  background: rgba(31, 143, 95, 0.9);
}

.overview-hero[data-tone="warn"]::before {
  background: rgba(182, 122, 16, 0.9);
}

.overview-hero[data-tone="danger"]::before {
  background: rgba(216, 76, 76, 0.92);
}

.overview-kicker {
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
}

.overview-title {
  font-size: 1.28rem;
  line-height: 1.35;
}

.overview-copy,
.overview-meta {
  margin: 0;
  color: var(--muted);
}

.overview-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 18px;
  font-size: 0.92rem;
}

.overview-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.overview-metric {
  display: grid;
  gap: 8px;
  padding: 16px;
  border-radius: 18px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.88);
}

.overview-metric[data-tone="danger"] {
  background: linear-gradient(180deg, rgba(216, 76, 76, 0.08) 0%, rgba(255, 255, 255, 0.96) 100%);
}

.overview-metric[data-tone="warn"] {
  background: linear-gradient(180deg, rgba(182, 122, 16, 0.08) 0%, rgba(255, 255, 255, 0.96) 100%);
}

.overview-metric[data-tone="ok"] {
  background: linear-gradient(180deg, rgba(31, 143, 95, 0.08) 0%, rgba(255, 255, 255, 0.96) 100%);
}

.overview-metric-label {
  color: var(--muted);
  font-size: 0.88rem;
}

.overview-metric-value {
  font-size: 1.5rem;
  line-height: 1;
}

.settings-shortcuts {
  display: grid;
  gap: 12px;
  margin-top: 16px;
}

.settings-shortcuts-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.settings-shortcut-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
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

.settings-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(320px, 0.95fr);
  gap: 16px;
}

.settings-card-grid,
.settings-maintenance-grid {
  display: grid;
  gap: 12px;
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

.settings-check-card::before,
.settings-insight-card::before {
  content: "";
  position: absolute;
  inset: 0 auto 0 0;
  width: 4px;
  background: rgba(15, 23, 42, 0.08);
}

.settings-check-card[data-tone="ok"]::before,
.settings-insight-card[data-tone="ok"]::before {
  background: rgba(31, 143, 95, 0.86);
}

.settings-check-card[data-tone="danger"]::before,
.settings-insight-card[data-tone="danger"]::before {
  background: rgba(216, 76, 76, 0.9);
}

.settings-check-card[data-tone="warn"]::before,
.settings-insight-card[data-tone="warn"]::before {
  background: rgba(182, 122, 16, 0.88);
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
  .settings-overview,
  .settings-layout,
  .settings-maintenance-grid,
  .settings-shortcut-grid {
    grid-template-columns: 1fr;
  }

  .overview-metrics {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .settings-shortcuts-head {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 760px) {
  .overview-metrics {
    grid-template-columns: 1fr;
  }
}
</style>
