<template>
  <Modal v-model="isVisible" class="border-none">
    <SearchInput
      large
      placeholder="搜索标题、内容或 #标签…"
      @search="toggleHandler"
      @keydown.esc="toggleHandler"
    />
  </Modal>
</template>

<script setup>
import Modal from "../components/Modal.vue";
import SearchInput from "./SearchInput.vue";

const isVisible = defineModel({ type: Boolean });

function toggleHandler() {
  isVisible.value = !isVisible.value;
}
</script>
