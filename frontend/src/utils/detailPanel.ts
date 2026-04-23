import type { Ref } from "vue";

const STACKED_LAYOUT_QUERY = "(max-width: 1180px)";
const DETAIL_TOP_OFFSET = 96;

export function focusDetailPanel(
  panelRef: Ref<HTMLElement | null>,
  options?: {
    forceScroll?: boolean;
  },
) {
  if (typeof window === "undefined") return;

  window.requestAnimationFrame(() => {
    const panel = panelRef.value;
    if (!panel) return;

    const rect = panel.getBoundingClientRect();
    const isStackedLayout = window.matchMedia(STACKED_LAYOUT_QUERY).matches;
    if (!isStackedLayout && !options?.forceScroll) return;

    const isFarAboveViewport = rect.top < DETAIL_TOP_OFFSET;
    const isBelowFold = rect.top > window.innerHeight * 0.45;
    if (!options?.forceScroll && !isFarAboveViewport && !isBelowFold) return;

    const top = window.scrollY + rect.top - DETAIL_TOP_OFFSET;
    window.scrollTo({
      top: Math.max(top, 0),
      behavior: "smooth",
    });
  });
}
