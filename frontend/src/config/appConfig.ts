const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const DEFAULT_PIPELINE_POLL_INTERVAL_MS = 2000;
const DEFAULT_CLIPBOARD_RESET_MS = 1400;

function normalizeBaseUrl(value: string | undefined, fallback: string): string {
  const raw = value?.trim() || fallback;
  return raw.replace(/\/+$/, "");
}

function readPositiveInt(value: string | undefined, fallback: number): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? Math.round(parsed) : fallback;
}

export const appConfig = {
  apiBaseUrl: normalizeBaseUrl(import.meta.env.VITE_API_BASE_URL, DEFAULT_API_BASE_URL),
  pipelinePollIntervalMs: readPositiveInt(
    import.meta.env.VITE_PIPELINE_POLL_INTERVAL_MS,
    DEFAULT_PIPELINE_POLL_INTERVAL_MS,
  ),
  clipboardResetMs: readPositiveInt(import.meta.env.VITE_CLIPBOARD_RESET_MS, DEFAULT_CLIPBOARD_RESET_MS),
} as const;

export function buildApiUrl(path: string): string {
  if (!path) return appConfig.apiBaseUrl;
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  return `${appConfig.apiBaseUrl}${path.startsWith("/") ? path : `/${path}`}`;
}
