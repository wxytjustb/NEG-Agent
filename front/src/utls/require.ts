// 基础配置 - 使用相对路径，通过 Vite 代理访问后端
const BASE_URL = '';

// 封装 fetch 请求
export const request = async (url: string, options: RequestInit = {}) => {
  const response = await fetch(`${BASE_URL}${url}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    throw new Error(`请求失败: ${response.status}`);
  }

  return await response.json();
};

// GET 请求
export const get = (url: string) => {
  return request(url, { method: 'GET' });
};

// POST 请求
export const post = (url: string, data?: any) => {
  return request(url, {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

// PUT 请求
export const put = (url: string, data?: any) => {
  return request(url, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
};

// DELETE 请求
export const del = (url: string) => {
  return request(url, { method: 'DELETE' });
};