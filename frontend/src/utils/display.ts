export function compactPipelineId(value?: string | null) {
  const text = String(value || "").trim();
  if (!text) return "--";
  if (text.length <= 12) return text;
  return `${text.slice(0, 6)}...${text.slice(-4)}`;
}
