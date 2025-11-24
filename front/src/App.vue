<template>
  <div>
    <h1>前端页面</h1>
    <p>后端返回：{{ backendMessage }}</p>

    <button @click="callBackend">点击测试连接后端</button>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { get } from "./utls/require";

const backendMessage = ref("（未连接）");

const callBackend = async () => {
  try {
    const data = await get("/ping");
    backendMessage.value = data.message;
  } catch (error) {
    backendMessage.value = "连接失败: " + error.message;
  }
};
</script>
