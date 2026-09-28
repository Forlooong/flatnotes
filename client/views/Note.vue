<template>
  <!-- Confirm Deletion Modal -->
  <ConfirmModal
    v-model="isDeleteModalVisible"
    title="确认删除"
    :message="`确定删除笔记“${note.title}”吗？此操作无法撤销。`"
    confirmButtonText="删除"
    confirmButtonStyle="danger"
    @confirm="deleteConfirmedHandler"
  />

  <!-- Save Changes Modal -->
  <ConfirmModal
    v-model="isSaveChangesModalVisible"
    title="保存修改"
    message="是否保存本次修改？"
    confirmButtonText="保存"
    confirmButtonStyle="success"
    rejectButtonText="放弃修改"
    rejectButtonStyle="danger"
    @confirm="saveHandler((close = true))"
    @reject="closeNote"
  />

  <!-- Draft Modal -->
  <ConfirmModal
    v-model="isDraftModalVisible"
    title="发现未保存的草稿"
    message="此浏览器中保留了这篇笔记的草稿。要继续编辑草稿，还是删除草稿？"
    confirmButtonText="继续草稿"
    confirmButtonStyle="cta"
    rejectButtonText="删除草稿"
    rejectButtonStyle="danger"
    @confirm="setEditMode()"
    @reject="
      clearDraft();
      setEditMode();
    "
  />

  <LoadingIndicator ref="loadingIndicator" class="notes-document flex flex-col">
    <!-- Header -->
    <div class="notes-document-header">
      <!-- Title -->
      <div class="notes-document-title">
        <span v-show="!editMode" :title="note.title">{{ note.title }}</span>
        <input
          v-show="editMode"
          v-model.trim="newTitle"
          class="w-full bg-theme-background outline-none"
          placeholder="笔记标题" aria-label="笔记标题"
        />
      </div>

      <!-- Buttons -->
      <div class="notes-document-actions print:hidden">
        <!-- Delete Button -->
        <CustomButton
          v-show="canModify && !isNewNote"
          label="删除"
          :iconPath="mdilDelete"
          @click="deleteHandler"
        />
        <!-- Save Button -->
        <CustomButton
          v-show="editMode"
          label="保存"
          :iconPath="mdilContentSave"
          @click="saveHandler((close = false))"
          class="relative ml-1"
        >
          <!-- Unsaved Changes Indicator -->
          <div
            v-show="unsavedChanges"
            class="absolute right-1 h-1.5 w-1.5 rounded-full bg-theme-brand"
          ></div>
        </CustomButton>
        <!-- Edit Toggle -->
        <Toggle
          v-if="canModify"
          label="编辑"
          :isOn="editMode"
          class="ml-1"
          @click="toggleEditModeHandler"
        />
      </div>
    </div>

    <hr v-if="!editMode" class="my-4 border-theme-border" />

    <!-- Content -->
    <div class="flex-1">
      <ToastViewer
        v-if="!editMode"
        :initialValue="note.content"
        class="toast-viewer pb-4"
      />
      <ToastEditor
        v-if="editMode"
        ref="toastEditor"
        :initialValue="getInitialEditorValue()"
        :initialEditType="loadDefaultEditorMode()"
        :addImageBlobHook="addImageBlobHook"
        @change="startContentChangedTimeout"
        @keydown="keydownHandler"
      />
    </div>
  </LoadingIndicator>
</template>

<style>
/* Disable checkboxes in view mode. See https://github.com/nhn/tui.editor/issues/1087. */
.toast-viewer li.task-list-item {
  pointer-events: none;
}
.toast-viewer li.task-list-item a {
  pointer-events: auto;
}
</style>

<script setup>
import { mdiNoteOffOutline } from "@mdi/js";
import { mdilContentSave, mdilDelete } from "@mdi/light-js";
import Mousetrap from "mousetrap";
import { useToast } from "primevue/usetoast";
import { computed, nextTick, onMounted, onBeforeUnmount, ref, watch } from "vue";
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRouter } from "vue-router";

import {
  apiErrorHandler,
  createAttachment,
  createNote,
  deleteNote,
  getNote,
  updateNote,
  syncAttachmentDraft,
} from "../api.js";
import { Note } from "../classes.js";
import ConfirmModal from "../components/ConfirmModal.vue";
import CustomButton from "../components/CustomButton.vue";
import LoadingIndicator from "../components/LoadingIndicator.vue";
import Toggle from "../components/Toggle.vue";
import ToastEditor from "../components/toastui/ToastEditor.vue";
import ToastViewer from "../components/toastui/ToastViewer.vue";
import { authTypes } from "../constants.js";
import { useGlobalStore } from "../globalStore.js";
import { getToastOptions } from "../helpers.js";

