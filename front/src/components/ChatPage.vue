<template>
  <view class="wx-page" :style="{ '--status': statusBarHeight + 'px' }">
    <view class="wx-header" :style="{ paddingTop: statusBarHeight + 'px' }">
      <view class="wx-header-bar">
        <view class="wx-back" @click="goBack"><uni-icons type="back" size="22" color="#333"></uni-icons></view>
        <text class="wx-title">{{ title }}</text>
        <view class="wx-more"><uni-icons type="more" size="22" color="#333"></uni-icons></view>
      </view>
    </view>

    <view class="wx-content">
      <scroll-view class="wx-scroll" scroll-y scroll-with-animation :scroll-into-view="lastId">
        <view v-for="(m,i) in messages" :key="i" :id="'msg-'+i" class="wx-msg" :class="m.type">
          <view class="wx-bubble" :class="m.type">
            <view v-if="isLoading && m.type==='other' && i===messages.length-1 && (!m.text || !m.text.trim())" class="wx-typing">
              <view class="dot"></view>
              <view class="dot"></view>
              <view class="dot"></view>
            </view>
            <text v-else class="wx-text">{{ m.text }}</text>
          </view>
        </view>
      </scroll-view>
    </view>

    <view class="wx-input" :style="{ bottom: keyboardHeight + 'px' }">
      <textarea 
        class="wx-textarea" 
        v-model="input" 
        placeholder="发送消息"
        :auto-height="true"
        :show-confirm-bar="false"
        :adjust-position="false"
        cursor-spacing="12"
        maxlength="600"
        :disabled="isLoading"
      />
      <view class="wx-right">
        <button class="wx-send" :class="{ disabled: !canSend || isLoading }" :disabled="!canSend || isLoading" @click="send">
          {{ isLoading ? '加载中...' : '发送' }}
        </button>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, onMounted, nextTick, onUnmounted, computed, watch } from 'vue'

// API 配置
const API_BASE_URL = 'http://127.0.0.1:8000'
const CHAT_ENDPOINT = '/api/agent/chat'

const title = ref('AI助手')
const messages = ref([
  { type: 'other', text: '你好，我是AI助手，有什么我可以帮助你的吗？' }
])
const input = ref('')
const isLoading = ref(false)
const canSend = computed(() => !!input.value.trim() && !isLoading.value)
const lastId = ref('')
const statusBarHeight = ref(0)
const keyboardHeight = ref(0)

const goBack = () => { uni.navigateBack() }

const scrollBottom = () => {
  if (!messages.value.length) return
  lastId.value = ''
  nextTick(() => { lastId.value = 'msg-' + (messages.value.length - 1) })
}

const send = async () => {
  const t = input.value.trim()
  if (!t || isLoading.value) {
    return
  }

  // 添加用户消息
  messages.value.push({ type: 'user', text: t })
  input.value = ''
  scrollBottom()

  isLoading.value = true
  let assistantMessage = { type: 'other', text: '' }
  messages.value.push(assistantMessage)

  try {
    // 构建消息列表，包含所有历史消息
    const chatMessages = messages.value
      .filter(m => m.type === 'user' || m.type === 'other')
      .slice(0, -1) // 排除正在构建的助手消息
      .map(m => ({
        role: m.type === 'user' ? 'user' : 'assistant',
        content: m.text
      }))

    

    // 使用微信原生 wx.request 支持真正的流式传输
    // #ifdef MP-WEIXIN
    const requestTask = wx.request({
      url: `${API_BASE_URL}${CHAT_ENDPOINT}`,
      method: 'POST',
      header: {
        'Content-Type': 'application/json'
      },
      data: {
        messages: chatMessages,
        provider: 'ollama',
        temperature: 0.7,
        max_tokens: 2000,
        stream: true
      },
      enableChunked: true,  // 微信原生API的分块传输
      timeout: 120000,
      
      success: (res) => {
        if (!assistantMessage.text && res.statusCode === 200 && res.data) {
          assistantMessage.text = typeof res.data === 'string' ? res.data : String(res.data)
        }
        if (!assistantMessage.text || assistantMessage.text.trim() === '') {
          assistantMessage.text = '(无响应)'
        }
        
        isLoading.value = false
        scrollBottom()
      },
      fail: (err) => {
        console.error('wx.request 失败:', err)
        assistantMessage.text = `连接失败: ${err.errMsg || '请检查后端服务'}`
        isLoading.value = false
        scrollBottom()
      }
    })
    try {
      requestTask.onChunkReceived((res) => {
        let chunkText = ''
        if (typeof res === 'string') {
          chunkText = res
        } else if (res && typeof res === 'object') {
          const buf = res.data || res.chunk || res
          if (buf instanceof ArrayBuffer) {
            chunkText = new TextDecoder('utf-8').decode(buf)
          } else if (buf instanceof Uint8Array) {
            chunkText = new TextDecoder('utf-8').decode(buf)
          } else {
            chunkText = String(buf)
          }
        } else if (res instanceof ArrayBuffer) {
          chunkText = new TextDecoder('utf-8').decode(res)
        } else {
          chunkText = String(res)
        }

        const lines = chunkText.split('\n')
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const content = line.substring(6)
            if (content === '[DONE]') {
              isLoading.value = false
              scrollBottom()
              break
            } else if (content.startsWith('[ERROR]')) {
              assistantMessage.text += '\n' + content
            } else if (content.trim()) {
              assistantMessage.text += content
              scrollBottom()
            }
          }
        }
      })
    } catch {}
    // #endif
    
    
  } catch (error) {
    console.error('请求异常:', error)
    assistantMessage.text = `错误: ${error.message || '未知错误'}`
    isLoading.value = false
    scrollBottom()
  }
}

