// 工单相关接口封装

/**
 * 工单模型
 */
export interface AppTicket {
  id?: number;
  appUserId?: number;
  issueType?: string;
  platform?: string;
  briefFacts?: string;
  userRequest?: string;
  peopleNeedingHelp?: number;
  conversationId?: string;
  status: string;
  handlerId?: number;
  handlerName?: string;
  createdAt?: string;
  updatedAt?: string;
}

/**
 * 工单列表响应
 */
export interface TicketListResponse {
  total: number;
  items?: AppTicket[];
  list?: AppTicket[]; // 兼容后端返回 list 字段
  page: number;
  page_size: number;
}

/**
 * 更新工单状态请求
 */
export interface UpdateTicketStatusRequest {
  id: string;
  status: string;
}

export interface BaseResponse {
  code: number;
  msg: string;
  data: any;
}

/**
 * 创建工单
 * @param sessionToken 会话Token
 * @param ticket 工单信息
 * @returns Promise<BaseResponse>
 */
export async function createTicket(
  sessionToken: string,
  ticket: AppTicket
): Promise<BaseResponse> {
  try {
    const response = await fetch(`/api/ticket/createTicket?session_token=${sessionToken}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(ticket),
    });

    if (!response.ok) {
       if (response.status === 401) {
        throw new Error('会话已过期，请刷新页面');
      }
      const errorText = await response.text();
      throw new Error(`创建工单失败: ${response.status} ${errorText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('[Ticket] 创建失败:', error);
    throw error;
  }
}

/**
 * 获取工单列表
 * @param sessionToken 会话Token
 * @param page 页码
 * @param pageSize 每页数量
 * @param conversationId 会话ID过滤
 * @returns Promise<TicketListResponse>
 */
export async function getTicketList(
  token: string,
  page: number = 1,
  pageSize: number = 10,
  conversationId?: string
): Promise<TicketListResponse> {
  try {
    let url = `/api/ticket/getTicketList?page=${page}&pageSize=${pageSize}&session_token=${token}`;
    if (conversationId) {
      url += `&conversationId=${conversationId}`;
    }

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'x-token': token
      }
    });

    if (!response.ok) {
       if (response.status === 401) {
        throw new Error('认证已过期，请刷新页面');
      }
      const errorText = await response.text();
      throw new Error(`获取工单列表失败: ${response.status} ${errorText}`);
    }

    const res = await response.json();
    if (res.code === 200 || res.code === 0) {
      return res.data;
    } else {
      throw new Error(res.msg || '获取列表失败');
    }
  } catch (error) {
    console.error('[Ticket] 获取列表失败:', error);
    throw error;
  }
}

/**
 * 获取工单详情
 * @param sessionToken 会话Token
 * @param id 工单ID
 * @returns Promise<AppTicket>
 */
export async function getTicketDetail(
  sessionToken: string,
  id: string
): Promise<AppTicket> {
  try {
    const response = await fetch(`/api/ticket/getTicketDetail?session_token=${sessionToken}&id=${id}`, {
      method: 'GET',
    });

    if (!response.ok) {
       if (response.status === 401) {
        throw new Error('会话已过期，请刷新页面');
      }
      const errorText = await response.text();
      throw new Error(`获取工单详情失败: ${response.status} ${errorText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('[Ticket] 获取详情失败:', error);
    throw error;
  }
}

/**
 * 更新工单状态
 * @param sessionToken 会话Token
 * @param params 更新参数
 * @returns Promise<any>
 */
export async function updateTicketStatus(
  sessionToken: string,
  params: UpdateTicketStatusRequest
): Promise<any> {
  try {
    const response = await fetch(`/api/ticket/updateTicketStatus?session_token=${sessionToken}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(params),
    });

    if (!response.ok) {
       if (response.status === 401) {
        throw new Error('会话已过期，请刷新页面');
      }
      const errorText = await response.text();
      throw new Error(`更新工单状态失败: ${response.status} ${errorText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('[Ticket] 更新状态失败:', error);
    throw error;
  }
}
