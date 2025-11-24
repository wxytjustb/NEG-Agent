// 基础配置
const BASE_URL = 'http://127.0.0.1:8000';

// 封装 uni.request 请求
export const request = (url: string, options: any = {}) => {
  return new Promise((resolve, reject) => {
    uni.request({
      url: `${BASE_URL}${url}`,
      method: options.method || 'GET',
      data: options.data,
      header: {
        'Content-Type': 'application/json',
        ...options.header,
      },
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else {
          reject(new Error(`请求失败: ${res.statusCode}`));
        }
      },
      fail: (err) => {
        reject(new Error(err.errMsg || '网络请求失败'));
      }
    });
  });
};

// GET 请求
export const get = (url: string, params?: any) => {
  if (params) {
    const query = Object.keys(params)
      .map(key => `${key}=${encodeURIComponent(params[key])}`)
      .join('&');
    url = `${url}?${query}`;
  }
  return request(url, { method: 'GET' });
};

// POST 请求
export const post = (url: string, data?: any) => {
  return request(url, {
    method: 'POST',
    data: data,
  });
};

// PUT 请求
export const put = (url: string, data?: any) => {
  return request(url, {
    method: 'PUT',
    data: data,
  });
};

// DELETE 请求
export const del = (url: string) => {
  return request(url, { method: 'DELETE' });
};