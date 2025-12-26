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
    </div>

    <!-- 消息列表 -->
    <div class="chat-messages" ref="messagesContainer">
      <div
        v-for="(msg, index) in messages"
        :key="index"
        class="message-wrapper"
        :class="msg.role === 'user' ? 'message-user' : msg.role === 'divider' ? '' : 'message-assistant'"
      >
        <!-- 分隔线 -->
        <div v-if="msg.role === 'divider'" class="history-divider">
          <span class="divider-text">{{ msg.content }}</span>
        </div>
        <!-- 正常消息 -->
        <div v-else class="message-bubble" :class="msg.role">
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
import { initSession, getSessionHistory } from '../api/agent';

// 消息类型（扩展支持分隔线）
interface ChatMessage {
  role: 'user' | 'assistant' | 'system' | 'divider';
  content: string;
}

// Session token management
const sessionToken = ref<string>('');
const isInitializing = ref(false);

const title = ref('AI 助手');
const provider = ref<'deepseek'>('deepseek');  // 固定为 deepseek
const inputText = ref('');
const isLoading = ref(false);
const messagesContainer = ref<HTMLElement | null>(null);

// 消息列表（初始显示欢迎消息）
const messages = ref<ChatMessage[]>([
  {
    role: 'assistant',
    content: '你好，我是安然，你的心理陪伴者。我在这里倾听你的心声，如果你在工作中遇到困扰或不公，随时可以跟我说。'
  }
]);

// 是否可以发送
const canSend = computed(() => {
  return inputText.value.trim().length > 0 && !isLoading.value && sessionToken.value !== '';
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



// 发送消息（统一使用 Workflow 接口）
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

  // 统一使用 Workflow API
  await handleWorkflowSend(userMessage);
};

// Workflow 流式发送
const handleWorkflowSend = async (userMessage: string) => {
  // 添加助手消息占位符
  const assistantMessageIndex = messages.value.length;
  messages.value.push({
    role: 'assistant',
    content: ''
  });

  isLoading.value = true;
  scrollToBottom();

  try {
    console.log('[Workflow] 调用 /api/agent/chat 流式接口...');
    
    const urlWithToken = `http://localhost:8000/api/agent/chat?session_token=${sessionToken.value}`;
    
    const response = await fetch(urlWithToken, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_input: userMessage
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) {
      throw new Error('无法获取响应流');
    }

    let buffer = ''; // 缓存不完整的 JSON

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      buffer += chunk;
      
      // 按行切分 JSON
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // 保留最后一个不完整的行

      for (const line of lines) {
        if (!line.trim()) continue; // 跳过空行
        
        console.log('[Workflow] 收到 JSON 行:', line); // 打印每个 JSON 行
        
        try {
          const jsonData = JSON.parse(line);
          console.log('[Workflow] 解析后的数据:', jsonData); // 打印解析后的对象
          
          if (jsonData.type === 'token') {
            console.log('[Workflow] 收到 token:', jsonData.content); // 打印每个 token
            // 正常的 token 数据
            const msg = messages.value[assistantMessageIndex];
            if (msg) {
              msg.content += jsonData.content;
            }
            scrollToBottom();
          } else if (jsonData.type === 'done') {
            console.log('[Workflow] ✅ 流式传输完成');
          } else if (jsonData.type === 'error') {
            console.log('[Workflow] ❌ 收到错误:', jsonData.message);
            const msg = messages.value[assistantMessageIndex];
            if (msg) {
              msg.content = `错误: ${jsonData.message}`;
            }
          }
        } catch (parseError) {
          console.warn('[Workflow] JSON 解析错误:', line, parseError);
        }
      }
    }
    
    console.log('[Workflow] 对话完成');
    
  } catch (error: any) {
    console.error('[Workflow] 错误:', error);
    const msg = messages.value[assistantMessageIndex];
    if (msg) {
      msg.content = `发送失败: ${error.message}`;
    }
  } finally {
    isLoading.value = false;
    scrollToBottom();
  }
};

