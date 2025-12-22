<template>
  <component :is="currentPage" />
</template>

<script setup>
import { ref } from 'vue';
import ChatPage from './components/ChatPage.vue';

const currentPage = ref(ChatPage);
</script>
