<template>
  <div class="shared-notes-home">
    <section class="shared-notes-hero">
      <h1>一起记下，随时翻阅。</h1>
      <p>这里的笔记由网站成员共同查看和编辑。</p>
    </section>

    <SearchInput
      large
      class="shared-notes-search"
      placeholder="搜索标题、内容或 #标签…"
    />

    <section class="shared-notes-recent">
      <h2>最近修改</h2>
      <LoadingIndicator
        ref="loadingIndicator"
        class="flex min-h-56 flex-col"
        hideLoader
      >
        <RouterLink
          v-for="note in notes.slice(0, globalStore.config.quickAccessLimit)"
          :key="note.title"
          :to="{ name: 'note', params: { title: note.title } }"
          class="shared-notes-row"
        >
          {{ note.title }}
        </RouterLink>
        <RouterLink
          v-if="notes.length > globalStore.config.quickAccessLimit"
          :to="{
            name: 'search',
            query: {
              term: globalStore.config.quickAccessTerm,
              sortBy: searchSortOptions[globalStore.config.quickAccessSort],
            },
          }"
          class="shared-notes-more"
        >
          查看全部笔记
        </RouterLink>
      </LoadingIndicator>
    </section>
  </div>
</template>

<script setup>
import { useToast } from "primevue/usetoast";
import { onMounted, ref, watch } from "vue";
import { RouterLink } from "vue-router";

import { apiErrorHandler, getNotes } from "../api.js";
import LoadingIndicator from "../components/LoadingIndicator.vue";
import { searchSortOptions } from "../constants.js";
import { useGlobalStore } from "../globalStore.js";
import SearchInput from "../partials/SearchInput.vue";

const globalStore = useGlobalStore();
const loadingIndicator = ref();
const notes = ref([]);
const toast = useToast();

function init() {
  if (globalStore.config.quickAccessHide) {
    loadingIndicator.value?.setLoaded();
    return;
  }
  getNotes(
    globalStore.config.quickAccessTerm,
    globalStore.config.quickAccessSort,
    globalStore.config.quickAccessSort === "title" ? "asc" : "desc",
    globalStore.config.quickAccessLimit + 1,
  )
    .then((data) => {
      notes.value = data;
      loadingIndicator.value?.setLoaded();
    })
    .catch((error) => {
      loadingIndicator.value?.setFailed();
      apiErrorHandler(error, toast);
    });
}

watch(() => globalStore.config.quickAccessHide, init);
onMounted(init);
</script>
