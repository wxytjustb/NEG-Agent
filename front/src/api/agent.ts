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


/**
 * 初始化 Agent 会话
 * @param accessToken 用户认证 Token (来自 Golang Server)
 * @returns Promise<SessionResponse>
 */
export async function initSession(accessToken: string): Promise<SessionResponse> {
  try {
    const response = await fetch(`http://127.0.0.1:8000/api/agent/init?access_token=${accessToken}`, {
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
    const response = await fetch(`http://127.0.0.1:8000/api/agent/chat?session_token=${sessionToken}`, {
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
 * 健康检查
 */
export async function ping() {
  return post('/ping');
}