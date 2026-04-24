const RUNNING_TASK_DELETE_MESSAGE =
  "\u4efb\u52a1\u4ecd\u5728\u8fd0\u884c\uff0c\u4e0d\u80fd\u76f4\u63a5\u5220\u9664\u3002\u8bf7\u5148\u53d6\u6d88\u4efb\u52a1\uff0c\u7b49\u72b6\u6001\u53d8\u6210\u5df2\u53d6\u6d88\u6216\u5931\u8d25\u540e\u518d\u5220\u9664\u3002";

function extractBackendMessage(err: unknown, fallback: string) {
  const anyErr = err as any;
  const detail = anyErr?.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) return detail.trim();
  if (typeof anyErr?.message === "string" && anyErr.message.trim()) return anyErr.message.trim();
  return fallback;
}

export function friendlyError(err: unknown, fallback: string) {
  const message = extractBackendMessage(err, fallback);
  const lower = message.toLowerCase();
  const code = String((err as any)?.code || "").toLowerCase();

  if (code === "err_network" || lower === "network error") {
    return "\u65e0\u6cd5\u8fde\u63a5\u5230\u540e\u7aef\u670d\u52a1\uff0c\u8bf7\u786e\u8ba4\u672c\u5730\u540e\u7aef\u5df2\u542f\u52a8\u540e\u518d\u8bd5\u3002";
  }
  if (code === "econnaborted" || lower.includes("timeout")) {
    return "\u8bf7\u6c42\u8d85\u65f6\u4e86\uff0c\u53ef\u80fd\u662f\u5206\u6790\u6216 AI \u751f\u6210\u8fd8\u5728\u5904\u7406\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002";
  }

  if (lower === "running task cannot be deleted" || lower === "running task can not be deleted") {
    return RUNNING_TASK_DELETE_MESSAGE;
  }
  if (lower === "pipeline is still running") {
    return "\u4efb\u52a1\u8fd8\u5728\u8fd0\u884c\u4e2d\uff0c\u8bf7\u7b49\u5b83\u5b8c\u6210\u6216\u5148\u53d6\u6d88\u540e\u518d\u91cd\u8bd5\u3002";
  }
  if (lower.startsWith("pipeline not found") || lower === "pipeline summary not found") {
    return "\u6ca1\u6709\u627e\u5230\u8fd9\u6761\u5206\u6790\u8bb0\u5f55\uff0c\u53ef\u80fd\u5df2\u7ecf\u88ab\u5220\u9664\u6216\u5386\u53f2\u6570\u636e\u5c1a\u672a\u540c\u6b65\u3002";
  }
  if (lower === "pipeline id is required") {
    return "\u7f3a\u5c11\u4efb\u52a1 ID\uff0c\u8bf7\u5237\u65b0\u5217\u8868\u540e\u518d\u64cd\u4f5c\u3002";
  }
  if (lower === "pipeline retry requires teacher/user video ids") {
    return "\u8fd9\u6761\u8bb0\u5f55\u7f3a\u5c11\u6559\u5e08\u6216\u5b66\u5458\u7d20\u6750\uff0c\u6682\u65f6\u4e0d\u80fd\u91cd\u65b0\u5206\u6790\u3002";
  }
  if (lower.startsWith("frame out of range")) {
    return "\u5f53\u524d\u5e27\u4e0d\u5728\u53ef\u7528\u7684\u5206\u6790\u8303\u56f4\u5185\uff0c\u8bf7\u6362\u4e00\u4e2a\u65f6\u95f4\u70b9\u67e5\u770b\u3002";
  }
  if (lower.startsWith("unsupported extension")) {
    return "\u4e0d\u652f\u6301\u8fd9\u4e2a\u89c6\u9891\u683c\u5f0f\uff0c\u8bf7\u4f7f\u7528 MP4\u3001MOV\u3001AVI\u3001MKV \u6216 M4V \u6587\u4ef6\u3002";
  }
  if (lower.startsWith("file too large")) {
    const maxMatch = message.match(/max\s+(\d+)mb/i);
    const maxText = maxMatch?.[1] ? `\uff0c\u6700\u5927\u652f\u6301 ${maxMatch[1]}MB` : "";
    return `\u6587\u4ef6\u592a\u5927${maxText}\uff0c\u8bf7\u538b\u7f29\u6216\u622a\u53d6\u540e\u518d\u4e0a\u4f20\u3002`;
  }
  if (lower === "name cannot be empty") {
    return "\u540d\u79f0\u4e0d\u80fd\u4e3a\u7a7a\uff0c\u8bf7\u5148\u8f93\u5165\u7d20\u6750\u540d\u79f0\u3002";
  }
  if (lower === "role must be teacher or user") {
    return "\u7d20\u6750\u89d2\u8272\u5f02\u5e38\uff0c\u8bf7\u91cd\u65b0\u9009\u62e9\u201c\u6559\u5e08\u793a\u8303\u201d\u6216\u201c\u5b66\u5458\u7ec3\u4e60\u201d\u3002";
  }
  if (lower.startsWith("video not found") || lower === "video file not found") {
    return "\u6ca1\u6709\u627e\u5230\u8fd9\u4e2a\u7d20\u6750\uff0c\u53ef\u80fd\u5df2\u7ecf\u88ab\u5220\u9664\uff0c\u8bf7\u5237\u65b0\u7d20\u6750\u5e93\u3002";
  }
  if (lower === "file not found") {
    return "\u6587\u4ef6\u4e0d\u5b58\u5728\u6216\u5df2\u88ab\u6e05\u7406\uff0c\u8bf7\u5237\u65b0\u540e\u518d\u8bd5\u3002";
  }
  if (lower === "invalid range" || lower === "multiple ranges not supported" || lower === "range not satisfiable") {
    return "\u89c6\u9891\u8bfb\u53d6\u8303\u56f4\u65e0\u6548\uff0c\u8bf7\u5237\u65b0\u9875\u9762\u540e\u518d\u64ad\u653e\u3002";
  }
  if (lower.startsWith("aliyun dashscope request failed")) {
    return "\u963f\u91cc\u4e91 AI \u8bf7\u6c42\u5931\u8d25\uff0c\u8bf7\u68c0\u67e5 API Key\u3001\u6a21\u578b\u914d\u7f6e\u6216\u7f51\u7edc\u540e\u518d\u8bd5\u3002";
  }
  if (lower.startsWith("openai request failed")) {
    return "OpenAI \u8bf7\u6c42\u5931\u8d25\uff0c\u8bf7\u68c0\u67e5 API Key\u3001\u6a21\u578b\u914d\u7f6e\u6216\u7f51\u7edc\u540e\u518d\u8bd5\u3002";
  }
  if (lower.includes("response did not include")) {
    return "AI \u8fd4\u56de\u5185\u5bb9\u4e0d\u5b8c\u6574\uff0c\u8bf7\u7a0d\u540e\u91cd\u65b0\u751f\u6210\u3002";
  }

  return message;
}

export function runningTaskDeleteMessage() {
  return RUNNING_TASK_DELETE_MESSAGE;
}
