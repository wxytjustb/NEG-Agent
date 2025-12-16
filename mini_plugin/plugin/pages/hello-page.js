// plugin/pages/hello-page.js
Page({
  data: {
    messages: [
      { type: 'other', text: '你好，我是AI助手，有什么我可以帮助你的吗？' }
    ],
    input: '',
    isLoading: false,
    scrollTop: 0,
    scrollIntoView: '',
    statusBarHeight: 44,
    keyboardHeight: 0,
    apiBaseUrl: 'http://127.0.0.1:8000',
    sessionToken: '',
    isInitializing: false,
    userScrolling: false,  // 用户是否正在滚动
    autoScroll: true  // 是否自动滚动
  },

  onLoad() {
    const sys = wx.getSystemInfoSync()
    this.setData({
      statusBarHeight: sys.statusBarHeight || 44
    })
    
    // 初始化会话
    this.initSession()
  },


  // 初始化会话
  initSession() {
    this.setData({ isInitializing: true })
    
    const accessToken = wx.getStorageSync('access_token') || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJJRCI6MzM0LCJPcGVuSUQiOiJvdEdjSTdFQXhsUUJQMWE1WlhLNVJ1cTloQ2UwIiwiQnVmZmVyVGltZSI6ODY0MDAsImlzcyI6InFtUGx1cyIsImF1ZCI6WyJBUFAiXSwiZXhwIjoxNzY0NTk3NTM3LCJuYmYiOjE3NjM5OTI3Mzd9.aOGj3aCwxi7ZvpgSuXxuj-b9eHx4OGnFSV9wqCo-98w'
    
    wx.request({
      url: `${this.data.apiBaseUrl}/api/agent/init?access_token=${accessToken}`,
      method: 'POST',
      header: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
      success: (res) => {
        if (res.statusCode === 200 && res.data && res.data.data) {
          const sessionToken = res.data.data.session_token
          this.setData({
            sessionToken: sessionToken,
            isInitializing: false
          }, () => {
            this.scrollBottom()
          })
          console.log('会话初始化成功', sessionToken)
        } else {
          console.error('会话初始化失败', res)
          this.setData({ isInitializing: false })
          wx.showToast({
            title: '认证失败，请重新登录',
            icon: 'none'
          })
        }
      },
      fail: (err) => {
        console.error('会话初始化请求失败:', err)
        this.setData({ isInitializing: false })
        wx.showToast({
          title: '连接失败，请检查网络',
          icon: 'none'
        })
      }
    })
  },

  goBack() {
    wx.navigateBack()
  },

  onInput(e) {
    this.setData({ input: e.detail.value })
  },

  onTouchStart(e) {
    // 用户开始触摸滚动区域，禁用自动滚动
    this.setData({
      autoScroll: false,
      userScrolling: true
    })
  },

  onTouchEnd(e) {
    // 用户结束触摸，保持禁用状态
    // 只有当用户发送新消息时才会重新启用
  },

  // 简化滚动逻辑 - 模仿 ChatPage.vue 的实现
  scrollBottom() {
    // 只有在允许自动滚动时才执行
    if (!this.data.autoScroll) {
      return
    }
    
    // 强制滚动到超大值
    this.setData({ 
      scrollTop: 999999,
      scrollIntoView: ''  // 清空 scrollIntoView
    })
  },

  send() {
    const t = this.data.input.trim()
    if (!t || this.data.isLoading || !this.data.sessionToken) {
      if (!this.data.sessionToken) {
        wx.showToast({
          title: '会话未初始化，请稍候',
          icon: 'none'
        })
      }
      return
    }

    // 发送新消息时，重新启用自动滚动
    this.setData({ autoScroll: true, userScrolling: false })

    // 添加用户消息
    const newMessages = [...this.data.messages, { type: 'user', text: t }]
    this.setData({
      messages: newMessages,
      input: '',
      isLoading: true
    }, () => {
      setTimeout(() => this.scrollBottom(), 100)
    })

    // 添加助手消息占位
    const assistantMsgIndex = newMessages.length
    newMessages.push({ type: 'other', text: '' })
    this.setData({ messages: newMessages }, () => {
      setTimeout(() => this.scrollBottom(), 100)
    })

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
      url: `${this.data.apiBaseUrl}/api/agent/chat?session_token=${this.data.sessionToken}`,
      method: 'POST',
      header: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.data.sessionToken}`
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
        }, () => {
          setTimeout(() => this.scrollBottom(), 100)
        })
      },
      fail: (err) => {
        console.error('wx.request 失败:', err)
        const msgs = this.data.messages
        msgs[assistantMsgIndex].text = `连接失败: ${err.errMsg || '请检查后端服务'}`
        this.setData({
          messages: msgs,
          isLoading: false
        }, () => {
          setTimeout(() => this.scrollBottom(), 100)
        })
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
        let hasUpdate = false
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const content = line.substring(6)
            if (content === '[DONE]') {
              this.setData({ isLoading: false }, () => {
                setTimeout(() => this.scrollBottom(), 100)
              })
              break
            } else if (content.startsWith('[ERROR]')) {
              msgs[assistantMsgIndex].text += '\n' + content
              hasUpdate = true
            } else if (content.trim()) {
              msgs[assistantMsgIndex].text += content
              hasUpdate = true
            }
          }
        }
        
        if (hasUpdate) {
          this.setData({ messages: msgs })
          // 流式更新时立即滚动
          this.scrollBottom()
        }
      })
    } catch (err) {
      console.error('设置 onChunkReceived 失败:', err)
    }
  }
})