import axios from "axios";

const API_BASE = "http://127.0.0.1:8000";

export const http = axios.create({
  baseURL: API_BASE,
  timeout: 30_000,
});

export function absMediaUrl(url: string): string {
  if (!url) return "";
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  return `${API_BASE}${url}`;
}
