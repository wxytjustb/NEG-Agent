<template>
  <component :is="currentPage" />
</template>

<script setup>
import { ref, onMounted } from 'vue';
import ChatPage from './components/ChatPage.vue';
import LangGraphChatPage from './components/LangGraphChatPage.vue';

const currentPage = ref(ChatPage);

// 根据 URL 路径决定显示哪个组件
onMounted(() => {
  const path = window.location.pathname;
  console.log('[App] 当前路径:', path);
  if (path === '/langgraph') {
    console.log('[App] ✅ 加载 LangGraphChatPage');
    currentPage.value = LangGraphChatPage;
  } else {
    console.log('[App] ✅ 加载 ChatPage');
    currentPage.value = ChatPage;
  }
});
</script>