const props = defineProps({
  title: String,
});

const canModify = computed(
  () => globalStore.config.authType != authTypes.readOnly,
);
let contentChangedTimeout = null;
let draftId = null;
let settledUploads = [];
let draftSync = Promise.resolve();
const uploads = new Set();
function draftKey() { return `flatnotes:attachment-draft:${String(note.value.title)}`; }
function ensureDraftId() {
  if (!draftId) {
    draftId = localStorage.getItem(draftKey()) || crypto.randomUUID();
    localStorage.setItem(draftKey(), draftId);
  }
  return draftId;
}
function syncDraft(content, discard = false) {
  const id = ensureDraftId();
  const settled = [...settledUploads];
  const cleanupKey = `flatnotes:attachment-cleanup:${id}`;
  if (discard) localStorage.setItem(cleanupKey, "pending");
  draftSync = draftSync.catch(() => {}).then(() => syncAttachmentDraft(id, content, settled, discard)).then(() => {
    if (discard) localStorage.removeItem(cleanupKey);
  });
  draftSync.catch(() => {
    toast.add(getToastOptions(discard ? "附件清理暂未完成，下次打开编辑页时会重试。" : "草稿正文已留在此浏览器，附件同步未完成；请联网后再次保存。", "附件同步失败", "error"));
  });
  return draftSync;
}
const editMode = ref(false);
const globalStore = useGlobalStore();
const isSaveChangesModalVisible = ref(false);
const isDeleteModalVisible = ref(false);
const isDraftModalVisible = ref(false);
const isNewNote = computed(() => !props.title);
const loadingIndicator = ref();
const note = ref({});
const reservedFilenameCharacters = /[<>:"/\\|?*]/;
const router = useRouter();
const newTitle = ref();
const toast = useToast();
const toastEditor = ref();
const unsavedChanges = ref(false);

function init() {
  // Return if we already have the note e.g. When we rename a note, the route prop would change but we’d already have the note.
  if (props.title && props.title == note.value.title) {
    return;
  }

  draftId = null;
  settledUploads = [];
  // Keep failed explicit discards retryable instead of losing their draft IDs.
  for (const key of Object.keys(localStorage).filter(key => key.startsWith("flatnotes:attachment-cleanup:"))) {
    const id = key.slice("flatnotes:attachment-cleanup:".length);
    syncAttachmentDraft(id, "", [], true).then(() => localStorage.removeItem(key)).catch(() => {});
  }
  loadingIndicator.value.setLoading();
  if (props.title) {
    getNote(props.title)
      .then((data) => {
        note.value = data;
        loadingIndicator.value.setLoaded();
      })
      .catch((error) => {
        if (error.response?.status === 404) {
          loadingIndicator.value.setFailed("笔记不存在或已被删除", mdiNoteOffOutline);
        } else {
          loadingIndicator.value.setFailed();
          apiErrorHandler(error, toast);
        }
      });
  } else {
    newTitle.value = "";
    note.value = new Note();
    // Set the editMode to false to close any existing editors.
    // This ensures the editor is cleanly reinitialised in an empty state.
    // Simple fix for #266 without requiring a full re-work of the logic.
    editMode.value = false;
    nextTick(() => {
      editHandler();
      loadingIndicator.value.setLoaded();
    });
  }
}

// Note Editing
function toggleEditModeHandler() {
  if (editMode.value) {
    closeHandler();
  } else {
    editHandler();
  }
}

function editHandler() {
  const draftContent = loadDraft();
  if (draftContent) {
    isDraftModalVisible.value = true;
  } else {
    setEditMode();
  }
}

function setEditMode() {
  ensureDraftId();
  newTitle.value = note.value.title;
  unsavedChanges.value = false;
  editMode.value = true;
}

function getInitialEditorValue() {
  const draftContent = loadDraft();
  return draftContent ? draftContent : note.value.content;
}

// Note Deletion
function deleteHandler() {
  isDeleteModalVisible.value = true;
}

async function deleteConfirmedHandler() {
  await Promise.all([...uploads]);
  deleteNote(note.value.title)
    .then(() => {
      clearDraft();
      editMode.value = false;
      toast.add(getToastOptions("笔记已删除 ✓", "成功", "success"));
      router.push({ name: "home" });
    })
    .catch((error) => {
      apiErrorHandler(error, toast);
    });
}

// Note Saving
async function saveHandler(close = false) {
  await Promise.all([...uploads]);
  clearContentChangedTimeout();
  try { await saveDraft(); } catch { return; }
  // Save Default Editor Mode
  saveDefaultEditorMode();

  // Empty Title Validation
  if (!newTitle.value) {
    toast.add(
      getToastOptions("请先填写笔记标题。", "无法保存", "error"),
    );
    return;
  }

  // Invalid Character Validation
  if (reservedFilenameCharacters.test(newTitle.value)) {
    badFilenameToast("标题");
    return;
  }

  // Save Note
  let newContent = toastEditor.value.getMarkdown();
  if (isNewNote.value) {
    saveNew(newTitle.value, newContent, close);
  } else {
    saveExisting(newTitle.value, newContent, close);
  }
}

function saveNew(newTitle, newContent, close = false) {
  createNote(newTitle, newContent, ensureDraftId())
    .then((data) => {
      clearDraft(true);
      unsavedChanges.value = false;
      note.value = data;
      router
        .push({
          name: "note",
          params: { title: note.value.title },
        })
        .then(() => {
          // Wait for the route to be updated before setting edit mode to false
          // as the route is used to determine the action.
          noteSaveSuccess(close);
        });
    })
    .catch(noteSaveFailure);
}

function saveExisting(newTitle, newContent, close = false) {
  // Return if no changes
  if (newTitle == note.value.title && newContent == note.value.content) {
    clearDraft();
    noteSaveSuccess(close);
    return;
  }

  updateNote(note.value.title, newTitle, newContent, ensureDraftId())
    .then((data) => {
      clearDraft(true);
      unsavedChanges.value = false;
      note.value = data;
      router.replace({ name: "note", params: { title: note.value.title } });
      noteSaveSuccess(close);
    })
    .catch(noteSaveFailure);
}

function noteSaveFailure(error) {
  if (error.response?.status === 409) {
    toast.add(
      getToastOptions(
        "已有同名笔记，请修改标题后重试。",
        "名称重复",
        "error",
      ),
    );
  } else if (error.response?.status === 413) {
    entityTooLargeToast("笔记");
  } else {
    apiErrorHandler(error, toast);
  }
}

function noteSaveSuccess(close = false) {
  unsavedChanges.value = false;
  if (close) {
    closeNote();
  }
  setBeforeUnloadConfirmation(false);
  toast.add(getToastOptions("笔记已保存 ✓", "成功", "success"));
}

// Note Closure
function closeHandler() {
  if (isContentChanged()) {
    isSaveChangesModalVisible.value = true;
  } else {
    closeNote();
  }
}

async function closeNote() {
  await Promise.all([...uploads]);
  clearDraft();
  editMode.value = false;
  if (isNewNote.value) {
    router.push({ name: "home" });
  } else {
    editMode.value = false;
  }
}

// Image Upload
function addImageBlobHook(file, callback) {
  const altTextInputValue = document.getElementById(
    "toastuiAltTextInput",
  )?.value;

  // Upload the image then use the callback to insert the URL into the editor
  const upload = postAttachment(file)?.then(function (data) {
    if (data) {
      // If the user has entered an alt text, use it. Otherwise, use the filename returned by the API.
      const altText = altTextInputValue ? altTextInputValue : data.filename;
      callback(data.url, altText);
      settledUploads.push(data.filename);
      saveDraft();
    }
  });
  if (upload) {
    uploads.add(upload);
    upload.finally(() => uploads.delete(upload));
  }
}

function postAttachment(file) {
  // Invalid Character Validation
  if (reservedFilenameCharacters.test(file.name)) {
    badFilenameToast("标题");
    return;
  }

  // Uploading Toast
  toast.add(getToastOptions("正在上传附件…"));

  // Upload the attachment
  return createAttachment(file, ensureDraftId())
    .then((data) => {
      // Success Toast
      toast.add(
        getToastOptions(
          "附件已上传 ✓",
          "成功",
          "success",
        ),
      );
      return data;
    })
    .catch((error) => {
      if (error.response?.status === 409) {
        // Note: The current implementation will append a datetime to the filename if it already exists.
        // Error Toast
        toast.add(
          getToastOptions(
            "已有同名附件，请修改文件名后重试。",
            "名称重复",
            "error",
          ),
        );
      } else if (error.response?.status == 413) {
        entityTooLargeToast("附件");
      } else {
        apiErrorHandler(error, toast);
      }
    });
}

// Content Change Watcher
function startContentChangedTimeout() {
  clearContentChangedTimeout();
  contentChangedTimeout = setTimeout(contentChangedHandler, 1000);
}

function clearContentChangedTimeout() {
  if (contentChangedTimeout != null) {
    clearTimeout(contentChangedTimeout);
  }
}

function contentChangedHandler() {
  if (isContentChanged()) {
    unsavedChanges.value = true;
    setBeforeUnloadConfirmation(true);
    saveDraft();
  } else {
    unsavedChanges.value = false;
    setBeforeUnloadConfirmation(false);
    clearDraft();
  }
}

// Drafts
function saveDraft() {
  if (!toastEditor.value) return;
  const content = toastEditor.value.getMarkdown();
  // OIDC drafts survive closing the tab; explicit discard removes them.
  localStorage.setItem(note.value.title, content);
  sessionStorage.removeItem(note.value.title);
  return syncDraft(content);
}

function clearDraft(saved = false) {
  clearContentChangedTimeout();
  if (uploads.size && !saved) return;
  if (draftId || localStorage.getItem(draftKey())) {
    if (!saved) syncDraft("", true);
    localStorage.removeItem(draftKey());
  }
  localStorage.removeItem(note.value.title);
  sessionStorage.removeItem(note.value.title);
  draftId = null;
  settledUploads = [];
}

function preserveDraft() {
  clearContentChangedTimeout();
  if (!editMode.value || !toastEditor.value) return;
  if (isContentChanged()) return saveDraft();
  clearDraft();
  return draftSync;
}
async function leaveEditor() {
  await Promise.all([...uploads]);
  await preserveDraft();
  setBeforeUnloadConfirmation(false);
}
onBeforeRouteLeave(leaveEditor);
onBeforeRouteUpdate(async (to) => {
  // Saving/renaming has already committed this title and released its draft.
  if (to.params.title !== note.value.title) await leaveEditor();
});
function pageHideHandler() { preserveDraft(); }
onMounted(() => window.addEventListener("pagehide", pageHideHandler));
onBeforeUnmount(() => {
  clearContentChangedTimeout();
  setBeforeUnloadConfirmation(false);
  window.removeEventListener("pagehide", pageHideHandler);
});

function loadDraft() {
  const localDraft = localStorage.getItem(note.value.title);
  const sessionDraft = sessionStorage.getItem(note.value.title);
  return localDraft || sessionDraft;
}

// Keyboard Shortcuts
// 'e' to edit
Mousetrap.bind("e", () => {
  if (editMode.value === false && canModify.value) {
    editHandler();
  }
});

function keydownHandler(event) {
  // Ctrl + Enter to save
  if ((event.ctrlKey || event.metaKey) && event.key == "Enter") {
    saveHandler((close = false));
  }
  // Escape to exit edit mode
  if (event.key == "Escape") {
    closeHandler();
  }
}

// Helpers
function entityTooLargeToast(entityName) {
  toast.add(
    getToastOptions(
      `${entityName}超过大小限制，请缩小后重试。`,
      "操作失败",
      "error",
    ),
  );
}

function badFilenameToast(entityName) {
  toast.add(
    getToastOptions(
      '名称不能包含以下字符： <>:"/\\|?*',
      `${entityName}不符合要求`,
      "error",
    ),
  );
}

function setBeforeUnloadConfirmation(enable = true) {
  if (enable) {
    window.onbeforeunload = () => {
      return true;
    };
  } else {
    window.onbeforeunload = null;
  }
}

function saveDefaultEditorMode() {
  const isWysiwygMode = toastEditor.value.isWysiwygMode();
  localStorage.setItem(
    "defaultEditorMode",
    isWysiwygMode ? "wysiwyg" : "markdown",
  );
}

function loadDefaultEditorMode() {
  const defaultWysiwygMode = localStorage.getItem("defaultEditorMode");
  return defaultWysiwygMode || "markdown";
}

function isContentChanged() {
  return (
    newTitle.value != note.value.title ||
    toastEditor.value.getMarkdown() != note.value.content
  );
}

watch(() => props.title, init);
onMounted(init);
</script>
