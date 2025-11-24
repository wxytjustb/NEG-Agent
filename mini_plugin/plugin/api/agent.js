// Agent 相关接口封装
const { request, sse } = require('../utls/require');

// 健康检查
function ping() {
  return request('/ping');
}

/**
 * Agent 对话（后端为 SSE 输出），在小程序内一次性解析并回调每段 data: 内容。
 * @param {Object} params
 * @param {Array<{role:string, content:string}>} params.messages
 * @param {string} [params.provider] - 'ollama' | 'deepseek'
 * @param {number} [params.temperature]
 * @param {number} [params.max_tokens]
 * @param {string} [params.model]
 * @param {(chunk:string)=>void} [params.onMessage] - 每段内容回调
 * @returns {Promise<string>} - 汇总文本
 */
function chat({ messages = [], provider = 'ollama', temperature = 0.7, max_tokens = 2000, model, onMessage } = {}) {
  return sse('/api/agent/chat', {
    method: 'POST',
    data: { messages, provider, temperature, max_tokens, model },
    headers: { 'Accept': 'text/event-stream' },
    onMessage,
  });
}

module.exports = {
  ping,
  chat,
};
