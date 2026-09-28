<template>
  <div class="flex h-full flex-col items-center justify-center text-theme-text-muted">
    <p>正在跳转到统一登录…</p>
  </div>
</template>

<script setup>
import { onMounted } from "vue";

const props = defineProps({ redirect: String });
onMounted(() => {
  const redirect = props.redirect || "/";
  const basePath = new URL(document.baseURI).pathname.replace(/\/$/, "");
  window.location.replace(`${basePath}/api/oidc/login?redirect=${encodeURIComponent(basePath + redirect)}`);
});
</script>
