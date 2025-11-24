<template>
  <div class="chat-container">
    <!-- 头部 -->
    <div class="chat-header">
      <button class="back-btn" @click="goBack">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <path d="M15 18L9 12L15 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
      <h1 class="chat-title">{{ title }}</h1>
      <div class="provider-toggle">
        <button class="provider-btn" @click="toggleProvider">{{ currentProviderLabel }}</button>
      </div>
    </div>

    <!-- 消息列表 -->
    <div class="chat-messages" ref="messagesContainer">
      <div 
        v-for="(msg, index) in messages" 
        :key="index" 
        class="message-wrapper"
        :class="msg.role === 'user' ? 'message-user' : 'message-assistant'"
      >
        <div class="message-bubble" :class="msg.role">
          <!-- 加载动画 -->
          <div v-if="isLoading && msg.role === 'assistant' && index === messages.length - 1 && !msg.content" class="typing-indicator">
            <span class="dot"></span>
            <span class="dot"></span>
            <span class="dot"></span>
          </div>
          <!-- 消息内容 -->
          <div v-else class="message-text">{{ msg.content }}</div>
        </div>
      </div>
    </div>

    <!-- 输入框 -->
    <div class="chat-input-wrapper">
      <textarea
        v-model="inputText"
        class="chat-input"
        placeholder="发送消息..."
        rows="1"
        @keydown.enter.exact.prevent="handleSend"
        :disabled="isLoading"
      ></textarea>
      <button 
        class="send-btn" 
        :class="{ disabled: !canSend }"
        :disabled="!canSend"
        @click="handleSend"
      >
        {{ isLoading ? '发送中...' : '发送' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted } from 'vue';
import { chatStream, type ChatMessage } from '../api/agent';

const title = ref('AI 助手');
const provider = ref<'ollama' | 'deepseek'>('ollama');
const currentProviderLabel = computed(() => provider.value === 'ollama' ? 'Ollama' : 'DeepSeek');
const toggleProvider = () => {
  provider.value = provider.value === 'ollama' ? 'deepseek' : 'ollama';
};
const inputText = ref('');
const isLoading = ref(false);
const messagesContainer = ref<HTMLElement | null>(null);

// 消息列表
const messages = ref<ChatMessage[]>([
  {
    role: 'assistant',
    content: '你好，我是AI助手，有什么我可以帮助你的吗？'
  }
]);

// 是否可以发送
const canSend = computed(() => {
  return inputText.value.trim().length > 0 && !isLoading.value;
});

// 滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
    }
  });
};

// 返回
const goBack = () => {
  window.history.back();
};

// 发送消息
const handleSend = async () => {
  if (!canSend.value) return;

  const userMessage = inputText.value.trim();
  inputText.value = '';

  // 添加用户消息
  messages.value.push({
    role: 'user',
    content: userMessage
  });

  scrollToBottom();

  // 添加助手消息占位符（使用数组索引来确保响应式）
  const assistantMessageIndex = messages.value.length;
  messages.value.push({
    role: 'assistant',
    content: ''
  });
  
  isLoading.value = true;
  scrollToBottom();

  try {
    // 构建聊天历史（排除当前正在构建的助手消息）
    const chatHistory = messages.value
      .slice(0, -1)
      .filter(msg => msg.role !== 'system');

    // 调用流式接口
    console.log('[Chat] 开始发送消息，历史消息数:', chatHistory.length);
    await chatStream(
      {
        messages: chatHistory,
        provider: provider.value,
        temperature: 0.7,
        max_tokens: 2000,
        stream: true
      },
      // onMessage - 接收流式数据
      (chunk: string) => {
        console.log('[Chat] 收到chunk:', chunk);
        // 使用索引访问并更新，触发响应式更新
        const msg = messages.value[assistantMessageIndex];
        if (msg) {
          msg.content += chunk;
        }
        scrollToBottom();
      },
      // onError - 错误处理
      (error: Error) => {
        console.error('[Chat] 错误:', error);
        const msg = messages.value[assistantMessageIndex];
        if (msg) {
          msg.content = `错误: ${error.message}`;
        }
        isLoading.value = false;
        scrollToBottom();
      },
      // onComplete - 完成回调
      () => {
        const msg = messages.value[assistantMessageIndex];
        console.log('[Chat] 流式传输完成，收到内容:', msg?.content);
        if (msg && !msg.content.trim()) {
          msg.content = '(无响应)';
        }
        isLoading.value = false;
        scrollToBottom();
      }
    );
  } catch (error) {
    console.error('Send message error:', error);
    const msg = messages.value[assistantMessageIndex];
    if (msg) {
      msg.content = `发送失败: ${error}`;
    }
    isLoading.value = false;
    scrollToBottom();
  }
};

