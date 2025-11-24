// 请求封装（微信小程序插件内使用 wx.request）
const BASE_URL = 'http://127.0.0.1:8000';

function request(path, options = {}) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${BASE_URL}${path}`,
      method: options.method || 'GET',
      data: options.data,
      header: Object.assign({
        'Content-Type': 'application/json'
      }, options.header || {}),
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else {
          reject(new Error(`请求失败: ${res.statusCode}`));
        }
      },
      fail(err) {
        reject(new Error(err.errMsg || '网络请求失败'));
      }
    });
  });
}

// 调用后端 SSE 接口（text/event-stream），在小程序环境无法逐段流式读取，
// 这里采用兼容方案：等待请求完成后一次性解析返回的文本，按行分发 data: 事件。
function sse(path, { method = 'POST', data, headers = {}, onMessage } = {}) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${BASE_URL}${path}`,
      method,
      data,
      header: Object.assign({
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream'
      }, headers),
      responseType: 'text',
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          const text = typeof res.data === 'string' ? res.data : '';
          let collected = '';
          if (text) {
            const chunks = text.split(/\n\n/);
            chunks.forEach(line => {
              const m = line.match(/^data: (.*)$/);
              if (m) {
                const payload = m[1];
                if (payload === '[DONE]') {
                  // 结束标记
                } else {
                  collected += payload;
                  if (typeof onMessage === 'function') {
                    try { onMessage(payload); } catch (_) {}
                  }
                }
              }
            });
          }
          resolve(collected);
        } else {
          reject(new Error(`SSE请求失败: ${res.statusCode}`));
        }
      },
      fail(err) {
        reject(new Error(err.errMsg || 'SSE网络请求失败'));
      }
    });
  });
}

module.exports = {
  BASE_URL,
  request,
  sse,
};
