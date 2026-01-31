// 志愿者相关接口

export interface VolunteerUser {
  realname?: string;
  nickname?: string;
  volunteerServiceType?: string;
}

export interface TicketVolunteer {
  ID: number;
  volunteerUser?: VolunteerUser;
}

export interface TicketVolunteerListResponse {
  list: TicketVolunteer[];
}

export interface BaseResponse<T = any> {
  code: number;
  msg: string;
  data: T;
}

/**
 * 根据工单ID和会话ID获取志愿者列表
 * @param sessionToken 会话Token
 * @param ticketId 工单ID
 * @param conversationId 会话ID
 * @returns Promise<BaseResponse<TicketVolunteerListResponse>>
 */
export async function getVolunteersByTicketAndConversation(
  sessionToken: string,
  ticketId?: number,
  conversationId?: string
): Promise<BaseResponse<TicketVolunteerListResponse>> {
  try {
    const response = await fetch(`/api/ticketVolunteer/getByTicketAndConversation?session_token=${sessionToken}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-token': sessionToken // 添加 x-token 头，确保兼容性
      },
      body: JSON.stringify({
        ticketId: Number(ticketId), // 确保转为数字
        conversationId: String(conversationId) // 确保转为字符串
      }),
    });

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error('会话已过期，请刷新页面');
      }
      const errorText = await response.text();
      throw new Error(`获取志愿者列表失败: ${response.status} ${errorText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('[TicketVolunteer] 获取失败:', error);
    throw error;
  }
}
