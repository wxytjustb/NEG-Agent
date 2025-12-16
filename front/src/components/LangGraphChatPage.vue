<template>
  <div class="chat-container">
    <!-- 头部 -->
    <div class="chat-header">
      <button class="back-btn" @click="goBack">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <path d="M15 18L9 12L15 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
      <h1 class="chat-title">{{ title }} <span class="workflow-badge">工作流</span></h1>
      <div class="switch-mode">
        <button class="mode-btn" @click="switchToNormalChat">切换到普通对话</button>
      </div>
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
          <div v-else>
            <!-- 用户意图标签 -->
            <div v-if="msg.intent" class="intent-tag">
              🎯 {{ msg.intent }}
            </div>
            <div class="message-text">{{ msg.content }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 输入框 -->
    <div class="chat-input-wrapper">
      <textarea
        v-model="inputText"
        class="chat-input"
        placeholder="发送消息（工作流模式）..."
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
        {{ isLoading ? '处理中...' : '发送' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted } from 'vue';
import { initSession, getChatHistory } from '../api/agent';

// 消息类型（扩展支持意图）
interface ChatMessage {
  role: 'user' | 'assistant' | 'system' | 'divider';
  content: string;
  intent?: string;  // AI 分析的用户意图
}

// Session token management
const sessionToken = ref<string>('');
const isInitializing = ref(false);

const title = ref('AI 助手');
const inputText = ref('');
const isLoading = ref(false);
const messagesContainer = ref<HTMLElement | null>(null);

// 消息列表（默认为空，由历史接口加载）
const messages = ref<ChatMessage[]>([]);

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

// 切换到普通对话
const switchToNormalChat = () => {
  const urlParams = new URLSearchParams(window.location.search);
  const accessToken = urlParams.get('access_token');
  if (accessToken) {
    window.location.href = `/?access_token=${accessToken}`;
  } else {
    window.location.href = '/';
  }
};

// 发送消息（使用工作流流式）
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

  // 添加助手消息占位符
  const assistantMessageIndex = messages.value.length;
  messages.value.push({
    role: 'assistant',
    content: '',
    intent: ''  // 用户意图
  });

  isLoading.value = true;
  scrollToBottom();

  try {
    console.log('[WorkflowChat] 开始发送消息（流式）...');
    
    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
    const response = await fetch(
      `${API_BASE_URL}/api/workflow/chat?session_token=${sessionToken.value}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: userMessage }),
      }
    );

    if (!response.ok) {
      if (response.status === 401) {
        console.warn('[WorkflowChat] Session 已过期，清除本地缓存');
        localStorage.removeItem('session_token');
        localStorage.removeItem('access_token');
        throw new Error('会话已过期，请刷新页面重新登录');
      }
      throw new Error(`请求失败: ${response.status}`);
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder('utf-8');

    if (!reader) {
      throw new Error('无法获取响应流');
    }

    let buffer = '';
    let intentReceived = false;  // 标记是否已收到意图

    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        console.log('[WorkflowStream] 读取完成');
        break;
      }

      // 解码数据块
      const chunk = decoder.decode(value, { stream: true });
      buffer += chunk;
      console.log('[WorkflowStream] 收到数据块:', chunk);

      // 处理SSE格式的数据
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const content = line.substring(6);
          console.log('[WorkflowStream] 解析数据:', content);

          if (content === '[DONE]') {
            console.log('[WorkflowStream] 收到结束标记');
            isLoading.value = false;
            scrollToBottom();
            return;
          } else if (content.startsWith('[ERROR]')) {
            console.error('[WorkflowStream] 收到错误:', content);
            const msg = messages.value[assistantMessageIndex];
            if (msg) {
              msg.content = content;
            }
            isLoading.value = false;
            scrollToBottom();
            return;
          } else if (content.startsWith('intent:')) {
            // 提取意图
            const intent = content.substring(7);
            console.log('[WorkflowStream] 收到意图:', intent);
            const msg = messages.value[assistantMessageIndex];
            if (msg) {
              msg.intent = intent;
            }
            intentReceived = true;
            scrollToBottom();
          } else if (content) {
            // 正常内容
            const msg = messages.value[assistantMessageIndex];
            if (msg) {
              msg.content += content;
            }
            scrollToBottom();
          }
        }
      }
    }

    console.log('[WorkflowStream] 流结束');
    isLoading.value = false;
    scrollToBottom();

  } catch (error: any) {
    console.error('[WorkflowChat] 发送失败:', error);
    
    const msg = messages.value[assistantMessageIndex];
    if (msg) {
      if (error.message && error.message.includes('会话已过期')) {
        msg.content = `⚠️ 会话已过期，请刷新页面重新登录`;
        sessionToken.value = '';
      } else {
        msg.content = `❌ 发送失败: ${error.message || error}`;
      }
    }
    
    isLoading.value = false;
    scrollToBottom();
  }
};

// 加载对话历史
const loadChatHistory = async () => {
  if (!sessionToken.value) {
    console.error('[History] 无法加载历史：session_token 为空');
    return;
  }

  try {
    console.log('[History] 开始加载对话历史...');
    const response = await getChatHistory(sessionToken.value);
    
    if (response.code === 200) {
      const historyMessages = response.data.messages;
      
      // 如果有历史记录（不是新用户）
      if (!response.data.is_new_user && historyMessages.length > 0) {
        // 构建完整消息列表：历史消息 + 分隔线 + 欢迎消息
        messages.value = [
          ...historyMessages.map(msg => ({
            role: msg.role,
            content: msg.content
          })),
          {
            role: 'divider',
            content: '以上是历史对话'
          },
          {
            role: 'assistant',
            content: '你好，我是AI助手（工作流模式），我会先分析你的意图，再给出专业的回复。'
          }
        ];
        console.log('[History] ✅ 历史加载成功，消息数:', historyMessages.length);
      } else {
        // 新用户，只显示欢迎消息
        messages.value = [
          {
            role: 'assistant',
            content: '你好，我是AI助手（工作流模式），我会先分析你的意图，再给出专业的回复。'
          }
        ];
        console.log('[History] ✅ 新用户，显示欢迎消息');
      }
      
      scrollToBottom();
    } else {
      console.error('[History] 加载失败:', response.msg);
      messages.value = [
        {
          role: 'assistant',
          content: '你好，我是AI助手（工作流模式），我会先分析你的意图，再给出专业的回复。'
        }
      ];
    }
  } catch (error) {
    console.error('[History] 加载错误:', error);
    messages.value = [
      {
        role: 'assistant',
        content: '你好，我是AI助手（工作流模式），我会先分析你的意图，再给出专业的回复。'
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
      alert('未找到用户认证信息\n请通过 URL 参数传递 token:\nhttp://localhost:5173/langgraph?access_token=your_token');
      return;
    }

    // 2. 检查缓存的 session 是否属于当前 access_token
    const cachedAccessToken = localStorage.getItem('access_token');

    if (cachedAccessToken === ACCESS_TOKEN) {
      const cachedSessionToken = localStorage.getItem('session_token');
      if (cachedSessionToken) {
        sessionToken.value = cachedSessionToken;
        console.log('[Session] ✅ 使用缓存的 session_token');
        return;
      }
    } else {
      if (cachedAccessToken) {
        console.log('[Session] ⚠️ 检测到 access_token 变化，清除旧会话缓存');
        localStorage.removeItem('session_token');
        localStorage.removeItem('access_token');
      }
    }

    // 3. 调用初始化接口
    console.log('[Session] 正在初始化会话...');
    const response = await initSession(ACCESS_TOKEN);

    if (response.code === 200) {
      sessionToken.value = response.data.session_token;
      localStorage.setItem('session_token', response.data.session_token);
      localStorage.setItem('access_token', ACCESS_TOKEN);
      console.log('[Session] ✅ 会话初始化成功');
    } else {
      console.error('[Session] 会话初始化失败:', response);
      alert(`❌ ${response.msg || '会话初始化失败'}\n\n请检查 access_token 是否有效`);
    }
  } catch (error: any) {
    console.error('[Session] 初始化错误:', error);
    alert(`❌ ${error.message || '会话初始化失败'}\n\n请检查网络连接和后端服务`);
  } finally {
    isInitializing.value = false;
  }
};

onMounted(async () => {
  console.log('[LangGraphChatPage] 🚀 组件加载 - 这是工作流页面！');
  await initializeSession();
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
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  height: 56px;
}

.back-btn {
  width: 40px;
  height: 40px;
  border: none;
  background: rgba(255, 255, 255, 0.2);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  transition: background 0.2s;
  color: #fff;
}

.back-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

.chat-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  color: #fff;
  display: flex;
  align-items: center;
  gap: 8px;
}

.workflow-badge {
  font-size: 12px;
  padding: 2px 8px;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 4px;
  font-weight: 500;
}

.switch-mode {
  display: flex;
  align-items: center;
}

.mode-btn {
  padding: 6px 12px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  background: rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  cursor: pointer;
  font-size: 12px;
  color: #fff;
  transition: background 0.2s;
}

.mode-btn:hover {
  background: rgba(255, 255, 255, 0.3);
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
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
  word-wrap: break-word;
  position: relative;
}

.message-bubble.user {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  border-bottom-right-radius: 4px;
}

.message-bubble.assistant {
  background: #fff;
  color: #000;
  border: 1px solid #e5e5e5;
  border-bottom-left-radius: 4px;
}

/* 意图标签 */
.intent-tag {
  display: inline-block;
  padding: 4px 10px;
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: #fff;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  margin-bottom: 8px;
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
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
  border: 2px solid #e5e5e5;
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
  border-color: #667eea;
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
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
}

.send-btn:hover:not(.disabled) {
  opacity: 0.9;
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
