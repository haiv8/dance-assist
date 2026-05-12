import axios from "axios";
import { appConfig, buildApiUrl } from "../config/appConfig";

export const http = axios.create({
  baseURL: appConfig.apiBaseUrl,
  timeout: 30_000,
});

export function absMediaUrl(url: string): string {
  if (!url) return "";
  return buildApiUrl(url);
}
