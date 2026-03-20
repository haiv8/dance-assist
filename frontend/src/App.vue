<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, RouterView, useRoute } from "vue-router";

const route = useRoute();

const navItems = [
  { to: "/upload", label: "\u7d20\u6750\u7ba1\u7406" },
  { to: "/compare", label: "\u52a8\u4f5c\u5206\u6790" },
  { to: "/tasks", label: "\u4efb\u52a1\u4e2d\u5fc3" },
  { to: "/reports", label: "\u62a5\u544a\u4e2d\u5fc3" },
  { to: "/issues", label: "\u95ee\u9898\u56de\u653e" },
  { to: "/settings", label: "\u7cfb\u7edf\u8bbe\u7f6e" },
];

const currentSection = computed(() => {
  const hit = navItems.find((item) => route.path.startsWith(item.to));
  return hit?.label ?? "Dance Assist";
});
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand-block">
        <div class="brand-mark">DA</div>
        <div>
          <h1>Dance Assist</h1>
          <p class="brand-copy">&#33310;&#36424;&#21160;&#20316;&#20998;&#26512;&#24037;&#20316;&#21488;</p>
        </div>
      </div>

      <nav class="nav-list">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          :class="{ active: route.path.startsWith(item.to) }"
        >
          <span class="nav-label">{{ item.label }}</span>
        </RouterLink>
      </nav>

      <div class="sidebar-note">
        <span class="status-pill online">&#26412;&#22320;&#24341;&#25806;&#22312;&#32447;</span>
        <p>&#20808;&#25226;&#32032;&#26448;&#12289;&#20998;&#26512;&#12289;&#20219;&#21153;&#12289;&#25253;&#21578;&#12289;&#38382;&#39064;&#22797;&#30424;&#21644;&#31995;&#32479;&#35774;&#32622;&#20845;&#26465;&#20027;&#32447;&#20570;&#31283;&#12290;&#21518;&#32493;&#26032;&#22686;&#33021;&#21147;&#32487;&#32493;&#25286;&#25104;&#29420;&#31435;&#39029;&#38754;&#65292;&#20445;&#25345;&#26700;&#38754;&#31471;&#28165;&#26224;&#31616;&#27905;&#12290;</p>
      </div>
    </aside>

    <div class="shell-main">
      <header class="topbar simple-topbar">
        <div>
          <h2>{{ currentSection }}</h2>
          <p class="helper-text topbar-copy">&#22260;&#32469;&#32032;&#26448;&#20837;&#24211;&#12289;&#21160;&#20316;&#20998;&#26512;&#12289;&#21382;&#21490;&#20219;&#21153;&#12289;&#25253;&#21578;&#22797;&#30424;&#12289;&#38382;&#39064;&#22238;&#25918;&#19982;&#31995;&#32479;&#32500;&#25252;&#20845;&#26465;&#20027;&#32447;&#65292;&#36880;&#27493;&#25193;&#23637;&#26356;&#23436;&#25972;&#30340;&#35757;&#32451;&#24037;&#20316;&#21488;&#12290;</p>
        </div>
      </header>

      <main class="content-area">
        <RouterView />
      </main>
    </div>
  </div>
</template>
