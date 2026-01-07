// Agent 相关接口封装
import { post } from '../utls/require';

// 消息类型
export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

// Chat 请求参数
export interface ChatRequest {
  messages: ChatMessage[];
  provider?: 'ollama' | 'deepseek';
  temperature?: number;
  max_tokens?: number;
  model?: string;
  stream?: boolean;
}

// Session 初始化响应
export interface SessionResponse {
  code: number;
  msg: string;
  data: {
    session_token: string;
    user: any;
    expires_in: number;
  };
}

// 对话历史响应
export interface HistoryResponse {
  code: number;
  msg: string;
  data: {
    user_id: string;
    metadata: any;
    messages: ChatMessage[];
    is_new_user: boolean;
  };
}

// ChromaDB 历史记录响应
export interface ChromaDBHistoryResponse {
  user_id: string;
  session_id: string;
  total_count: number;
  messages: Array<{
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: string;
    user_id: string;
    session_id: string;
  }>;
}

// LangGraph 工作流请求参数
export interface WorkflowChatRequest {
  message: string;
}

// LangGraph 工作流响应
export interface WorkflowChatResponse {
  code: number;
  msg: string;
  data: {
    user_id: string;
    user_intent: string;  // AI 分析的用户意图
    ai_response: string;  // AI 回复
    error: string | null; // 错误信息
  };
}

// Conversation ID 响应
export interface ConversationResponse {
  code: number;
  msg: string;
  data: {
    conversation_id: string;
    created_at: number;
  };
}

// 会话列表项
export interface ConversationListItem {
  conversation_id: string;
  first_user_message: string | null;
  last_assistant_message: string | null;
  message_count: number;
  created_at: string | null;
}

// 会话列表响应
export interface ConversationListResponse {
  code: number;
  msg: string;
  data: {
    user_id: string;
    total_conversations: number;
    conversations: ConversationListItem[];
  };
}


/**
 * 获取用户的所有会话列表
 * @param sessionToken 会话Token
 * @returns Promise<ConversationListResponse>
 */
export async function getConversationList(sessionToken: string): Promise<ConversationListResponse> {
  try {
    const response = await fetch(`/api/conversation/list?session_token=${sessionToken}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      if (response.status === 401) {
        console.warn('[ConversationList] Session 已过期，清除本地缓存');
        localStorage.removeItem('session_token');
        localStorage.removeItem('access_token');
        throw new Error('会话已过期，请刷新页面重新登录');
      }
      throw new Error(`获取会话列表失败: ${response.status}`);
    }

    const data = await response.json();
    console.log('[ConversationList] 会话列表:', data);
    return data;
  } catch (error) {
    console.error('Get conversation list error:', error);
    throw error;
  }
}

/**
 * 创建新的 conversation_id
 * @param sessionToken 会话Token
 * @returns Promise<ConversationResponse>
 */
export async function createConversationId(sessionToken: string): Promise<ConversationResponse> {
  try {
    const response = await fetch(`/api/conversation/create?session_token=${sessionToken}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`创建 conversation_id 失败: ${response.status}`);
    }

    const data = await response.json();
    console.log('[Conversation] 创建新的 conversation_id:', data.data.conversation_id);
    return data;
  } catch (error) {
    console.error('Create conversation_id error:', error);
    throw error;
  }
}

/**
 * 初始化 Agent 会话
 * @param accessToken 用户认证 Token (来自 Golang Server)
 * @returns Promise<SessionResponse>
 */
export async function initSession(accessToken: string): Promise<SessionResponse> {
  try {
    const response = await fetch(`/api/agent/init?access_token=${accessToken}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    const data = await response.json();

    if (!response.ok) {
      // 提取后端返回的错误信息
      const errorMsg = data.detail || `HTTP ${response.status}: ${response.statusText}`;
      console.error('[Session] 初始化失败:', errorMsg);
      throw new Error(errorMsg);
    }

    console.log('[Session] 会话初始化响应:', data);
    return data;
  } catch (error) {
    console.error('Init session error:', error);
    throw error;
  }
}

/**
 * Agent 流式对话接口
 * @param sessionToken 会话 Token (由 initSession 获得)
 * @param params 对话参数
 * @param onMessage 流式消息回调
 * @returns Promise<void>
 */
export async function chatStream(
  sessionToken: string,
  params: ChatRequest,
  onMessage: (chunk: string) => void,
  onError?: (error: Error) => void,
  onComplete?: () => void
): Promise<void> {
  try {
    const response = await fetch(`/api/agent/chat?session_token=${sessionToken}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        messages: params.messages,
        provider: params.provider || 'ollama',
        temperature: params.temperature || 0.7,
        max_tokens: params.max_tokens || 2000,
        model: params.model,
        stream: true,
      }),
    });

    if (!response.ok) {
      // 如果是 401 错误（session 过期），清除本地缓存
      if (response.status === 401) {
        console.warn('[Session] Session 已过期，清除本地缓存');
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

    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        console.log('[Stream] 读取完成');
        break;
      }

      // 解码数据块
      const chunk = decoder.decode(value, { stream: true });
      buffer += chunk;
      console.log('[Stream] 收到数据块:', chunk);

      // 处理SSE格式的数据 - SSE使用双换行符分隔消息
      const messages = buffer.split('\n\n');
      // 保留最后一个可能不完整的消息
      buffer = messages.pop() || '';

      for (const message of messages) {
        // 每个消息可能包含多行，我们只处理data:开头的行
        const lines = message.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const content = line.substring(6);
            console.log('[Stream] 解析数据:', content);

            if (content === '[DONE]') {
              console.log('[Stream] 收到结束标记');
              onComplete?.();
              return;
            } else if (content.startsWith('[ERROR]')) {
              console.error('[Stream] 收到错误:', content);
              onError?.(new Error(content));
            } else if (content) {
              onMessage(content);
            }
          }
        }
      }
    }

    console.log('[Stream] 流结束，调用onComplete');
    onComplete?.();
  } catch (error) {
    console.error('Chat stream error:', error);
    onError?.(error as Error);
  }
}

