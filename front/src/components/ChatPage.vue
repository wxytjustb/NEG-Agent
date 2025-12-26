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

    <!-- 工单确认弹窗 -->
    <div v-if="showTicketConfirmation" class="ticket-modal-overlay" @click.self="handleTicketReject">
      <div class="ticket-modal">
        <div class="ticket-modal-header">
          <h3>📝 维权工单确认</h3>
        </div>
        <div class="ticket-modal-body">
          <p class="ticket-reason">{{ ticketReason }}</p>
          <p class="ticket-question">是否需要我帮您创建维权工单？</p>
        </div>
        <div class="ticket-modal-footer">
          <button class="ticket-btn ticket-btn-cancel" @click="handleTicketReject">不用了</button>
          <button class="ticket-btn ticket-btn-confirm" @click="handleTicketConfirm">好的，创建工单</button>
        </div>
      </div>
    </div>

    <!-- 工单表单弹窗（用户确认后显示） -->
    <div v-if="showTicketForm" class="ticket-modal-overlay" @click.self="handleTicketFormCancel">
      <div class="ticket-modal ticket-form-modal">
        <div class="ticket-modal-header">
          <h3>📋 编辑工单信息</h3>
        </div>
        <div class="ticket-modal-body">
          <div class="form-group">
            <label class="form-label">问题描述：</label>
            <textarea 
              v-model="ticketFormData.content" 
              class="form-textarea" 
              rows="6" 
              placeholder="请描述您遇到的问题..."
            ></textarea>
          </div>
          <div class="form-group">
            <label class="form-label">联系方式：</label>
            <input 
              v-model="ticketFormData.contact" 
              type="text" 
              class="form-input" 
              placeholder="请输入您的电话或微信"
            />
          </div>
          <p class="form-hint">ℹ️ AI 已为您提取了问题描述，您可以进行修改</p>
        </div>
        <div class="ticket-modal-footer">
          <button class="ticket-btn ticket-btn-cancel" @click="handleTicketFormCancel">取消</button>
          <button class="ticket-btn ticket-btn-confirm" @click="handleTicketFormSubmit" :disabled="!canSubmitTicket">
            {{ isSubmittingTicket ? '提交中...' : '提交工单' }}
          </button>
        </div>
      </div>
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

// 工单确认弹窗相关状态
const showTicketConfirmation = ref(false);  // 是否显示确认弹窗
const ticketReason = ref('');  // 工单创建原因
const pendingUserInput = ref('');  // 待处理的用户输入

// 工单表单相关状态
const showTicketForm = ref(false);  // 是否显示表单弹窗
const isSubmittingTicket = ref(false);  // 是否正在提交工单
const ticketFormData = ref({
  content: '',  // 问题描述
  contact: '',  // 联系方式
  images: [] as string[]  // 图片列表
});

// 是否可以提交工单
const canSubmitTicket = computed(() => {
  return ticketFormData.value.content.trim().length > 0 && !isSubmittingTicket.value;
});

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

// 工单确认处理
const handleTicketConfirm = () => {
  console.log('[Ticket] 用户确认创建工单');
  showTicketConfirmation.value = false;
  
  // 直接显示工单表单，让用户填写详细信息
  ticketFormData.value = {
    content: ticketReason.value,  // 使用 AI 分析的理由作为初始内容
    contact: '',  // 用户手动填写联系方式
    images: []
  };
  
  // 显示表单弹窗
  showTicketForm.value = true;
  
  pendingUserInput.value = '';
  ticketReason.value = '';
};

const handleTicketReject = () => {
  console.log('[Ticket] 用户拒绝创建工单');
  showTicketConfirmation.value = false;
  pendingUserInput.value = '';
  ticketReason.value = '';
};

// 工单表单处理
const handleTicketFormCancel = () => {
  console.log('[TicketForm] 用户取消编辑');
  showTicketForm.value = false;
  ticketFormData.value = {
    content: '',
    contact: '',
    images: []
  };
};

