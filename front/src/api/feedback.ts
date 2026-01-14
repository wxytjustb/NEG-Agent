// 反馈相关接口封装

/**
 * 创建用户反馈请求参数
 */
export interface CreateFeedbackRequest {
  conversation_id: string;
  is_useful: boolean;
  feedback_type?: string;  // 新增：反馈类型（标签）
  comment?: string;
  user_message: string;
  ai_response: string;
}

/**
 * 反馈响应
 */
export interface FeedbackResponse {
  code: number;
  msg: string;
  data: any;
}

// 按会话查询反馈-条目
export interface ConversationFeedbackItem {
  aiResponse: string;
  createdAt: string;
}

// 按会话查询反馈-数据体
export interface ConversationFeedbackData {
  conversationId: string;
  hasFeedback: boolean;
  count: number;
  items: ConversationFeedbackItem[];
}

/**
 * 创建用户反馈
 * @param sessionToken 会话Token
 * @param params 反馈参数
 * @returns Promise<FeedbackResponse>
 */
export async function createFeedback(
  sessionToken: string,
  params: CreateFeedbackRequest
): Promise<FeedbackResponse> {
  try {
    console.log('[Feedback] 创建反馈(入参):', params);

    // 组装后端所需的 camelCase 字段，并保证 feedbackType/comment 始终传递
    const payload = {
      conversationId: params.conversation_id,
      isUseful: params.is_useful,
      feedbackType: params.feedback_type ?? "",
      comment: params.comment ?? "",
      userMessage: params.user_message,
      aiResponse: params.ai_response,
    };
    
    const response = await fetch(`/api/feedback/create?session_token=${sessionToken}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      if (response.status === 401) {
        console.warn('[Feedback] Session 已过期');
        localStorage.removeItem('session_token');
        localStorage.removeItem('access_token');
        throw new Error('会话已过期，请刷新页面');
      }
      throw new Error(`创建反馈失败: ${response.status}`);
    }

    const data = await response.json();
    console.log('[Feedback] 创建反馈响应:', data);
    
    // 兼容处理：Go后端可能返回 code 或者直接是 code字段
    if (data.code === 200 || data.code === 0 || response.status === 200) {
      console.log('[Feedback] 反馈创建成功');
      return { code: 200, msg: '成功', data: data.data || data };
    }
    
    return data;
  } catch (error) {
    console.error('[Feedback] 创建失败:', error);
    throw error;
  }
}

/**
 * 获取反馈总结（近 n 天）
 * @param sessionToken 会话Token
 * @param n 天数
 * @returns Promise<FeedbackResponse>
 */
export async function getFeedbackSummary(
  sessionToken: string,
  days: number
): Promise<FeedbackResponse> {
  try {
    console.log('[Feedback] 查询反馈总结: days=', days);

    const response = await fetch(`/api/feedback/summary?session_token=${sessionToken}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ days }),
    });

    if (!response.ok) {
      if (response.status === 401) {
        console.warn('[Feedback] Session 已过期');
        localStorage.removeItem('session_token');
        localStorage.removeItem('access_token');
        throw new Error('会话已过期，请刷新页面');
      }
      throw new Error(`查询反馈总结失败: ${response.status}`);
    }

    const data = await response.json();
    console.log('[Feedback] 反馈总结响应:', data);

    if (data.code === 200 || data.code === 0 || response.status === 200) {
      return { code: 200, msg: '成功', data: data.data || data };
    }

    return data;
  } catch (error) {
    console.error('[Feedback] 查询总结失败:', error);
    throw error;
  }
}

/**
 * 根据会话ID查询已提交的反馈
 * @param sessionToken 会话Token
 * @param conversationId 会话ID
 * @returns Promise<FeedbackResponse<ConversationFeedbackData>>
 */
export async function getFeedbackByConversation(
  sessionToken: string,
  conversationId: string
): Promise<FeedbackResponse> {
  try {
    console.log('[Feedback] 按会话查询反馈: conversationId=', conversationId);

    const response = await fetch(
      `/api/feedback/by_conversation?session_token=${sessionToken}&conversationId=${encodeURIComponent(conversationId)}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    if (!response.ok) {
      if (response.status === 401) {
        console.warn('[Feedback] Session 已过期');
        localStorage.removeItem('session_token');
        localStorage.removeItem('access_token');
        throw new Error('会话已过期，请刷新页面');
      }
      throw new Error(`按会话查询反馈失败: ${response.status}`);
    }

    const data = await response.json();
    console.log('[Feedback] 会话反馈响应:', data);

    if (data.code === 200 || data.code === 0 || response.status === 200) {
      return { code: 200, msg: '成功', data: data.data || data };
    }

    return data;
  } catch (error) {
    console.error('[Feedback] 查询失败:', error);
    throw error;
  }
}