/**
 * 获取对话历史（Redis）
 * @param sessionToken 会话 Token
 * @returns Promise<HistoryResponse>
 */
export async function getChatHistory(sessionToken: string): Promise<HistoryResponse> {
  try {
    const response = await fetch(`/api/agent/history?session_token=${sessionToken}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`获取历史失败: ${response.status}`);
    }

    const data = await response.json();
    console.log('[History] 对话历史:', data);
    return data;
  } catch (error) {
    console.error('Get chat history error:', error);
    throw error;
  }
}

/**
 * 获取指定会话的所有历史对话（ChromaDB）
 * @param sessionToken 会话 Token
 * @param sessionId 会话ID
 * @param limit 限制数量（可选）
 * @returns Promise<ChromaDBHistoryResponse>
 */
export async function getSessionHistory(
  sessionToken: string,
  sessionId: string,
  limit?: number
): Promise<ChromaDBHistoryResponse> {
  try {
    const url = new URL(`/api/agent/history/${sessionId}`, window.location.origin);
    url.searchParams.append('session_token', sessionToken);
    if (limit) {
      url.searchParams.append('limit', limit.toString());
    }

    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      if (response.status === 401) {
        console.warn('[SessionHistory] Session 已过期，清除本地缓存');
        localStorage.removeItem('session_token');
        localStorage.removeItem('access_token');
        throw new Error('会话已过期，请刷新页面重新登录');
      }
      throw new Error(`获取会话历史失败: ${response.status}`);
    }

    const data = await response.json();
    console.log('[SessionHistory] ChromaDB 历史记录:', data);
    return data;
  } catch (error) {
    console.error('Get session history error:', error);
    throw error;
  }
}

/**
 * 健康检查
 */
export async function ping() {
  return post('/ping');
}

/**
 * 开始新对话（增加 conversation_count）
 * @param accessToken 用户认证 Token
 * @returns Promise<any>
 */
export async function startNewConversation(accessToken: string): Promise<any> {
  try {
    const response = await fetch(`/api/agent/new-conversation?access_token=${accessToken}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`开始新对话失败: ${response.status}`);
    }

    const data = await response.json();
    console.log('[NewConversation] 新对话已开始:', data);
    return data;
  } catch (error) {
    console.error('Start new conversation error:', error);
    throw error;
  }
}

/**
 * 调用 LangGraph 工作流进行对话
 * @param sessionToken 会话 Token
 * @param message 用户消息
 * @returns Promise<WorkflowChatResponse>
 */
export async function workflowChat(
  sessionToken: string,
  message: string
): Promise<WorkflowChatResponse> {
  try {
    console.log('[WorkflowChat] 发起请求:', { message });
    
    const response = await fetch(
      `/api/workflow/chat?session_token=${sessionToken}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message }),
      }
    );

    if (!response.ok) {
      // 如果是 401 错误（session 过期），清除本地缓存
      if (response.status === 401) {
        console.warn('[WorkflowChat] Session 已过期，清除本地缓存');
        localStorage.removeItem('session_token');
        localStorage.removeItem('access_token');
        throw new Error('会话已过期，请刷新页面重新登录');
      }
      
      const errorData = await response.json().catch(() => ({}));
      const errorMsg = errorData.detail || `请求失败: ${response.status}`;
      throw new Error(errorMsg);
    }

    const data = await response.json();
    console.log('[WorkflowChat] 工作流响应:', data);
    
    // 检查是否有错误
    if (data.data?.error) {
      console.warn('[WorkflowChat] 工作流执行出现错误:', data.data.error);
    }
    
    return data;
  } catch (error) {
    console.error('[WorkflowChat] 请求失败:', error);
    throw error;
  }
}