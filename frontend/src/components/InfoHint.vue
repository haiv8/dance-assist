<template>
  <span class="info-hint">
    <button class="info-hint-trigger" type="button" :aria-label="text" @click.stop @keydown.stop>
      <span aria-hidden="true">!</span>
    </button>
    <span class="info-hint-popover" role="tooltip">{{ text }}</span>
  </span>
</template>

<script setup lang="ts">
defineProps<{
  text: string;
}>();
</script>

<style scoped>
.info-hint {
  position: relative;
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  z-index: 10010;
}

.info-hint-trigger {
  display: inline-grid;
  place-items: center;
  width: 22px;
  height: 22px;
  min-height: 22px;
  padding: 0;
  border-radius: 999px;
  border: 1px solid rgba(15, 23, 42, 0.14);
  background: rgba(241, 247, 251, 0.95);
  color: var(--muted);
  box-shadow: none;
  font-size: 0.72rem;
  font-weight: 750;
  line-height: 1;
  text-transform: none;
  letter-spacing: 0;
}

.info-hint-trigger:hover,
.info-hint-trigger:focus-visible {
  color: var(--accent-dark);
  border-color: rgba(15, 143, 179, 0.34);
  background: rgba(232, 247, 252, 0.98);
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
  outline: none;
  transform: none;
}

.info-hint-popover {
  position: absolute;
  z-index: 10020;
  left: 50%;
  bottom: calc(100% + 10px);
  width: min(320px, calc(100vw - 48px));
  max-width: calc(100vw - 48px);
  box-sizing: border-box;
  padding: 10px 12px;
  border-radius: 14px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  background: rgba(17, 24, 39, 0.94);
  color: #fff;
  box-shadow: 0 18px 38px rgba(15, 23, 42, 0.18);
  font-size: 0.82rem;
  font-weight: 400;
  line-height: 1.55;
  letter-spacing: 0;
  overflow-wrap: anywhere;
  word-break: break-word;
  white-space: normal;
  opacity: 0;
  pointer-events: none;
  transform: translate(-50%, 4px);
  transition: opacity 0.14s ease, transform 0.14s ease;
}

.info-hint-popover::after {
  content: "";
  position: absolute;
  left: 50%;
  top: 100%;
  width: 10px;
  height: 10px;
  background: rgba(17, 24, 39, 0.94);
  transform: translate(-50%, -5px) rotate(45deg);
}

.info-hint:hover .info-hint-popover,
.info-hint:focus-within .info-hint-popover {
  opacity: 1;
  transform: translate(-50%, 0);
}

@media (max-width: 720px) {
  .info-hint-popover {
    left: auto;
    right: 0;
    transform: translate(0, 4px);
  }

  .info-hint:hover .info-hint-popover,
  .info-hint:focus-within .info-hint-popover {
    transform: translate(0, 0);
  }

  .info-hint-popover::after {
    left: auto;
    right: 8px;
  }
}
</style>
