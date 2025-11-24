// plugin/pages/hello-page.js
Page({
  data: {
    messages: [
      { type: 'other', text: '你好，我是AI助手，有什么我可以帮助你的吗？' }
    ],
    input: '',
    isLoading: false,
    lastId: '',
    statusBarHeight: 44,
    keyboardHeight: 0,
    apiBaseUrl: 'http://127.0.0.1:8000'
  },

  onLoad() {
    const sys = wx.getSystemInfoSync()
    this.setData({
      statusBarHeight: sys.statusBarHeight || 44
    })
    
    wx.onKeyboardHeightChange(res => {
      this.setData({ keyboardHeight: res.height })
      this.scrollBottom()
    })
    
    this.scrollBottom()
  },

  onUnload() {
    wx.offKeyboardHeightChange()
  },

  goBack() {
    wx.navigateBack()
  },

  onInput(e) {
    this.setData({ input: e.detail.value })
  },

  scrollBottom() {
    if (!this.data.messages.length) return
    this.setData({ lastId: '' })
    setTimeout(() => {
      this.setData({ lastId: 'msg-' + (this.data.messages.length - 1) })
    }, 100)
  },

  send() {
    const t = this.data.input.trim()
    if (!t || this.data.isLoading) {
      return
    }

    // 添加用户消息
    const newMessages = [...this.data.messages, { type: 'user', text: t }]
    this.setData({
      messages: newMessages,
      input: '',
      isLoading: true
    })
    this.scrollBottom()

    // 添加助手消息占位
    const assistantMsgIndex = newMessages.length
    newMessages.push({ type: 'other', text: '' })
    this.setData({ messages: newMessages })

    // 构建消息列表
    const chatMessages = newMessages
      .filter(m => m.type === 'user' || m.type === 'other')
      .slice(0, -1)
      .map(m => ({
        role: m.type === 'user' ? 'user' : 'assistant',
        content: m.text
      }))

    // 发送请求
    const requestTask = wx.request({
      url: `${this.data.apiBaseUrl}/api/agent/chat`,
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
      enableChunked: true,
      timeout: 120000,
      
      success: (res) => {
        const msgs = this.data.messages
        if (!msgs[assistantMsgIndex].text && res.statusCode === 200 && res.data) {
          msgs[assistantMsgIndex].text = typeof res.data === 'string' ? res.data : String(res.data)
        }
        if (!msgs[assistantMsgIndex].text || msgs[assistantMsgIndex].text.trim() === '') {
          msgs[assistantMsgIndex].text = '(无响应)'
        }
        
        this.setData({
          messages: msgs,
          isLoading: false
        })
        this.scrollBottom()
      },
      fail: (err) => {
        console.error('wx.request 失败:', err)
        const msgs = this.data.messages
        msgs[assistantMsgIndex].text = `连接失败: ${err.errMsg || '请检查后端服务'}`
        this.setData({
          messages: msgs,
          isLoading: false
        })
        this.scrollBottom()
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
        const msgs = this.data.messages
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const content = line.substring(6)
            if (content === '[DONE]') {
              this.setData({ isLoading: false })
              this.scrollBottom()
              break
            } else if (content.startsWith('[ERROR]')) {
              msgs[assistantMsgIndex].text += '\n' + content
            } else if (content.trim()) {
              msgs[assistantMsgIndex].text += content
              this.setData({ messages: msgs })
              this.scrollBottom()
            }
          }
        }
      })
    } catch (err) {
      console.error('设置 onChunkReceived 失败:', err)
    }
  }
})
