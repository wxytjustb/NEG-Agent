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
      <div class="header-actions">
        <button class="history-btn" @click="toggleHistoryList" title="历史记录">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M12 8V12L15 15M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
        <button class="new-chat-btn" @click="startNewChat" title="新对话">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M12 5V19M5 12H19" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- 消息列表 -->
    <div class="chat-messages" ref="messagesContainer" v-show="!showHistoryList">
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
        <div v-else>
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
          
          <!-- 反馈按钮（仅AI回复显示） -->
          <div v-if="msg.role === 'assistant' && msg.content && !isLoading && !msg.isWelcome" class="feedback-buttons">
            <button 
              class="feedback-btn"
              :class="{ active: msg.feedbackStatus === 'useful' }"
              @click="handleFeedback(index, true)"
              :disabled="msg.feedbackStatus !== 'none' && msg.feedbackStatus !== undefined"
              title="有用"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M7 22V11M2 13V20C2 21.1046 2.89543 22 4 22H17.4262C18.907 22 20.1662 20.9197 20.3914 19.4562L21.4683 12.4562C21.7479 10.6389 20.3418 9 18.5032 9H15C14.4477 9 14 8.55228 14 8V4.46584C14 3.10399 12.896 2 11.5342 2C11.2093 2 10.915 2.1913 10.7831 2.48812L7.26394 10.4061C7.10344 10.7673 6.74532 11 6.35013 11H4C2.89543 11 2 11.8954 2 13Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </button>
            <button 
              class="feedback-btn"
              :class="{ active: msg.feedbackStatus === 'not_useful' }"
              @click="handleFeedback(index, false)"
              :disabled="msg.feedbackStatus !== 'none' && msg.feedbackStatus !== undefined"
              title="无用"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M17 2V13M22 11V4C22 2.89543 21.1046 2 20 2H6.57377C5.09297 2 3.83376 3.08028 3.60859 4.54377L2.53165 11.5438C2.25211 13.3611 3.65824 15 5.49686 15H9C9.55228 15 10 15.4477 10 16V19.5342C10 20.896 11.104 22 12.4658 22C12.7907 22 13.085 21.8087 13.2169 21.5119L16.7361 13.5939C16.8966 13.2327 17.2547 13 17.6499 13H20C21.1046 13 22 12.1046 22 11Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </button>
            <span v-if="msg.feedbackStatus !== 'none' && msg.feedbackStatus !== undefined" class="feedback-status-label">已反馈</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 历史记录列表 -->
    <div class="history-list" v-show="showHistoryList">
      <div class="history-header">
        <h3>历史记录</h3>
      </div>
      <div class="history-content">
        <div v-if="isLoadingHistory" class="history-loading">
          <div class="loading-spinner"></div>
          <p>加载中...</p>
        </div>
        <div v-else-if="conversationList.length === 0" class="history-empty">
          <p>暂无历史记录</p>
        </div>
        <div v-else class="history-items">
          <div
            v-for="conv in conversationList"
            :key="conv.conversation_id"
            class="history-item"
            @click="loadConversation(conv.conversation_id)"
          >
            <div class="history-item-title">
              {{ conv.first_user_message || '无标题' }}
            </div>
            <div class="history-item-preview">
              {{ conv.last_assistant_message || '' }}
            </div>
            <div class="history-item-meta">
              <span class="message-count">{{ conv.message_count }} 条消息</span>
              <span class="created-time">{{ formatTime(conv.created_at) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 输入框 -->
    <div class="chat-input-wrapper" v-show="!showHistoryList">
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

    <!-- 工单表单弹窗（用户确认后显示）-->
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

    <!-- 反馈弹窗（负面反馈）-->
    <div v-if="showFeedbackModal" class="ticket-modal-overlay" @click.self="handleNegativeFeedbackCancel">
      <div class="ticket-modal feedback-modal">
        <div class="ticket-modal-header">
          <h3>💬 告诉我为何不好</h3>
        </div>
        <div class="ticket-modal-body">
          <!-- 反馈标签 -->
          <div class="feedback-tags">
            <button 
              v-for="tag in ['问题没解决', '内容不准确', '态度不好', '处理速度慢', '数据不积极', '其它']" 
              :key="tag"
              class="feedback-tag"
              :class="{ active: feedbackTags.includes(tag) }"
              @click="toggleFeedbackTag(tag)"
            >
              {{ tag }}
            </button>
          </div>
          
          <!-- 评语输入 -->
          <div class="form-group">
            <textarea 
              v-model="feedbackComment" 
              class="form-textarea feedback-textarea" 
              rows="4" 
              placeholder="请进一步说明（选填）..."
              maxlength="300"
            ></textarea>
            <div class="char-count">{{ feedbackComment.length }}/300</div>
          </div>
        </div>
        <div class="ticket-modal-footer">
          <button class="ticket-btn ticket-btn-cancel" @click="handleNegativeFeedbackCancel">取消</button>
          <button class="ticket-btn ticket-btn-confirm" @click="handleNegativeFeedbackSubmit">
            提交
          </button>
        </div>
      </div>
    </div>

    <!-- 反馈成功提示 -->
    <div v-if="showFeedbackSuccess" class="feedback-success-toast">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
        <path d="M20 6L9 17L4 12" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <span>感谢您的反馈！</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted } from 'vue';
import { initSession, getSessionHistory, createConversationId, getConversationList } from '../api/agent';
import { createFeedback, getFeedbackByConversation } from '../api/feedback';
import type { ConversationListItem } from '../api/agent';
import type { CreateFeedbackRequest } from '../api/feedback';

// 消息类型（扩展支持分隔线）
interface ChatMessage {
  role: 'user' | 'assistant' | 'system' | 'divider';
  content: string;
  timestamp?: string;  // 新增：消息时间戳（用于时间比对）
  feedbackStatus?: 'none' | 'useful' | 'not_useful' | 'submitted';  // 新增：反馈状态，submitted 表示历史已反馈
  userMessage?: string;  // 新增：对应的用户消息
  isWelcome?: boolean;  // 新增：是否是欢迎消息
}

// Session token management
const sessionToken = ref<string>('');
const conversationId = ref<string>('');  // 新增：对话ID
const isInitializing = ref(false);

// 历史记录相关状态
const showHistoryList = ref(false);  // 是否显示历史列表
const conversationList = ref<ConversationListItem[]>([]);  // 会话列表
const isLoadingHistory = ref(false);  // 是否正在加载历史

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

// 反馈弹窗相关状态
const showFeedbackModal = ref(false);  // 是否显示反馈弹窗
const showFeedbackSuccess = ref(false);  // 是否显示成功提示
const currentFeedbackIndex = ref(-1);  // 当前反馈的消息索引
const feedbackComment = ref('');  // 反馈评语
const feedbackTags = ref<string[]>([]);  // 选中的反馈标签

// 是否可以提交工单
const canSubmitTicket = computed(() => {
  return ticketFormData.value.content.trim().length > 0 && !isSubmittingTicket.value;
});

// 消息列表（初始显示欢迎消息）
const messages = ref<ChatMessage[]>([
  {
    role: 'assistant',
    content: '你好，我是安然，你的心理陪伴者。我在这里倾听你的心声，如果你在工作中遇到困扰或不公，随时可以跟我说。',
    isWelcome: true  // 标记为欢迎消息
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

// 新对话
const startNewChat = () => {
  console.log('[NewChat] 开始新对话');
  // 清空 conversation_id
  conversationId.value = '';
  // 清空消息列表，显示欢迎消息
  messages.value = [
    {
      role: 'assistant',
      content: '你好，我是安然，你的心理陪伴者。我在这里倾听你的心声，如果你在工作中遇到困扰或不公，随时可以跟我说。'
    }
  ];
  // 关闭历史列表
  showHistoryList.value = false;
  scrollToBottom();
};

// 切换历史列表显示
const toggleHistoryList = async () => {
  showHistoryList.value = !showHistoryList.value;
  
  if (showHistoryList.value) {
    // 打开历史列表时，加载数据
    await loadHistoryList();
  }
};

// 加载历史列表
const loadHistoryList = async () => {
  if (!sessionToken.value) {
    console.error('[History] 缺少 session_token');
    return;
  }
  
  try {
    isLoadingHistory.value = true;
    console.log('[History] 开始加载历史列表...');
    
    const response = await getConversationList(sessionToken.value);
    console.log('[History] 完整响应:', response);
    
    if (response.code === 200) {
      conversationList.value = response.data.conversations;
      console.log('[History] 历史列表加载成功，共', conversationList.value.length, '条记录');
    } else {
      console.error('[History] 加载失败 | code:', response.code, '| msg:', response.msg);
      alert('❌ 加载失败: ' + (response.msg || '未知错误'));
    }
  } catch (error: any) {
    console.error('[History] 加载异常:', error);
    alert('❌ 加载失败: ' + error.message);
  } finally {
    isLoadingHistory.value = false;
  }
};

// 加载具体某个会话的历史
const loadConversation = async (convId: string) => {
  console.log('[History] 开始加载会话:', convId);
  
  if (!sessionToken.value) {
    alert('❌ 会话已过期，请刷新页面');
    return;
  }
  
  try {
    // 1. 设置 conversation_id
    conversationId.value = convId;
    console.log('[History] 设置 conversation_id:', convId.substring(0, 20) + '...');
    
    // 2. 调用后端接口获取该会话的完整历史（从 MySQL）
    const response = await fetch(
      `/api/conversation/history/${convId}?session_token=${sessionToken.value}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const data = await response.json();
    console.log('[History] 历史消息:', data);
    
    // 3. 渲染历史消息
    if (data.messages && data.messages.length > 0) {
      messages.value = data.messages.map((msg: any) => ({
        role: msg.role,
        content: msg.content,
        // 兼容不同后端返回字段名：timestamp / createdAt
        timestamp: msg.timestamp || msg.createdAt,
        feedbackStatus: 'none'  // 初始化反馈状态
      }));
      console.log('[History] ✅ 加载历史成功，消息数:', data.messages.length);
    } else {
      // 无历史消息，显示默认欢迎信息
      messages.value = [
        {
          role: 'assistant',
          content: '你好，我是安然，你的心理陪伴者。我在这里倾听你的心声，如果你在工作中遇到困扰或不公，随时可以跟我说。'
        }
      ];
      console.log('[History] ⚠️ 该会话无历史消息');
    }
    
    // 4. 关闭历史列表，显示聊天界面
    showHistoryList.value = false;
    scrollToBottom();

    // 5. 查询当前会话的历史反馈，并标记到消息上
    try {
      const fbResp = await getFeedbackByConversation(sessionToken.value, conversationId.value);
      if (fbResp && (fbResp.code === 200 || fbResp.code === 0) && fbResp.data && fbResp.data.items) {
        const items: Array<{ userMessage: string; aiResponse: string; userMessageTimestamp?: string; aiResponseTimestamp?: string }> = fbResp.data.items;
        console.log('[History] 已有反馈条目:', items.length);

        // 规范化时间字符串：兼容 "YYYY-MM-DD HH:mm:ss" 与 ISO 格式
        const normalizeTime = (s?: string): number | string | null => {
          if (!s) return null;
          const t = s.trim();
          let d = new Date(t);
          if (isNaN(d.getTime())) {
            // 尝试替换空格为 T
            const t2 = t.replace(' ', 'T');
            d = new Date(t2);
          }
          return isNaN(d.getTime()) ? t : d.getTime();
        };

        const isSameTime = (a?: string, b?: string) => {
          if (!a || !b) return true; // 任一缺失时不阻断匹配（兼容老数据）
          const na = normalizeTime(a);
          const nb = normalizeTime(b);
          if (typeof na === 'number' && typeof nb === 'number') return na === nb;
          return String(na) === String(nb);
        };

        items.forEach(item => {
          // 先根据 userMessage 锚定该轮用户发言
          const userIdx = messages.value.findIndex(m => m.role === 'user' && m.content === item.userMessage);

          if (userIdx !== -1) {
            // 从该用户消息之后向前查找第一个匹配的助手回复
            for (let j = userIdx + 1; j < messages.value.length; j++) {
              const m = messages.value[j];
              if (m.role === 'user') break; // 到下一轮用户发言，停止搜索
              if (m.role === 'assistant' && m.content === item.aiResponse) {
                // 时间戳严格校验（在时间戳存在的情况下）
                const userOk = isSameTime(messages.value[userIdx]?.timestamp, item.userMessageTimestamp);
                const aiOk = isSameTime(m.timestamp, item.aiResponseTimestamp);
                if (!userOk || !aiOk) {
                  continue; // 时间不一致则不标记为已反馈
                }
                if (m.feedbackStatus === undefined || m.feedbackStatus === 'none') {
                  m.feedbackStatus = 'submitted';
                }
                break;
              }
            }
          } // 不再使用仅AI回复匹配的回退逻辑，必须同时匹配用户与AI消息
        });
      }
    } catch (e) {
      console.warn('[History] 查询会话反馈失败(不影响聊天):', e);
    }

    console.log('[History] ✅ 会话切换完成，可以继续对话');
    
  } catch (error: any) {
    console.error('[History] 加载会话失败:', error);
    alert('❌ 加载失败: ' + error.message);
  }
};

// 格式化时间
const formatTime = (timeStr: string | null): string => {
  if (!timeStr) return '';
  try {
    const date = new Date(timeStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    
    if (days === 0) return '今天';
    if (days === 1) return '昨天';
    if (days < 7) return `${days}天前`;
    return date.toLocaleDateString('zh-CN');
  } catch (e) {
    return '';
  }
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
    
    // 获取 access_token（优先从 URL，其次从 localStorage）
    const urlParams = new URLSearchParams(window.location.search);
    let accessToken = urlParams.get('access_token');
    
    if (!accessToken) {
      accessToken = localStorage.getItem('access_token');
    }
    
    if (!accessToken) {
      throw new Error('未找到用户认证信息，请确保 URL 中包含 access_token 参数');
    }
    
    console.log('[TicketForm] 使用 access_token:', accessToken.substring(0, 20) + '...');
    
    // 构建请求数据（将 images 数组转为字符串）
    const requestData = {
      content: ticketFormData.value.content,
      contact: ticketFormData.value.contact,
      images: ticketFormData.value.images.join(',')  // ✅ 数组转字符串
    };
    
    console.log('[TicketForm] 请求数据:', requestData);
    
    // 直接调用 Golang 接口（使用 Vite 代理，避免 CORS 问题）
    const response = await fetch('/app/help/postHelpRequest', {
      method: 'POST',
      headers: {
        'x-token': accessToken,  // 使用 x-token 而不是 Authorization
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(requestData)  // ✅ 使用处理后的数据
    });
    
    console.log('[TicketForm] 响应状态码:', response.status);
    console.log('[TicketForm] 响应头:', Object.fromEntries(response.headers.entries()));
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('[TicketForm] HTTP 错误响应:', errorText);
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }
    
    const responseText = await response.text();
    console.log('[TicketForm] 原始响应内容:', responseText);
    
    let result;
    try {
      result = responseText ? JSON.parse(responseText) : {};
    } catch (e) {
      console.error('[TicketForm] JSON 解析失败:', e);
      throw new Error(`响应不是有效的 JSON: ${responseText}`);
    }
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



/// 处理反馈
const handleFeedback = async (messageIndex: number, isUseful: boolean) => {
  const message = messages.value[messageIndex];
  
  if (!message || message.role !== 'assistant') {
    console.error('[Feedback] 无效的消息索引');
    return;
  }
  
  console.log('[Feedback] AI消息内容:', message.content);
  console.log('[Feedback] 消息长度:', message.content?.length || 0);
  
  if (!message.content) {
    console.error('[Feedback] AI消息内容为空！');
    alert('❌ AI回复内容为空，无法提交反馈');
    return;
  }
  
  // 查找对应的用户消息（往前查找最近的user消息）
  let userMessage = '';
  for (let i = messageIndex - 1; i >= 0; i--) {
    const msg = messages.value[i];
    if (msg && msg.role === 'user') {
      userMessage = msg.content;
      break;
    }
  }
  
  if (!userMessage) {
    console.error('[Feedback] 未找到对应的用户消息');
    return;
  }
  
  if (!conversationId.value) {
    console.error('[Feedback] conversation_id 为空');
    alert('❌ 无法提交反馈，请先发送消息');
    return;
  }
  
  console.log('[Feedback] 数据检查通过:', {
    userMessage: userMessage.substring(0, 30),
    aiMessage: message.content.substring(0, 30),
    conversationId: conversationId.value
  });
  
  if (isUseful) {
    // 点击"有用"：直接提交反馈
    await submitFeedback(messageIndex, userMessage, message.content, true, 'helpful', '');
  } else {
    // 点击"无用"：显示反馈表单
    currentFeedbackIndex.value = messageIndex;
    feedbackComment.value = '';
    feedbackTags.value = [];
    showFeedbackModal.value = true;
  }
};

// 提交反馈
const submitFeedback = async (
  messageIndex: number,
  userMsg: string,
  aiMsg: string,
  isUseful: boolean,
  feedbackType: string,  // 新增：反馈类型
  comment: string
) => {
  try {
    console.log('[Feedback] 提交反馈:', {
      isUseful,
      feedbackType,
      userMessage: userMsg.substring(0, 50) + '...',
      aiResponse: aiMsg.substring(0, 50) + '...',
      comment
    });
    
    const feedbackParams: CreateFeedbackRequest = {
      conversation_id: conversationId.value,
      is_useful: isUseful,
      feedback_type: feedbackType || undefined,  // 新增：反馈类型
      comment: comment || undefined,
      user_message: userMsg,
      ai_response: aiMsg
    };
    
    const response = await createFeedback(sessionToken.value, feedbackParams);
    console.log('[Feedback] 后端完整响应:', response);
    
    // 兼容处理：判断是否成功
    // 1. code === 200 (标准格式)
    // 2. code === 0 (部分后端使用0表示成功)
    // 3. msg 包含 '成功' 或 'success'
    const isSuccess = 
      response.code === 200 || 
      response.code === 0 || 
      (response.msg && (
        response.msg.includes('成功') || 
        response.msg.toLowerCase().includes('success')
      ));
    
    if (isSuccess) {
      // 更新反馈状态
      const message = messages.value[messageIndex];
      if (message) {
        message.feedbackStatus = isUseful ? 'useful' : 'not_useful';
      }
      console.log('[Feedback] ✅ 反馈提交成功');
      
      // 显示成功提示
      showFeedbackSuccess.value = true;
      setTimeout(() => {
        showFeedbackSuccess.value = false;
      }, 2000);
    } else {
      console.error('[Feedback] 反馈失败:', response.msg || '未知错误');
      alert(`❌ 反馈失败: ${response.msg || '请稍后重试'}`);
    }
  } catch (error: any) {
    console.error('[Feedback] 提交异常:', error);
    alert(`❌ 反馈失败: ${error.message}`);
  }
};

// 确认提交负面反馈
const handleNegativeFeedbackSubmit = async () => {
  if (currentFeedbackIndex.value < 0) return;
  
  const message = messages.value[currentFeedbackIndex.value];
  if (!message) {
    console.error('[Feedback] 消息不存在');
    return;
  }
  
  console.log('[Feedback] 当前AI消息内容:', message.content);
  console.log('[Feedback] 消息长度:', message.content?.length || 0);
  
  // 查找对应的用户消息
  let userMessage = '';
  for (let i = currentFeedbackIndex.value - 1; i >= 0; i--) {
    const msg = messages.value[i];
    if (msg && msg.role === 'user') {
      userMessage = msg.content;
      console.log('[Feedback] 找到用户消息:', userMessage);
      break;
    }
  }
  
  if (!userMessage) {
    console.error('[Feedback] 未找到对应的用户消息');
    return;
  }
  
  if (!message.content) {
    console.error('[Feedback] AI消息内容为空！');
    alert('❌ AI回复内容为空，无法提交反馈');
    return;
  }
  
  // 组合标签和评语
  const feedbackType = feedbackTags.value.length > 0 ? feedbackTags.value.join('、') : '';
  const finalComment = feedbackComment.value.trim();
  
  console.log('[Feedback] 准备提交:', {
    feedbackType,
    comment: finalComment,
    userMessage: userMessage.substring(0, 30),
    aiMessage: message.content.substring(0, 30)
  });
  
  showFeedbackModal.value = false;
  await submitFeedback(
    currentFeedbackIndex.value,
    userMessage,
    message.content,
    false,
    feedbackType,  // 标签作为feedback_type
    finalComment   // 评语作为comment
  );
};

// 取消负面反馈
const handleNegativeFeedbackCancel = () => {
  showFeedbackModal.value = false;
  feedbackComment.value = '';
  feedbackTags.value = [];
  currentFeedbackIndex.value = -1;
};

// 切换标签选择
const toggleFeedbackTag = (tag: string) => {
  const index = feedbackTags.value.indexOf(tag);
  if (index > -1) {
    feedbackTags.value.splice(index, 1);
  } else {
    feedbackTags.value.push(tag);
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
  // 如果还没有 conversation_id，先创建一个
  if (!conversationId.value) {
    console.log('[Conversation] 第一次发送消息，创建对话ID...');
    try {
      const convResponse = await createConversationId(sessionToken.value);
      if (convResponse.code === 200) {
        conversationId.value = convResponse.data.conversation_id;
        console.log('[Conversation] ✅ 对话ID创建成功:', conversationId.value.substring(0, 20) + '...');
      } else {
        console.error('[Conversation] 对话ID创建失败:', convResponse);
        throw new Error('对话初始化失败');
      }
    } catch (error: any) {
      console.error('[Conversation] 创建对话ID异常:', error);
      alert('❌ 对话初始化失败，请刷新页面重试');
      return;
    }
  }
  
  // 添加助手消息占位符
  const assistantMessageIndex = messages.value.length;
  messages.value.push({
    role: 'assistant',
    content: '',
    feedbackStatus: 'none'  // 初始化反馈状态
  });

  isLoading.value = true;
  scrollToBottom();

  try {
    console.log('[Workflow] 调用 /api/agent/chat 流式接口...');
    
    const urlWithToken = `/api/agent/chat?session_token=${sessionToken.value}`;
    
    // 构建请求体，支持额外的 state 传递
    const requestBody: any = {
      user_input: userMessage,
      conversation_id: conversationId.value  // 新增：传递 conversation_id
    };
    
    // 如果有额外的 state，合并到请求体
    if (Object.keys(additionalState).length > 0) {
      Object.assign(requestBody, additionalState);
      console.log('[Workflow] 携带额外 state:', additionalState);
    }
    
    console.log('[Workflow] conversation_id:', conversationId.value);
    
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
        content: msg.content,
        timestamp: msg.timestamp, // 映射时间戳用于后续时间校验
        feedbackStatus: 'none' as const  // 使用 as const 明确类型
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
      const cachedSessionToken = localStorage.getItem('session_token');
      if (cachedSessionToken) {
        sessionToken.value = cachedSessionToken;
        console.log('[Session] ✅ 使用缓存的 session_token:', cachedSessionToken.substring(0, 20) + '...');
        // conversation_id 会在第一次发送消息时创建
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
      // conversation_id 会在第一次发送消息时创建
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
  // ✅ 不再自动加载历史，仅显示默认欢迎信息
  // await loadChatHistory(); // 删除
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
  position: relative;  /* 添加定位上下文 */
}

.back-btn,
.new-chat-btn,
.history-btn {
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
  color: #333;  /* 设置默认颜色 */
}

.back-btn svg,
.new-chat-btn svg,
.history-btn svg {
  color: #333;  /* SVG 图标颜色 */
}

.back-btn:hover,
.new-chat-btn:hover,
.history-btn:hover {
  background: #f0f0f0;
}

.header-actions {
  display: flex;
  gap: 8px;
  z-index: 10;  /* 确保在最上层 */
}

.chat-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  color: #333;
  position: absolute;  /* 绝对定位居中 */
  left: 50%;
  transform: translateX(-50%);
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

/* 历史记录列表 */
.history-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #fff;
  overflow: hidden;
}

.history-header {
  padding: 16px;
  border-bottom: 1px solid #e5e5e5;
}

.history-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.history-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.history-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #999;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #07c160;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 12px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.history-empty {
  text-align: center;
  padding: 40px;
  color: #999;
}

.history-items {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-item {
  background: #fff;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.history-item:hover {
  background: #f5f5f5;
  border-color: #07c160;
}

.history-item-title {
  font-size: 15px;
  font-weight: 500;
  color: #333;
  margin-bottom: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-item-preview {
  font-size: 13px;
  color: #666;
  margin-bottom: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-item-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #999;
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
  flex-direction: column;  /* 添加：垂直排列消息和反馈按钮 */
}

.message-user {
  align-items: flex-end;  /* 用户消息右对齐 */
}

.message-assistant {
  align-items: flex-start;  /* AI消息左对齐 */
}

.message-bubble {
  max-width: 70%;  /* 增加最大宽度，从50%改为70% */
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
  word-wrap: break-word;
  word-break: break-word;  /* 添加：英文单词换行 */
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

/* 反馈按钮样式 */
.feedback-buttons {
  display: flex;
  gap: 8px;
  margin-top: 8px;
  padding-left: 0;
}

.feedback-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px solid #e5e5e5;
  background: #fff;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  color: #999;
}

.feedback-btn:hover:not(:disabled) {
  border-color: #07c160;
  background: #f0f9f4;
  color: #07c160;
}

.feedback-btn.active {
  border-color: #07c160;
  background: #07c160;
  color: #fff;
}

.feedback-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.feedback-btn svg {
  width: 16px;
  height: 16px;
}

.feedback-status-label {
  align-self: center;
  font-size: 12px;
  color: #999;
}

/* 反馈弹窗样式 */
.feedback-modal {
  max-width: 420px;
}

.feedback-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.feedback-tag {
  padding: 8px 16px;
  border: 1px solid #e5e5e5;
  background: #fff;
  border-radius: 20px;
  font-size: 14px;
  color: #666;
  cursor: pointer;
  transition: all 0.2s;
}

.feedback-tag:hover {
  border-color: #07c160;
  color: #07c160;
}

.feedback-tag.active {
  border-color: #07c160;
  background: #07c160;
  color: #fff;
}

.feedback-textarea {
  min-height: 100px;
  margin-bottom: 0;
}

.char-count {
  text-align: right;
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

/* 反馈成功提示 */
.feedback-success-toast {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: rgba(0, 0, 0, 0.8);
  color: #fff;
  padding: 16px 24px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  z-index: 2000;
  animation: fadeInOut 2s ease-in-out;
}

@keyframes fadeInOut {
  0% {
    opacity: 0;
    transform: translate(-50%, -40%);
  }
  10%, 90% {
    opacity: 1;
    transform: translate(-50%, -50%);
  }
  100% {
    opacity: 0;
    transform: translate(-50%, -60%);
  }
}
</style>