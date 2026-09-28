<template>
  <div class="notes-search-results flex flex-col">
    <!-- Search Input -->
    <SearchInput :initialSearchTerm="props.searchTerm" class="mb-2" />

    <LoadingIndicator ref="loadingIndicator" class="flex-1">
      <!-- Sort By -->
      <div class="flex justify-end">
        <CustomButton
          :label="`排序：${sortByName}`"
          :iconPath="mdiSort"
          class="mb-1"
          @click="toggleSortMenu"
        />
        <PrimeMenu ref="sortMenu" :model="menuItems" :popup="true" />
      </div>

      <!-- Search Results -->
      <div
        v-for="result in results"
        class="notes-search-result"
      >
        <RouterLink :to="{ name: 'note', params: { title: result.title } }">
          <!-- Title and Tags -->
          <div>
            <span v-html="result.titleHighlightsOrTitle" class="mr-2"></span>
            <Tag v-for="tag in result.tagMatches" :tag="tag" class="mr-1" />
          </div>
          <!-- Last Modified and Content Highlights -->
          <div>
            <span class="text-theme-text-muted">{{
              result.lastModifiedAsString
            }}</span>
            <span v-if="result.contentHighlights"> - </span>
            <span
              v-html="result.contentHighlights"
              class="text-theme-text-muted"
            ></span>
          </div>
        </RouterLink>
      </div>
    </LoadingIndicator>
  </div>
</template>

<script setup>
import { useToast } from "primevue/usetoast";
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";

import { mdiMagnify, mdiSort } from "@mdi/js";
import { apiErrorHandler, getNotes } from "../api.js";
import CustomButton from "../components/CustomButton.vue";
import LoadingIndicator from "../components/LoadingIndicator.vue";
import PrimeMenu from "../components/PrimeMenu.vue";
import Tag from "../components/Tag.vue";
import { params, searchSortOptions } from "../constants.js";
import SearchInput from "../partials/SearchInput.vue";

const props = defineProps({
  searchTerm: String,
  sortBy: {
    type: Number,
    default: searchSortOptions.score,
  },
});

const loadingIndicator = ref();
const results = ref([]);
const router = useRouter();
const sortMenu = ref();
const toast = useToast();

const sortByName = computed(() => {
  const sortOptionNames = {
    [searchSortOptions.title]: "标题",
    [searchSortOptions.lastModified]: "最近修改",
    [searchSortOptions.score]: "相关程度",
  };
  return sortOptionNames[props.sortBy];
});

function init() {
  loadingIndicator.value.setLoading();
  getNotes(props.searchTerm)
    .then((data) => {
      results.value = sortResults(data);
      if (results.value.length > 0) {
        loadingIndicator.value.setLoaded();
      } else {
        loadingIndicator.value.setFailed("没有找到笔记", mdiMagnify);
      }
    })
    .catch((error) => {
      loadingIndicator.value.setFailed();
      apiErrorHandler(error, toast);
    });
}

function sortResults(results) {
  if (props.sortBy === searchSortOptions.title) {
    return results.sort((a, b) => a.title.localeCompare(b.title));
  } else if (props.sortBy === searchSortOptions.lastModified) {
    return results.sort((a, b) => b.lastModified - a.lastModified);
  } else {
    return results.sort((a, b) => b.score - a.score);
  }
}

function reSortResults() {
  results.value = sortResults(results.value);
}

function updateSortByParam(sortBy) {
  router.push({
    name: "search",
    query: {
      [params.searchTerm]: props.searchTerm,
      [params.sortBy]: sortBy,
    },
  });
}

const menuItems = [
  {
    label: "按相关程度排序",
    command: () => {
      updateSortByParam(searchSortOptions.score);
    },
  },

  {
    label: "按标题排序",
    command: () => {
      updateSortByParam(searchSortOptions.title);
    },
  },
  {
    label: "按最近修改排序",
    command: () => {
      updateSortByParam(searchSortOptions.lastModified);
    },
  },
];

function toggleSortMenu(event) {
  sortMenu.value.toggle(event);
}

watch(() => props.searchTerm, init);
watch(() => props.sortBy, reSortResults);
onMounted(init);
</script>

<style>
.match {
  @apply text-theme-brand;
}
</style>