onMounted(() => {
  scrollToBottom();
});
</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100vw;
  background: #f5f5f5;
  margin: 0;
  padding: 0;
}

/* 头部 */
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #fff;
  border-bottom: 1px solid #e5e5e5;
  height: 56px;
}

.back-btn {
  width: 40px;
  height: 40px;
  border: none;
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  transition: background 0.2s;
}

.back-btn:hover {
  background: #f0f0f0;
}

.chat-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  color: #333;
}

.provider-toggle {
  display: flex;
  align-items: center;
}

.provider-btn {
  padding: 6px 10px;
  border: 1px solid #e5e5e5;
  background: #fff;
  border-radius: 8px;
  cursor: pointer;
  font-size: 12px;
}

.provider-btn:hover {
  background: #f0f0f0;
}

/* 消息列表 */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.message-wrapper {
  display: flex;
  width: 100%;
}

.message-user {
  justify-content: flex-end;
}

.message-assistant {
  justify-content: flex-start;
}

.message-bubble {
  max-width: 50%;
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
  word-wrap: break-word;
  position: relative;
}

.message-bubble.user {
  background: #95ec69;
  color: #000;
  border-bottom-right-radius: 4px;
}

.message-bubble.assistant {
  background: #fff;
  color: #000;
  border: 1px solid #e5e5e5;
  border-bottom-left-radius: 4px;
}

.message-text {
  white-space: pre-wrap;
  text-align: left;
}

/* 加载动画 */
.typing-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 0;
}

.typing-indicator .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #bbb;
  animation: typing-blink 1.4s infinite;
}

.typing-indicator .dot:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator .dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing-blink {
  0%, 60%, 100% {
    opacity: 0.3;
    transform: scale(0.9);
  }
  30% {
    opacity: 1;
    transform: scale(1);
  }
}

/* 输入框 */
.chat-input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 12px 16px;
  background: #fff;
  border-top: 1px solid #e5e5e5;
}

.chat-input {
  flex: 1;
  min-height: 40px;
  max-height: 120px;
  padding: 10px 12px;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  font-size: 14px;
  resize: none;
  font-family: inherit;
  outline: none;
  transition: border-color 0.2s;
  background: #f5f5f5;
  color: #000;
}

.chat-input:focus {
  border-color: #07c160;
}

.chat-input:disabled {
  background: #f5f5f5;
  cursor: not-allowed;
}

.send-btn {
  min-width: 80px;
  height: 40px;
  padding: 0 20px;
  border: none;
  border-radius: 8px;
  background: #07c160;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.send-btn:hover:not(.disabled) {
  background: #06ad56;
}

.send-btn.disabled {
  background: #c9c9c9;
  cursor: not-allowed;
}

/* 滚动条样式 */
.chat-messages::-webkit-scrollbar {
  width: 6px;
}

.chat-messages::-webkit-scrollbar-track {
  background: transparent;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: #ccc;
  border-radius: 3px;
}

.chat-messages::-webkit-scrollbar-thumb:hover {
  background: #999;
}
</style>