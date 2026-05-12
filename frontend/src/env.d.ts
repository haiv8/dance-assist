declare module "*.vue" {
  import type { DefineComponent } from "vue";
  const component: DefineComponent<{}, {}, any>;
  export default component;
}

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_PIPELINE_POLL_INTERVAL_MS?: string;
  readonly VITE_CLIPBOARD_RESET_MS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
