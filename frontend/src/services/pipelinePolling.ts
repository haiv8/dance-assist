import { appConfig } from "../config/appConfig";
import type { PipelineStatusResponse } from "../types/video";
import { isTerminalPipelineStatus } from "./pipelineStatus";

type TimerHandle = ReturnType<typeof window.setInterval>;

export interface PipelinePollerOptions {
  getStatus: (pipelineId: string) => Promise<PipelineStatusResponse>;
  onStatus: (status: PipelineStatusResponse) => void;
  onTerminal?: (status: PipelineStatusResponse) => Promise<void> | void;
  onError: (error: unknown) => void;
  intervalMs?: number;
  setIntervalFn?: typeof window.setInterval;
  clearIntervalFn?: typeof window.clearInterval;
}

export interface PipelinePoller {
  readonly activePipelineId: string;
  start: (pipelineId: string, options?: { immediate?: boolean }) => void;
  stop: () => void;
  tick: (pipelineId?: string) => Promise<void>;
}

export function createPipelinePoller(options: PipelinePollerOptions): PipelinePoller {
  const intervalMs = options.intervalMs ?? appConfig.pipelinePollIntervalMs;
  const setIntervalFn = options.setIntervalFn ?? window.setInterval.bind(window);
  const clearIntervalFn = options.clearIntervalFn ?? window.clearInterval.bind(window);
  let timer: TimerHandle | null = null;
  let activePipelineId = "";
  let inFlight = false;

  function stop() {
    if (timer !== null) {
      clearIntervalFn(timer);
      timer = null;
    }
  }

  async function tick(pipelineId = activePipelineId) {
    if (!pipelineId || inFlight) return;
    inFlight = true;
    try {
      const status = await options.getStatus(pipelineId);
      options.onStatus(status);
      if (isTerminalPipelineStatus(status.status)) {
        stop();
        await options.onTerminal?.(status);
      }
    } catch (error) {
      stop();
      options.onError(error);
    } finally {
      inFlight = false;
    }
  }

  function start(pipelineId: string, startOptions?: { immediate?: boolean }) {
    stop();
    activePipelineId = pipelineId;
    timer = setIntervalFn(() => {
      void tick(pipelineId);
    }, intervalMs);
    if (startOptions?.immediate !== false) {
      void tick(pipelineId);
    }
  }

  return {
    get activePipelineId() {
      return activePipelineId;
    },
    start,
    stop,
    tick,
  };
}
