<template>
  <div ref="editorElement"></div>
</template>

<script setup>
import Editor from "@toast-ui/editor";
import "@toast-ui/editor/dist/i18n/zh-cn";
import { onMounted, onBeforeUnmount, ref } from "vue";

import baseOptions from "./baseOptions.js";

Editor.setLanguage("zh-CN", { WYSIWYG: "富文本", URL: "网址" });

const props = defineProps({
  initialValue: String,
  initialEditType: {
    type: String,
    default: "markdown",
  },
  addImageBlobHook: Function,
});

const emit = defineEmits(["change", "keydown"]);

const editorElement = ref();
let toastEditor;
const desktop = window.matchMedia("(min-width: 1024px)");
const updatePreview = () => toastEditor.changePreviewStyle(desktop.matches ? "vertical" : "tab");
const editorHeight = () => `${Math.max(520, window.innerHeight - 320)}px`;
const updateHeight = () => toastEditor.setHeight(editorHeight());

onMounted(() => {
  toastEditor = new Editor({
    ...baseOptions,
    height: editorHeight(),
    language: "zh-CN",
    autofocus: false,
    previewStyle: desktop.matches ? "vertical" : "tab",
    el: editorElement.value,
    initialValue: props.initialValue,
    initialEditType: props.initialEditType,
    events: {
      change: () => {
        emit("change");
      },
      keydown: (_, event) => {
        emit("keydown", event);
      },
    },
    hooks: props.addImageBlobHook
      ? { addImageBlobHook: props.addImageBlobHook }
      : {},
  });
  desktop.addEventListener("change", updatePreview);
  window.addEventListener("resize", updateHeight);
  editorElement.value.querySelector('.scroll-sync input')?.setAttribute('aria-label', '同步滚动');
});

onBeforeUnmount(() => {
  desktop.removeEventListener("change", updatePreview);
  window.removeEventListener("resize", updateHeight);
  toastEditor?.destroy();
});

function getMarkdown() {
  return toastEditor.getMarkdown();
}

function isWysiwygMode() {
  return toastEditor.isWysiwygMode();
}

defineExpose({ getMarkdown, isWysiwygMode });
</script>

<style>
@import "@toast-ui/editor/dist/toastui-editor.css";
@import "prismjs/themes/prism.css";
@import "@toast-ui/editor-plugin-code-syntax-highlight/dist/toastui-editor-plugin-code-syntax-highlight.css";
@import "./toastui-editor-overrides.scss";
</style>