onMounted(() => {
  const sys = uni.getSystemInfoSync()
  statusBarHeight.value = sys.statusBarHeight || 44
  uni.onKeyboardHeightChange(res => { keyboardHeight.value = res.height; scrollBottom() })
  scrollBottom()
})

onUnmounted(() => { uni.offKeyboardHeightChange() })

watch(messages, () => { nextTick(() => scrollBottom()) }, { deep: true })
</script>

<style scoped>
.wx-page { width: 100vw; height: 100vh; background: #f3f3f3; display: flex; flex-direction: column; }
.wx-header { position: fixed; left: 0; right: 0; top: 0; background: #fff; border-bottom: 1rpx solid #ededed; z-index: 10; }
.wx-header-bar { height: 88rpx; display: flex; align-items: center; justify-content: space-between; padding: 0 24rpx; }
.wx-back, .wx-more { width: 64rpx; height: 64rpx; display: flex; align-items: center; justify-content: center; }
.wx-title { font-size: 34rpx; color: #111; }
.wx-content { flex: 1; padding-top: calc(var(--status) + 88rpx); padding-bottom: 120rpx; }
.wx-scroll { height: 100%; }
.wx-msg { width: 100%; padding: 12rpx 24rpx; box-sizing: border-box; display: flex; }
.wx-msg.other { justify-content: flex-start; }
.wx-msg.user { justify-content: flex-end; }
.wx-bubble { max-width: 72%; padding: 18rpx 22rpx; border-radius: 18rpx; font-size: 28rpx; line-height: 1.6; position: relative; }
.wx-bubble.other { background: #fff; color: #121506; border: 1rpx solid #e5e5e5; }
.wx-bubble.user { background: #95ec69; color: #121506; }
.wx-bubble.user::after { content: ""; position: absolute; right: -10rpx; top: 26rpx; width: 0; height: 0; border-left: 12rpx solid #95ec69; border-top: 10rpx solid transparent; border-bottom: 10rpx solid transparent; }
.wx-bubble.other::before { content: ""; position: absolute; left: -10rpx; top: 26rpx; width: 0; height: 0; border-right: 12rpx solid #fff; border-top: 10rpx solid transparent; border-bottom: 10rpx solid transparent; }
.wx-text { word-break: break-word; }
.wx-typing { display: flex; align-items: center; gap: 8rpx; height: 36rpx; }
.wx-typing .dot { width: 10rpx; height: 10rpx; border-radius: 50%; background: #bbb; animation: wx-blink 1s infinite ease-in-out; }
.wx-typing .dot:nth-child(2) { animation-delay: 0.2s; }
.wx-typing .dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes wx-blink { 0%, 80%, 100% { opacity: 0.2; transform: scale(0.9); } 40% { opacity: 1; transform: scale(1); } }
.wx-input { position: fixed; left: 0; right: 0; bottom: 0; background: #f8f8f8; border-top: 1rpx solid #e6e6e6; padding: 12rpx 16rpx; display: flex; align-items: flex-end; gap: 12rpx; z-index: 11; }
.wx-icon-btn { width: 72rpx; height: 72rpx; border-radius: 36rpx; display: flex; align-items: center; justify-content: center; }
.wx-textarea { flex: 1; height: 72rpx; min-height: 72rpx; max-height: 300rpx; box-sizing: border-box; background: #fff; border: 1rpx solid #e6e6e6; border-radius: 15rpx; padding: 20rpx 24rpx; font-size: 28rpx; line-height: 36rpx; overflow-y: hidden; }
.wx-right { display: flex; align-items: center; }
.wx-send { min-width: 140rpx; height: 72rpx; padding: 0 28rpx; border-radius: 15rpx; background: #07c160; display: flex; align-items: center; justify-content: center; color: #fff; border: none; font-size: 28rpx; font-weight: 600; }
.wx-send.disabled { background: #c9c9c9; color: #fff; }
</style>
