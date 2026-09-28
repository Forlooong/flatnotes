<template>
  <nav class="notes-nav" aria-label="笔记导航">
    <div class="notes-brand">
      <RouterLink :to="{ name: 'home' }" class="notes-wordmark">
        <img :src="notesIcon" width="34" height="34" alt="" />
        <span>Flatnotes</span>
      </RouterLink>
    </div>
    <div class="notes-nav-actions">
      <!-- New Note -->
      <RouterLink v-if="showNewButton" :to="{ name: 'new' }">
        <CustomButton :iconPath="mdilPlusCircle" label="新建笔记" />
      </RouterLink>
      <!-- Menu -->
      <CustomButton
        class="ml-1"
        :iconPath="mdilMenu"
        label="菜单"
        @click="toggleMenu"
      />
      <PrimeMenu ref="menu" :model="menuItems" :popup="true" />
    </div>
  </nav>
</template>

<script setup>
import {
  mdilLogout,
  mdilMagnify,
  mdilMenu,
  mdilMonitor,
  mdilNoteMultiple,
  mdilPlusCircle,
} from "@mdi/light-js";
import { computed, ref } from "vue";
import notesIcon from "../assets/notes.svg";
import { RouterLink, useRouter } from "vue-router";

import CustomButton from "../components/CustomButton.vue";
import PrimeMenu from "../components/PrimeMenu.vue";
import { authTypes, params, searchSortOptions } from "../constants.js";
import { useGlobalStore } from "../globalStore.js";
import { toggleTheme } from "../helpers.js";
import { logOut as oidcLogOut, apiErrorHandler } from "../api.js";
import { useToast } from "primevue/usetoast";

const globalStore = useGlobalStore();
const menu = ref();
const router = useRouter();
const toast = useToast();

const emit = defineEmits(["toggleSearchModal"]);

const menuItems = [
  {
    label: "搜索笔记",
    icon: mdilMagnify,
    command: () => emit("toggleSearchModal"),
    keyboardShortcut: "/",
  },
  {
    label: "全部笔记",
    icon: mdilNoteMultiple,
    command: () =>
      router.push({
        name: "search",
        query: {
          [params.searchTerm]: "*",
          [params.sortBy]: searchSortOptions.title,
        },
      }),
  },
  {
    label: "切换主题",
    icon: mdilMonitor,
    command: toggleTheme,
  },
  {
    separator: true,
    visible: showLogOutButton,
  },
  {
    label: "退出登录",
    icon: mdilLogout,
    command: logOut,
    visible: showLogOutButton,
  },
];

const showNewButton = computed(() => {
  return globalStore.config.authType !== authTypes.readOnly;
});

async function logOut() {
  try {
    const response = await oidcLogOut();
    window.location.assign(response.redirect);
  } catch (error) {
    apiErrorHandler(error, toast);
  }
}

function toggleMenu(event) {
  menu.value.toggle(event);
}

function showLogOutButton() {
  return ![authTypes.none, authTypes.readOnly].includes(globalStore.config.authType);
}
</script>