// 加载对话历史（统一使用 ChromaDB）
const loadChatHistory = async () => {
  if (!sessionToken.value) {
    console.error('[History] 无法加载历史：session_token 为空');
    return;
  }

  try {
    console.log('[History] 开始加载对话历史（ChromaDB）...');
    
    // 使用 sessionToken 作为 session_id
    const response = await getSessionHistory(sessionToken.value, sessionToken.value);
    
    if (response.total_count > 0) {
      // 构建完整消息列表：历史消息 + 分隔线 + 欢迎消息
      const historyMessages = response.messages.map(msg => ({
        role: msg.role,
        content: msg.content
      }));
      
      messages.value = [
        ...historyMessages,  // 历史对话
        {
          role: 'divider',
          content: '以上是历史对话'
        },
        {
          role: 'assistant',
          content: '你好，我是安然，你的心理陪伴者。我在这里倾听你的心声，如果你在工作中遇到困扰或不公，随时可以跟我说。'
        }
      ];
      console.log('[History] ✅ ChromaDB历史加载成功，消息数:', response.total_count);
    } else {
      // 无历史记录，只显示欢迎消息
      messages.value = [
        {
          role: 'assistant',
          content: '你好，我是安然，你的心理陪伴者。我在这里倾听你的心声，如果你在工作中遇到困扰或不公，随时可以跟我说。'
        }
      ];
      console.log('[History] ✅ 无历史记录，显示欢迎消息');
    }
    
    scrollToBottom();
  } catch (error: any) {
    console.error('[History] ChromaDB历史加载失败:', error);
    // 失败时显示默认欢迎消息
    messages.value = [
      {
        role: 'assistant',
        content: '你好，我是安然，你的心理陪伴者。我在这里倾听你的心声，如果你在工作中遇到困扰或不公，随时可以跟我说。'
      }
    ];
  }
};

// 初始化会话
const initializeSession = async () => {
  try {
    isInitializing.value = true;

    // 1. 从 URL 获取 access_token
    const urlParams = new URLSearchParams(window.location.search);
    const ACCESS_TOKEN = urlParams.get('access_token');

    if (!ACCESS_TOKEN) {
      console.error('[Session] 未找到 access_token');
      alert('未找到用户认证信息\n请通过 URL 参数传递 token:\nhttp://localhost:5173/?access_token=your_token');
      return;
    }

    // 2. 检查缓存的 session 是否属于当前 access_token
    const cachedAccessToken = localStorage.getItem('access_token');

    if (cachedAccessToken === ACCESS_TOKEN) {
      // access_token 没变，使用缓存的 session_token
      // 注意：如果 Redis 中的 session 已过期，会在发送消息时检测到 401 错误并清除缓存
      const cachedSessionToken = localStorage.getItem('session_token');
      if (cachedSessionToken) {
        sessionToken.value = cachedSessionToken;
        console.log('[Session] ✅ 使用缓存的 session_token:', cachedSessionToken.substring(0, 20) + '...');
        return;
      }
    } else {
      // access_token 变了，清除旧缓存
      if (cachedAccessToken) {
        console.log('[Session] ⚠️ 检测到 access_token 变化，清除旧会话缓存');
        localStorage.removeItem('session_token');
        localStorage.removeItem('access_token');
      }
    }

    // 3. 调用初始化接口（后端会自动复用现有 session）
    console.log('[Session] 正在初始化会话...');
    const response = await initSession(ACCESS_TOKEN);

    if (response.code === 200) {
      sessionToken.value = response.data.session_token;
      // 保存 session_token 和 access_token
      localStorage.setItem('session_token', response.data.session_token);
      localStorage.setItem('access_token', ACCESS_TOKEN);
      console.log('[Session] ✅ 会话初始化成功:', sessionToken.value.substring(0, 20) + '...');
    } else {
      console.error('[Session] 会话初始化失败:', response);
      const errorMsg = response.msg || '会话初始化失败';
      alert(`❌ ${errorMsg}\n\n请检查 access_token 是否有效`);
    }
  } catch (error: any) {
    console.error('[Session] 初始化错误:', error);
    const errorMsg = error.message || '会话初始化失败';
    alert(`❌ ${errorMsg}

请检查:
1. access_token 是否有效
2. 网络连接是否正常
3. 后端服务是否运行`);
  } finally {
    isInitializing.value = false;
  }
};

onMounted(async () => {
  console.log('[ChatPage] 💬 组件加载 - 这是普通对话页面！');
  await initializeSession();
  // 初始化完成后加载历史
  await loadChatHistory();
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
  flex: 1;
  text-align: center;
}

.header-spacer {
  width: 40px;  /* 与返回按钮同宽，实现居中对称 */
}

.test-btn {
  min-width: 80px;
  height: 32px;
  padding: 0 16px;
  border: 1px solid #07c160;
  background: transparent;
  color: #07c160;
  font-size: 14px;
  font-weight: 600;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.test-btn.active {
  background: #07c160;
  color: #fff;
  border-color: #07c160;
}

.test-btn:hover:not(:disabled):not(.active) {
  background: #f0f9f4;
}

.test-btn:disabled {
  border-color: #c9c9c9;
  color: #c9c9c9;
  cursor: not-allowed;
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

/* 历史分隔线 */
.history-divider {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 20px 0;
  position: relative;
}

.history-divider::before,
.history-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: linear-gradient(to right, transparent, #d0d0d0, transparent);
}

.divider-text {
  padding: 0 16px;
  color: #999;
  font-size: 12px;
  white-space: nowrap;
}
</style>