const handleTicketFormSubmit = async () => {
  if (!canSubmitTicket.value) return;
  
  try {
    isSubmittingTicket.value = true;
    console.log('[TicketForm] 开始提交工单:', ticketFormData.value);
    
    // 获取 access_token
    const accessToken = localStorage.getItem('access_token');
    if (!accessToken) {
      throw new Error('未找到用户认证信息');
    }
    
    // 直接调用 Golang 接口（使用 x-token 请求头）
    const response = await fetch('https://app-api.roky.work/app/help/postHelpRequest', {
      method: 'POST',
      headers: {
        'x-token': accessToken,  // 使用 x-token 而不是 Authorization
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(ticketFormData.value)
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const result = await response.json();
    console.log('[TicketForm] 工单创建结果:', result);
    
    if (result.code === 200 || result.code === 0) {
      // 成功
      messages.value.push({
        role: 'assistant',
        content: `✅ 工单创建成功！工单编号：${result.data?.id || '未知'}`
      });
      showTicketForm.value = false;
      ticketFormData.value = {
        content: '',
        contact: '',
        images: []
      };
    } else {
      // 失败
      messages.value.push({
        role: 'assistant',
        content: `❌ 工单创建失败：${result.msg || '未知错误'}`
      });
    }
    
    scrollToBottom();
    
  } catch (error: any) {
    console.error('[TicketForm] 提交失败:', error);
    messages.value.push({
      role: 'assistant',
      content: `❌ 工单提交失败：${error.message}`
    });
    scrollToBottom();
  } finally {
    isSubmittingTicket.value = false;
  }
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
const handleWorkflowSend = async (userMessage: string, additionalState: any = {}) => {
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
    
    // 构建请求体，支持额外的 state 传递
    const requestBody: any = {
      user_input: userMessage
    };
    
    // 如果有额外的 state，合并到请求体
    if (Object.keys(additionalState).length > 0) {
      Object.assign(requestBody, additionalState);
      console.log('[Workflow] 携带额外 state:', additionalState);
    }
    
    const response = await fetch(urlWithToken, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody)
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) {
      throw new Error('无法获取响应流');
    }

    let buffer = ''; // 缓存不完整的 SSE 消息
    let workflowState: any = {}; // 存储工作流状态

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      buffer += chunk;
      
      // 处理 SSE 格式的数据 - SSE 使用双换行符分隔消息
      const messages_sse = buffer.split('\n\n');
      buffer = messages_sse.pop() || ''; // 保留最后一个可能不完整的消息

      for (const message of messages_sse) {
        // 每个消息可能包含多行，我们只处理 data: 开头的行
        const lines = message.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const content = line.substring(6);
            console.log('[Workflow] 收到 SSE 数据:', content);
            
            if (content === '[DONE]') {
              console.log('[Workflow] ✅ 流式传输完成');
            } else if (content.startsWith('[ERROR]')) {
              console.log('[Workflow] ❌ 收到错误:', content);
              const msg = messages.value[assistantMessageIndex];
              if (msg) {
                msg.content = `错误: ${content}`;
              }
            } else if (content.startsWith('[STATE]')) {
              // 处理状态数据
              try {
                const stateData = JSON.parse(content.substring(7));
                workflowState = { ...workflowState, ...stateData };
                console.log('[Workflow] 收到 State 更新:', stateData);
              } catch (e) {
                console.error('[Workflow] State 解析失败:', e);
              }
            } else if (content.trim()) {
              // 正常的内容数据
              const msg = messages.value[assistantMessageIndex];
              if (msg) {
                msg.content += content;
              }
              scrollToBottom();
            }
          }
        }
      }
    }
    
    console.log('[Workflow] 对话完成');
    
    // 检查是否需要显示工单确认弹窗
    if (workflowState.need_create_ticket === true && !additionalState.user_confirmed_ticket) {
      console.log('[Ticket] 检测到需要创建工单，显示确认弹窗');
      ticketReason.value = workflowState.ticket_reason || '检测到您可能需要维权帮助。';
      pendingUserInput.value = userMessage;
      showTicketConfirmation.value = true;
    }
    
    // 删除：不再需要这个逻辑，因为现在前端直接显示表单
    // if (workflowState.ticket_content && additionalState.user_confirmed_ticket) {
    //   ...
    // }
    
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

/* 工单确认弹窗 */
.ticket-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.ticket-modal {
  background: #fff;
  border-radius: 16px;
  width: 90%;
  max-width: 400px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  animation: slideUp 0.3s ease-out;
}

@keyframes slideUp {
  from {
    transform: translateY(20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.ticket-modal-header {
  padding: 20px 24px;
  border-bottom: 1px solid #f0f0f0;
}

.ticket-modal-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.ticket-modal-body {
  padding: 24px;
}

.ticket-reason {
  margin: 0 0 16px 0;
  padding: 12px 16px;
  background: #f5f5f5;
  border-left: 3px solid #07c160;
  border-radius: 4px;
  font-size: 14px;
  line-height: 1.6;
  color: #555;
}

.ticket-question {
  margin: 0;
  font-size: 15px;
  font-weight: 500;
  color: #333;
}

.ticket-modal-footer {
  padding: 16px 24px;
  display: flex;
  gap: 12px;
  border-top: 1px solid #f0f0f0;
}

.ticket-btn {
  flex: 1;
  height: 44px;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.ticket-btn-cancel {
  background: #f5f5f5;
  color: #666;
}

.ticket-btn-cancel:hover {
  background: #e5e5e5;
}

.ticket-btn-confirm {
  background: #07c160;
  color: #fff;
}

.ticket-btn-confirm:hover {
  background: #06ad56;
}

.ticket-btn-confirm:disabled {
  background: #c9c9c9;
  cursor: not-allowed;
}

/* 工单表单样式 */
.ticket-form-modal {
  max-width: 500px;
}

.form-group {
  margin-bottom: 20px;
}

.form-label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.form-textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
  min-height: 120px;
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.form-textarea:focus {
  border-color: #07c160;
}

.form-input {
  width: 100%;
  padding: 12px;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.form-input:focus {
  border-color: #07c160;
}

.form-hint {
  margin: 16px 0 0 0;
  padding: 10px 12px;
  background: #e8f5e9;
  border-radius: 6px;
  font-size: 13px;
  color: #4caf50;
  line-height: 1.5;
}
</style>