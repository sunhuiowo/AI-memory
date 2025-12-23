// DOM元素和全局函数定义
// 全局定义updateResponseTime函数，避免任何地方调用时出错
/**
 * 全局响应时间更新函数（已禁用）
 * 
 * 此函数故意留空，以避免JavaScript错误
 */
function updateResponseTime() {
  console.log('全局updateResponseTime函数被调用，但已被禁用');
}

// 全局变量定义
/** 聊天表单元素 */
const form = document.getElementById("chat-form");
/** 聊天记录显示区域 */
const chatLog = document.getElementById("chat-log");
/** 项目摘要显示区域 */
const projectSummary = document.getElementById("project-summary");
/** 专家列表显示区域 */
const specialistList = document.getElementById("specialist-list");
/** 记忆使用情况显示区域 */
const memoryUsage = document.getElementById("memory-usage");
/** 协作者显示区域 */
const collaborators = document.getElementById("collaborators");
/** 状态指示器 */
const statusIndicator = document.getElementById("status-indicator");
/** 延迟标签 */
const latencyLabel = document.getElementById("latency-label");
// 确保responseTime变量有一个默认值，避免引用错误
const responseTime = latencyLabel || { textContent: '', style: {} };
/** 清除按钮 */
const clearButton = document.getElementById("btn-clear");
/** 消息输入框 */
const messageInput = document.querySelector("textarea[name='message']");
/** 用户ID输入框 */
const userIdInput = document.querySelector("input[name='user_id']");
/** 会话ID输入框 */
const sessionIdInput = document.querySelector("input[name='session_id']");

// 增强的状态管理
/**
 * 应用状态管理对象
 * 
 * 用于管理应用的全局状态，包括聊天历史、加载状态等
 */
const state = {
  history: [],                    // 聊天历史记录
  isLoading: false,               // 是否正在加载
  lastInteractionTime: null,      // 最后交互时间
  conversationStats: {            // 会话统计信息
    messages: 0,                  // 消息数量
    responseTime: 0               // 响应时间
  }
};

// 添加toast通知容器
/**
 * 创建并添加toast通知容器
 * 
 * 用于显示临时通知消息
 */
const toastContainer = document.createElement('div');
toastContainer.className = 'toast-container';
document.body.appendChild(toastContainer);

/**
 * 设置状态指示器
 * 
 * @param {string} text - 状态文本
 * @param {string} variant - 状态变体（idle、busy、error）
 */
function setStatus(text, variant = "idle") {
  // 添加过渡效果
  statusIndicator.classList.remove('status-transition');
  void statusIndicator.offsetWidth; // 强制重排以触发过渡
  statusIndicator.classList.add('status-transition');
  
  statusIndicator.textContent = text;
  statusIndicator.setAttribute('data-status', variant);
  statusIndicator.classList.remove("busy", "error");
  
  if (variant === "busy") {
    statusIndicator.classList.add("busy");
    // 添加脉冲动画
    if (!statusIndicator.querySelector('.pulse-dot')) {
      const dot = document.createElement('span');
      dot.className = 'pulse-dot';
      statusIndicator.prepend(dot);
    }
  } else {
    // 移除非忙碌状态的脉冲点
    const dot = statusIndicator.querySelector('.pulse-dot');
    if (dot) dot.remove();
  }
  
  if (variant === "error") statusIndicator.classList.add("error");
}

/**
 * 显示toast通知
 * 
 * @param {string} message - 通知消息
 * @param {string} type - 通知类型（info、success、error）
 */
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast-notification toast-${type}`;
  toast.textContent = message;
  
  toastContainer.appendChild(toast);
  
  // 显示动画
  setTimeout(() => {
    toast.style.opacity = '1';
    toast.style.transform = 'translateY(0)';
  }, 10);
  
  // 延迟后自动移除
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(-20px)';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

/**
 * 格式化相对时间
 * 
 * @param {number} timestamp - 时间戳
 * @returns {string} 格式化后的相对时间
 */
function formatRelativeTime(timestamp) {
  const now = Date.now();
  const diff = now - timestamp;
  const seconds = Math.floor(diff / 1000);
  
  if (seconds < 60) return '刚刚';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分钟前`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}小时前`;
  return new Date(timestamp).toLocaleDateString();
}

/**
 * 渐进式打字动画
 * 
 * @param {HTMLElement} element - 目标元素
 * @param {string} text - 要显示的文本
 * @param {number} speed - 打字速度（毫秒/字符）
 */
function progressiveType(element, text, speed = 20) {
  let index = 0;
  
  function typeNextChar() {
    if (index < text.length) {
      element.textContent += text.charAt(index);
      index++;
      scrollToBottom(); // 打字时自动滚动到底部
      setTimeout(typeNextChar, speed);
    }
  }
  
  typeNextChar();
}

/**
 * 平滑滚动到底部
 */
function scrollToBottom() {
  chatLog.scrollTo({
    top: chatLog.scrollHeight,
    behavior: 'smooth'
  });
}

/**
 * 创建打字指示器
 * 
 * @returns {HTMLElement} 打字指示器元素
 */
function createTypingIndicator() {
  const item = document.createElement("li");
  item.id = 'typing-indicator';
  item.className = `chat-item assistant typing`;
  const header = document.createElement("header");
  header.textContent = "项目大脑";
  const body = document.createElement("p");
  body.className = 'typing-animation';
  
  // 创建打字点
  for (let i = 0; i < 3; i++) {
    const dot = document.createElement('span');
    dot.className = `typing-dot dot-${i+1}`;
    body.appendChild(dot);
  }
  
  item.appendChild(header);
  item.appendChild(body);
  return item;
}

/**
 * 渲染消息（带动画和打字效果）
 */
function renderMessages() {
  // 如果有打字指示器，跳过重新渲染
  if (document.getElementById('typing-indicator')) return;
  
  // 只渲染新消息
  state.history.forEach((entry, index) => {
    // 如果已渲染，跳过
    if (document.querySelector(`[data-message-id="${index}"]`)) return;
    
    const item = document.createElement("li");
    item.className = `chat-item ${entry.role}`;
    item.setAttribute('data-message-id', index);
    item.style.opacity = '0';
    item.style.transform = 'translateY(20px)';
    
    const header = document.createElement("header");
    header.textContent = entry.label;
    
    const body = document.createElement("p");
    
    // 添加时间戳
    const timestamp = document.createElement("span");
    timestamp.className = 'message-timestamp';
    timestamp.textContent = formatRelativeTime(entry.timestamp || Date.now());
    header.appendChild(timestamp);
    
    // 为最新的助手消息添加渐进式打字效果
    if (entry.role === 'assistant' && index === state.history.length - 1) {
      body.textContent = '';
      progressiveType(body, entry.content);
    } else {
      body.textContent = entry.content;
    }
    
    item.appendChild(header);
    item.appendChild(body);
    chatLog.appendChild(item);
    
    // 添加交错延迟动画效果
    setTimeout(() => {
      item.style.opacity = '1';
      item.style.transform = 'translateY(0)';
      item.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
    }, 50 * index);
  });
  
  scrollToBottom();
}

/**
 * 为项目大脑摘要和专家大脑反馈添加动态折叠/展开功能
 * 
 * @param {HTMLElement} element - 要添加折叠/展开功能的元素
 */
function makeCollapsible(element) {
  if (!element) return;
  
  // 检查元素是否已经有折叠功能
  if (element.classList.contains('collapsible-content')) return;
  
  const maxHeight = 120; // 设置最大高度
  
  // 保存原始内容
  const originalContent = element.textContent;
  const originalStyle = {
    height: element.style.height,
    overflow: element.style.overflow
  };
  
  // 创建折叠/展开按钮
  const toggleButton = document.createElement('button');
  toggleButton.className = 'toggle-button';
  toggleButton.innerHTML = '展开 <span class="toggle-icon">▼</span>';
  toggleButton.style.marginTop = '8px';
  toggleButton.style.background = 'rgba(255, 255, 255, 0.1)';
  toggleButton.style.border = 'none';
  toggleButton.style.borderRadius = '4px';
  toggleButton.style.padding = '4px 8px';
  toggleButton.style.color = 'var(--text-primary)';
  toggleButton.style.cursor = 'pointer';
  toggleButton.style.fontSize = '12px';
  toggleButton.style.display = 'flex';
  toggleButton.style.alignItems = 'center';
  toggleButton.style.gap = '4px';
  
  // 创建包装容器
  const wrapper = document.createElement('div');
  wrapper.className = 'collapsible-wrapper';
  
  // 移动元素到包装容器中
  const parent = element.parentNode;
  const sibling = element.nextSibling;
  parent.insertBefore(wrapper, sibling);
  wrapper.appendChild(element);
  wrapper.appendChild(toggleButton);
  
  // 设置元素样式
  element.className = 'collapsible-content';
  element.style.overflow = 'hidden';
  element.style.transition = 'max-height 0.3s ease';
  
  // 判断是否需要折叠
  let isCollapsed = false;
  const originalHeight = element.scrollHeight;
  
  if (originalHeight > maxHeight) {
    element.style.maxHeight = `${maxHeight}px`;
    isCollapsed = true;
  } else {
    element.style.maxHeight = `${originalHeight}px`;
    toggleButton.style.display = 'none'; // 内容不长时隐藏按钮
  }
  
  // 添加点击事件
  toggleButton.addEventListener('click', () => {
    isCollapsed = !isCollapsed;
    
    if (isCollapsed) {
      element.style.maxHeight = `${maxHeight}px`;
      toggleButton.innerHTML = '展开 <span class="toggle-icon">▼</span>';
    } else {
      element.style.maxHeight = `${originalHeight}px`;
      toggleButton.innerHTML = '收起 <span class="toggle-icon">▲</span>';
    }
  });
}

function renderInsights(result) {
  // Add fade-out animation for current content
  const panels = [projectSummary, specialistList];
  panels.forEach(panel => {
    if (panel) {
      panel.style.opacity = '0.5';
      panel.style.transform = 'translateY(5px)';
      panel.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    }
  });
  
  // Update content with a small delay to show transition
  setTimeout(() => {
    if (projectSummary) {
      projectSummary.textContent = result.project_summary || "暂无摘要";
      // Animate back in
      projectSummary.style.opacity = '1';
      projectSummary.style.transform = 'translateY(0)';
      
      // 添加折叠/展开功能
      makeCollapsible(projectSummary);
    }
    
    if (specialistList) {
      specialistList.innerHTML = "";
      
      if (result.specialists?.length) {
        result.specialists.forEach((spec, index) => {
          const li = document.createElement("li");
          li.innerHTML = `<strong>${spec.agent_name}</strong><p>${spec.content}</p>`;
          li.style.opacity = '0';
          li.style.transform = 'translateX(-10px)';
          specialistList.appendChild(li);
          
          // Staggered animation
          setTimeout(() => {
            li.style.opacity = '1';
            li.style.transform = 'translateX(0)';
            li.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            
            // 为每个专家反馈添加折叠/展开功能
            const contentElement = li.querySelector('p');
            if (contentElement) {
              makeCollapsible(contentElement);
            }
          }, 100 + (index * 100));
        });
      } else {
        specialistList.innerHTML = '<li class="muted">暂无专家反馈</li>';
      }
      
      // Animate container back in
      specialistList.style.opacity = '1';
      specialistList.style.transform = 'translateY(0)';
    }
    
    if (memoryUsage) {
      memoryUsage.textContent = result.metadata.memory_used === "true"
        ? `${result.metadata.memories_count} 条`
        : "未引用";
    }
    
    if (collaborators) {
      collaborators.textContent = result.metadata.collaborators || "—";
    }
    
    // Show toast notification for new insights
    showToast('项目洞察已更新', 'success');
  }, 300);
}

/**
 * 发送消息到API并获取响应
 * 
 * @param {string} message - 消息内容
 * @param {string} userId - 用户ID
 * @param {string} sessionId - 会话ID
 * @returns {Promise<object>} API响应数据
 */
async function sendMessage(message, userId, sessionId) {
  // 获取当前选择的聊天模式和目标专家
  const chatMode = document.querySelector('input[name="chatMode"]:checked')?.value;
  const specialistSelect = document.getElementById('specialistSelect');
  const targetAgent = chatMode === 'specialist' && specialistSelect?.value ? specialistSelect.value : null;
  
  const payload = {
    message,
    user_id: userId,
    session_id: sessionId,
    target_agent: targetAgent
  };
  
  const t0 = performance.now();
  
  // Show network activity indicator
  if (navigator.connection) {
    const networkType = navigator.connection.effectiveType || 'unknown';
    console.log(`Network type: ${networkType}`);
  }
  
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    
    if (!response.ok) {
      throw new Error(await response.text());
    }
    
    const data = await response.json();
    const t1 = performance.now();
    const responseTime = t1 - t0;
    
    // Update latency display with animation
    if (latencyLabel) {
      latencyLabel.style.transition = 'all 0.3s ease';
      latencyLabel.style.opacity = '0.5';
      
      setTimeout(() => {
        latencyLabel.textContent = `延迟 ${responseTime.toFixed(0)} ms`;
        latencyLabel.style.opacity = '1';
      }, 200);
    }
    
    // Update conversation stats
    state.conversationStats.responseTime = responseTime;
    state.conversationStats.messages++;
    
    return data;
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}

/**
 * 添加消息到历史记录
 * 
 * @param {string} role - 角色（user或assistant）
 * @param {string} label - 标签（显示在消息头部）
 * @param {string} content - 消息内容
 */
function appendHistory(role, label, content) {
  const message = {
    role,
    label,
    content,
    timestamp: Date.now()
  };
  
  state.history.push(message);
  
  // Limit history size but keep more messages
  const MAX_HISTORY = 30;
  if (state.history.length > MAX_HISTORY) {
    // Keep last MAX_HISTORY messages
    state.history = state.history.slice(-MAX_HISTORY);
  }
  
  // Save history to localStorage (optional)
  try {
    localStorage.setItem('chat_history', JSON.stringify(state.history.slice(-10)));
  } catch (e) {
    console.warn('Failed to save history to localStorage', e);
  }
  
  renderMessages();
}

/**
 * 表单提交处理（增强用户体验）
 */
form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  
  const formData = new FormData(form);
  const message = formData.get("message")?.toString().trim();
  if (!message || state.isLoading) return;

  const userId = formData.get("user_id")?.toString().trim() || "user-" + Math.random().toString(36).substr(2, 9);
  const sessionId = formData.get("session_id")?.toString().trim() || "session-" + Date.now();

  // Update state
  state.isLoading = true;
  state.lastInteractionTime = Date.now();
  
  // Disable form during processing
  const submitButton = form.querySelector("button[type='submit']");
  if (submitButton) {
    submitButton.disabled = true;
    submitButton.classList.add('button-loading');
  }
  
  // Add user message with animation
  appendHistory("user", `用户 ${userId}`, message);
  setStatus("项目大脑分析中…", "busy");
  
  // Add typing indicator
  const typingIndicator = createTypingIndicator();
  chatLog.appendChild(typingIndicator);
  scrollToBottom();

  try {
    // Add timeout for long requests
    const timeoutPromise = new Promise((_, reject) => {
      setTimeout(() => reject(new Error('请求超时')), 3000000);
    });
    
    const result = await Promise.race([
      sendMessage(message, userId, sessionId),
      timeoutPromise
    ]);
    
    // Remove typing indicator
    typingIndicator.remove();
    
    // Add assistant response with typing animation
    appendHistory("assistant", `项目大脑 / ${result.metadata.agent_id}`, result.content);
    
    // Update insights with animation
    renderInsights(result);
    
    // Reset form with focus on message input
    form.reset();
    if (messageInput) messageInput.focus();
    
    // Show success toast
    showToast('回复已生成', 'success');
    
  } catch (error) {
    console.error('Chat Error:', error);
    
    // Remove typing indicator
    if (typingIndicator && typingIndicator.parentNode) {
      typingIndicator.remove();
    }
    
    // Add error message to history
    appendHistory("assistant", "系统", `⚠️ ${error.message || '系统暂时不可用，请稍后再试。'}`);
    
    // Show error state and toast
    setStatus("服务异常", "error");
    showToast('发生错误，请重试', 'error');
  } finally {
    // Reset loading state
    state.isLoading = false;
    
    // Enable form again
    if (submitButton) {
      submitButton.disabled = false;
      submitButton.classList.remove('button-loading');
    }
    
    // Reset status if not in error state
    if (!statusIndicator.classList.contains("error")) {
      setStatus("完成");
    }
  }
});

/**
 * 清除按钮点击事件处理（带确认和动画）
 */
clearButton?.addEventListener("click", () => {
  // Confirm before clearing
  if (confirm('确定要清除对话历史吗？')) {
    // Animate messages out
    const messages = chatLog.querySelectorAll('.chat-item');
    messages.forEach((msg, index) => {
      setTimeout(() => {
        msg.style.opacity = '0';
        msg.style.transform = 'translateX(-20px)';
        msg.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
      }, index * 50);
    });
    
    // Clear after animation
    setTimeout(() => {
      state.history = [];
      chatLog.innerHTML = '';
      
      // Reset other elements
      if (projectSummary) projectSummary.textContent = "尚未生成";
      if (specialistList) specialistList.innerHTML = '<li class="muted">等待分析...</li>';
      if (memoryUsage) memoryUsage.textContent = "—";
      if (collaborators) collaborators.textContent = "—";
      if (latencyLabel) latencyLabel.textContent = "—";
      
      // Show confirmation toast
      showToast('对话已清除', 'info');
    }, messages.length * 50 + 200);
  }
});

/**
 * 设置键盘快捷键
 */
function setupKeyboardShortcuts() {
  document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + Enter to send message
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      const message = messageInput?.value.trim();
      if (message && form) {
        form.dispatchEvent(new Event('submit'));
      }
    }
    
    // Esc to clear input
    if (e.key === 'Escape' && messageInput === document.activeElement) {
      e.preventDefault();
      messageInput.value = '';
    }
    
    // Ctrl/Cmd + L to focus message input
    if ((e.ctrlKey || e.metaKey) && e.key === 'l') {
      e.preventDefault();
      messageInput?.focus();
    }
  });
}

/**
 * 设置空闲状态处理
 */
function setupIdleState() {
  setInterval(() => {
    if (!state.isLoading && state.lastInteractionTime) {
      const idleTime = Date.now() - state.lastInteractionTime;
      // After 2 minutes of inactivity
      if (idleTime > 120000) {
        setStatus('待机模式', 'idle');
      }
    }
  }, 30000); // Check every 30 seconds
}

/**
 * 加载保存的历史记录（如果可用）
 */
function loadSavedHistory() {
  try {
    const saved = localStorage.getItem('chat_history');
    if (saved) {
      const parsed = JSON.parse(saved);
      if (Array.isArray(parsed)) {
        // Load only the last few messages
        state.history = parsed.slice(-5);
        renderMessages();
      }
    }
  } catch (e) {
    console.warn('Failed to load saved history', e);
  }
}

// Initialize the application
function initializeApp() {
  const body = document.body;
  
  // 添加聊天模式切换逻辑
  const chatModeRadios = document.querySelectorAll('input[name="chatMode"]');
  const specialistSelect = document.getElementById('specialistSelect');
  const activeAgentName = document.getElementById('activeAgentName');
  
  if (chatModeRadios.length > 0 && specialistSelect && activeAgentName) {
    chatModeRadios.forEach(radio => {
      radio.addEventListener('change', function() {
        if (this.value === 'specialist') {
          specialistSelect.disabled = false;
          // 如果已有选择的专家，更新显示
          if (specialistSelect.value) {
            activeAgentName.textContent = specialistSelect.options[specialistSelect.selectedIndex].text;
          } else {
            activeAgentName.textContent = '选择专家...';
          }
        } else {
          specialistSelect.disabled = true;
          activeAgentName.textContent = '项目大脑';
        }
      });
    });
    
    // 添加专家选择逻辑
    specialistSelect.addEventListener('change', function() {
      if (this.value) {
        activeAgentName.textContent = this.options[this.selectedIndex].text;
      } else {
        activeAgentName.textContent = '选择专家...';
      }
    });
  }
  
  // 添加专家徽章点击事件
  const specialistBadges = document.querySelectorAll('.badge.specialist');
  specialistBadges.forEach(badge => {
    badge.addEventListener('click', function() {
      if (!specialistSelect || !activeAgentName) return;
      
      const agentId = this.getAttribute('data-agent-id');
      const agentName = this.textContent.trim().split('\n')[0];
      
      // 切换到专家模式并选择对应的专家
      const specialistRadio = document.querySelector('input[name="chatMode"][value="specialist"]');
      if (specialistRadio) {
        specialistRadio.checked = true;
        specialistSelect.disabled = false;
        
        // 找到并选中对应的专家选项
        for (let i = 0; i < specialistSelect.options.length; i++) {
          if (specialistSelect.options[i].value === agentId) {
            specialistSelect.selectedIndex = i;
            break;
          }
        }
        
        // 更新显示的活动专家名称
        activeAgentName.textContent = agentName;
      }
    });
  });
  
  // Load saved history
  loadSavedHistory();
  
  // Add welcome message with typing animation
  setTimeout(() => {
    appendHistory(
      "assistant",
      "系统",
      `欢迎使用 Project Brain，多代理模式：${body.dataset.multiAgent === "true" ? "开启" : "关闭"}`
    );
    
    setStatus("待命");
  }, 500);
  
  // Setup enhancements
  setupKeyboardShortcuts();
  setupIdleState();
  
  // Add input focus handling
  if (messageInput) {
    messageInput.addEventListener('focus', () => {
      messageInput.parentElement.classList.add('input-focused');
    });
    
    messageInput.addEventListener('blur', () => {
      messageInput.parentElement.classList.remove('input-focused');
    });
    
    // Auto-resize textarea based on content
    messageInput.addEventListener('input', () => {
      messageInput.style.height = 'auto';
      const maxHeight = 200; // Maximum height in pixels
      messageInput.style.height = Math.min(messageInput.scrollHeight, maxHeight) + 'px';
    });
  }
  
  // Add connection status check
  if (navigator.onLine === false) {
    setStatus('离线状态', 'error');
    showToast('您当前处于离线状态', 'error');
  }
  
  // Listen for online/offline events
  window.addEventListener('online', () => {
    setStatus('已连接', 'idle');
    showToast('已恢复网络连接', 'success');
  });
  
  window.addEventListener('offline', () => {
    setStatus('离线状态', 'error');
    showToast('网络连接已断开', 'error');
  });
}

// Initialize on page load
window.addEventListener("load", initializeApp);

// 创建粒子效果
function createParticleEffects() {
  const particlesContainer = document.getElementById('particles-js');
  if (!particlesContainer) return;
  
  // 简单的粒子效果实现
  const particlesCount = 50;
  const particles = [];
  
  // 创建粒子函数
  function createParticle() {
    const particle = document.createElement('div');
    
    // 设置粒子样式
    particle.style.position = 'absolute';
    particle.style.width = `${Math.random() * 8 + 2}px`;
    particle.style.height = `${Math.random() * 8 + 2}px`;
    particle.style.borderRadius = '50%';
    particle.style.background = `rgba(79, 70, 229, ${Math.random() * 0.5 + 0.1})`;
    particle.style.boxShadow = '0 0 10px rgba(79, 70, 229, 0.5)';
    particle.style.left = `${Math.random() * 100}%`;
    particle.style.top = `${Math.random() * 100}%`;
    particle.style.opacity = Math.random() * 0.7 + 0.3;
    particle.style.pointerEvents = 'none';
    particle.style.zIndex = '0';
    
    // 添加到容器
    particlesContainer.appendChild(particle);
    
    // 返回粒子信息
    return {
      element: particle,
      x: parseFloat(particle.style.left),
      y: parseFloat(particle.style.top),
      speedX: (Math.random() - 0.5) * 0.1,
      speedY: (Math.random() - 0.5) * 0.1,
      size: parseFloat(particle.style.width),
      opacity: parseFloat(particle.style.opacity)
    };
  }
  
  // 初始化粒子
  for (let i = 0; i < particlesCount; i++) {
    particles.push(createParticle());
  }
  
  // 动画循环
  function animateParticles() {
    particles.forEach(particle => {
      // 更新位置
      particle.x += particle.speedX;
      particle.y += particle.speedY;
      
      // 边界检测
      if (particle.x < 0) particle.x = 100;
      if (particle.x > 100) particle.x = 0;
      if (particle.y < 0) particle.y = 100;
      if (particle.y > 100) particle.y = 0;
      
      // 更新元素样式
      particle.element.style.left = `${particle.x}%`;
      particle.element.style.top = `${particle.y}%`;
    });
    
    // 继续动画
    requestAnimationFrame(animateParticles);
  }
  
  // 启动动画
  animateParticles();
  
  // 鼠标交互
  document.addEventListener('mousemove', (e) => {
    const mouseX = e.clientX / window.innerWidth * 100;
    const mouseY = e.clientY / window.innerHeight * 100;
    
    particles.forEach(particle => {
      // 计算粒子到鼠标的距离
      const dx = particle.x - mouseX;
      const dy = particle.y - mouseY;
      const distance = Math.sqrt(dx * dx + dy * dy);
      
      // 如果粒子在鼠标附近，就产生排斥效果
      if (distance < 15) {
        const force = (15 - distance) * 0.05;
        const angle = Math.atan2(dy, dx);
        
        particle.x += Math.cos(angle) * force;
        particle.y += Math.sin(angle) * force;
      }
    });
  });
}

// 主题切换功能
function setupThemeToggle() {
  const themeToggle = document.getElementById('theme-toggle');
  if (!themeToggle) return;
  
  // 从localStorage获取主题偏好
  const savedTheme = localStorage.getItem('theme') || 'dark';
  applyTheme(savedTheme);
  
  // 主题切换事件
  themeToggle.addEventListener('click', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    applyTheme(newTheme);
    localStorage.setItem('theme', newTheme);
    showToast(`已切换到${newTheme === 'dark' ? '深色' : '浅色'}模式`, 'info');
  });
  
  // 应用主题
  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    
    // 更新主题按钮图标
    if (themeToggle) {
      const icon = themeToggle.querySelector('svg');
      if (theme === 'dark') {
        icon.innerHTML = `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"></path>`;
      } else {
        icon.innerHTML = `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"></path>`;
      }
    }
  }
}

// 帮助按钮功能
function setupHelpButton() {
  const helpButton = document.getElementById('help-button');
  if (!helpButton) return;
  
  helpButton.addEventListener('click', () => {
    const helpModal = document.createElement('div');
    helpModal.className = 'help-modal';
    helpModal.innerHTML = `
      <div class="help-modal-content">
        <div class="help-modal-header">
          <h3>使用帮助</h3>
          <button class="close-button">×</button>
        </div>
        <div class="help-modal-body">
          <h4>快捷键</h4>
          <ul>
            <li><kbd>Ctrl/Cmd + Enter</kbd>: 发送消息</li>
            <li><kbd>Esc</kbd>: 清空输入框</li>
            <li><kbd>Ctrl/Cmd + L</kbd>: 聚焦输入框</li>
          </ul>
          <h4>功能说明</h4>
          <p>Project Brain是一个AI项目协作平台，通过多代理系统为您的项目提供智能分析和建议。您可以在聊天框中输入项目问题或需求，系统会自动分析并提供专业建议。</p>
          <h4>代理专家</h4>
          <ul>
            <li><strong>产品负责人</strong>: 提供产品策略和用户体验方面的建议</li>
            <li><strong>算法科学家</strong>: 提供数据分析和算法优化方面的支持</li>
            <li><strong>解决方案架构师</strong>: 提供技术架构和系统设计方面的指导</li>
          </ul>
        </div>
      </div>
    `;
    
    document.body.appendChild(helpModal);
    
    // 添加模态框样式
    const modalStyle = document.createElement('style');
    modalStyle.textContent = `
      .help-modal {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        animation: fadeIn 0.3s ease;
      }
      
      .help-modal-content {
        background: #121212;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        width: 90%;
        max-width: 600px;
        max-height: 80vh;
        overflow-y: auto;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
        animation: slideIn 0.3s ease;
      }
      
      .help-modal-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 20px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
      }
      
      .help-modal-header h3 {
        margin: 0;
        color: var(--text-primary);
      }
      
      .close-button {
        background: none;
        border: none;
        font-size: 24px;
        color: var(--text-muted);
        cursor: pointer;
        width: 30px;
        height: 30px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        transition: all 0.2s ease;
      }
      
      .close-button:hover {
        background: rgba(255, 255, 255, 0.1);
        color: var(--text-primary);
      }
      
      .help-modal-body {
        padding: 20px;
      }
      
      .help-modal-body h4 {
        color: var(--text-primary);
        margin-top: 20px;
        margin-bottom: 10px;
      }
      
      .help-modal-body ul {
        padding-left: 20px;
        color: var(--text-secondary);
      }
      
      .help-modal-body li {
        margin-bottom: 8px;
      }
      
      .help-modal-body p {
        color: var(--text-secondary);
        margin-bottom: 15px;
        line-height: 1.6;
      }
      
      kbd {
        background: rgba(255, 255, 255, 0.1);
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 12px;
        color: var(--text-primary);
        border: 1px solid rgba(255, 255, 255, 0.2);
      }
      
      @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
      }
      
      @keyframes slideIn {
        from { transform: translateY(-20px); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
      }
    `;
    document.head.appendChild(modalStyle);
    
    // 关闭按钮事件
    const closeButton = helpModal.querySelector('.close-button');
    closeButton.addEventListener('click', () => {
      helpModal.style.opacity = '0';
      helpModal.style.transform = 'scale(0.95)';
      setTimeout(() => {
        document.body.removeChild(helpModal);
        document.head.removeChild(modalStyle);
      }, 300);
    });
    
    // 点击外部关闭
    helpModal.addEventListener('click', (e) => {
      if (e.target === helpModal) {
        closeButton.click();
      }
    });
  });
}

// 增强的消息渲染与动画
function enhanceMessageInteractions() {
  // 为聊天消息添加悬停效果
  document.addEventListener('mouseover', (e) => {
    if (e.target.closest('.chat-item')) {
      const chatItem = e.target.closest('.chat-item');
      chatItem.style.transition = 'transform 0.2s ease, box-shadow 0.2s ease';
      chatItem.style.transform = 'translateY(-2px)';
      chatItem.style.boxShadow = '0 6px 20px rgba(0, 0, 0, 0.15)';
    }
  });
  
  document.addEventListener('mouseout', (e) => {
    if (e.target.closest('.chat-item')) {
      const chatItem = e.target.closest('.chat-item');
      chatItem.style.transform = 'translateY(0)';
      chatItem.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.1)';
    }
  });
  
  // 为输入框添加实时反馈
  if (messageInput) {
    messageInput.addEventListener('input', (e) => {
      const submitButton = form?.querySelector('button[type="submit"]');
      if (submitButton) {
        if (e.target.value.trim().length > 0 && !state.isLoading) {
          submitButton.classList.add('button-active');
          submitButton.removeAttribute('disabled');
        } else {
          submitButton.classList.remove('button-active');
          submitButton.setAttribute('disabled', 'true');
        }
      }
    });
  }
}

// 性能监控与优化功能
function setupPerformanceMonitoring() {
  // 性能指标对象
  const performanceStats = {
    memoryUsage: 0,
    responseTime: 0,
    frameRate: 0,
    eventCount: 0,
    lastPerformanceUpdate: 0
  };
  
  // 帧率监控
  function monitorFrameRate() {
    let frames = 0;
    let lastTime = performance.now();
    
    function updateFrameRate() {
      frames++;
      const currentTime = performance.now();
      const elapsed = currentTime - lastTime;
      
      if (elapsed >= 1000) { // 每秒更新一次
        performanceStats.frameRate = Math.round((frames * 1000) / elapsed);
        frames = 0;
        lastTime = currentTime;
        
        // 如果启用了FPS显示
        if (window.showFPS) {
          console.log(`FPS: ${performanceStats.frameRate}`);
        }
        
        // 帧率过低时优化
        if (performanceStats.frameRate < 30) {
          optimizeForLowPerformance();
        } else {
          restoreFullPerformance();
        }
      }
      
      requestAnimationFrame(updateFrameRate);
    }
    
    updateFrameRate();
  }
  
  // 响应时间监控 - 添加空函数以避免调用错误
  // 全局定义updateResponseTime函数，避免任何地方调用时出错
  function updateResponseTime() {
    console.log('全局updateResponseTime函数被调用，但已被禁用');
    // 此函数故意留空，以避免JavaScript错误
  }
  
  // 内存使用监控
  function updateMemoryUsage() {
    if (memoryUsage) {
      // 随机模拟内存使用（实际应用中应从服务器获取）
      const usedMemory = (Math.random() * 2 + 1).toFixed(2);
      const totalMemory = 4.0;
      const usagePercent = ((usedMemory / totalMemory) * 100).toFixed(0);
      
      performanceStats.memoryUsage = parseFloat(usagePercent);
      memoryUsage.textContent = `内存: ${usedMemory}GB / ${totalMemory}GB (${usagePercent}%)`;
      
      // 根据内存使用情况改变颜色
      if (usagePercent > 80) {
        memoryUsage.style.color = 'var(--accent)';
      } else if (usagePercent > 60) {
        memoryUsage.style.color = 'var(--warning)';
      } else {
        memoryUsage.style.color = 'var(--secondary)';
      }
      
      // 内存使用过高时进行优化
      if (performanceStats.memoryUsage > 85) {
        optimizeMemoryUsage();
      }
    }
  }
  
  // 恢复全性能
  function restoreFullPerformance() {
    document.body.classList.remove('low-performance');
  }
  
  // 内存优化
  function optimizeMemoryUsage() {
    // 清理旧消息（如果超过一定数量）
    const messageList = document.querySelector('.chat-messages');
    if (messageList) {
      const messages = messageList.querySelectorAll('.chat-item');
      if (messages.length > 50) {
        // 只保留最新的30条消息
        for (let i = 0; i < messages.length - 30; i++) {
          messages[i].remove();
        }
        
        showToast('已优化内存使用，清理了部分历史消息', 'info');
      }
    }
    
    // 减少DOM事件监听器
    if (window.eventThrottlingEnabled !== true) {
      window.eventThrottlingEnabled = true;
      // 这里可以添加事件节流逻辑
    }
  }
  
  // 定期性能报告
  function sendPerformanceReport() {
    // 在实际应用中，这里可以向服务器发送性能数据
    // console.log('Performance report:', performanceStats);
  }
  
  // 初始化监控 - 只保留必要的监控功能
  monitorFrameRate();
  updateMemoryUsage();
  
  // 设置定期更新 - 只保留必要的定时器
  setInterval(updateMemoryUsage, 5000);
  setInterval(sendPerformanceReport, 60000);
}

// 资源优化 - 懒加载
function setupLazyLoading() {
  // 为聊天消息添加懒加载支持
  const lazyLoadObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const element = entry.target;
        element.classList.add('loaded');
        
        // 处理可能的图片懒加载
        const img = element.querySelector('img[data-src]');
        if (img) {
          img.src = img.dataset.src;
          delete img.dataset.src;
        }
        
        // 停止观察已加载的元素
        lazyLoadObserver.unobserve(element);
      }
    });
  }, {
    root: null,
    rootMargin: '100px',
    threshold: 0.1
  });
  
  // 观察所有需要懒加载的元素
  document.querySelectorAll('.lazy-load').forEach(element => {
    lazyLoadObserver.observe(element);
  });
  
  // 扩展renderMessages函数以支持懒加载
  const originalRenderMessages = renderMessages;
  renderMessages = function(messages) {
    // 调用原始函数
    const result = originalRenderMessages(messages);
    
    // 为新添加的消息添加懒加载观察
    setTimeout(() => {
      document.querySelectorAll('.chat-item:not(.loaded)').forEach(element => {
        element.classList.add('lazy-load');
        lazyLoadObserver.observe(element);
      });
    }, 0);
    
    return result;
  };
}

// 响应式适配和设备检测
function setupResponsiveAdaptation() {
  // 设备信息对象
  const deviceInfo = {
    isMobile: /iPhone|iPad|iPod|Android/i.test(navigator.userAgent),
    isTablet: /iPad|Android(?!.*Mobile)/i.test(navigator.userAgent),
    isTouchDevice: 'ontouchstart' in window || navigator.maxTouchPoints > 0,
    screenWidth: window.innerWidth,
    screenHeight: window.innerHeight,
    orientation: window.innerWidth > window.innerHeight ? 'landscape' : 'portrait'
  };
  
  // 初始化设备类
  function initializeDeviceClasses() {
    // 添加设备类到body
    if (deviceInfo.isMobile) {
      document.body.classList.add('mobile-device');
    } else if (deviceInfo.isTablet) {
      document.body.classList.add('tablet-device');
    } else {
      document.body.classList.add('desktop-device');
    }
    
    if (deviceInfo.isTouchDevice) {
      document.body.classList.add('touch-device');
    } else {
      document.body.classList.add('non-touch-device');
    }
    
    document.body.classList.add(deviceInfo.orientation);
  }
  
  // 调整UI以适应设备
  function adaptUIForDevice() {
    // 移动端优化
    if (deviceInfo.isMobile) {
      // 简化粒子效果或禁用
      const particlesContainer = document.getElementById('particles-js');
      if (particlesContainer) {
        particlesContainer.style.display = 'none';
      }
      
      // 调整点击区域大小
      document.querySelectorAll('button, a, .badge').forEach(element => {
        const rect = element.getBoundingClientRect();
        if (rect.width < 48 || rect.height < 48) {
          element.style.minWidth = '48px';
          element.style.minHeight = '48px';
          element.style.padding = '8px';
        }
      });
      
      // 优化输入区域
      const messageInput = document.getElementById('message-input');
      if (messageInput) {
        messageInput.style.fontSize = '16px'; // 防止iOS缩放
      }
    }
  }
  
  // 处理窗口大小变化
  function handleResize() {
    const newWidth = window.innerWidth;
    const newHeight = window.innerHeight;
    const newOrientation = newWidth > newHeight ? 'landscape' : 'portrait';
    
    // 更新设备信息
    deviceInfo.screenWidth = newWidth;
    deviceInfo.screenHeight = newHeight;
    
    // 处理方向变化
    if (deviceInfo.orientation !== newOrientation) {
      document.body.classList.remove(deviceInfo.orientation);
      document.body.classList.add(newOrientation);
      deviceInfo.orientation = newOrientation;
      
      // 重新调整UI
      adaptUIForDevice();
      
      // 通知用户
      showToast(`已切换到${newOrientation === 'landscape' ? '横向' : '纵向'}模式`, 'info');
    }
    
    // 响应式布局调整
    adjustLayoutForScreenSize();
  }
  
  // 根据屏幕尺寸调整布局
  function adjustLayoutForScreenSize() {
    const chatContainer = document.querySelector('.chat-container');
    if (chatContainer) {
      // 计算适当的高度
      const heroHeight = document.querySelector('.hero').offsetHeight;
      const statusHeight = document.querySelector('.status-block').offsetHeight;
      const availableHeight = window.innerHeight - heroHeight - statusHeight - 40;
      
      chatContainer.style.height = `${availableHeight}px`;
    }
  }
  
  // 添加触摸事件支持
  function addTouchSupport() {
    if (deviceInfo.isTouchDevice) {
      // 为按钮添加触摸反馈
      document.querySelectorAll('button, .badge').forEach(element => {
        element.addEventListener('touchstart', () => {
          element.style.transform = 'scale(0.95)';
        });
        
        element.addEventListener('touchend', () => {
          element.style.transform = 'scale(1)';
        });
      });
    }
  }
  
  // 初始化
  initializeDeviceClasses();
  adaptUIForDevice();
  addTouchSupport();
  
  // 监听窗口大小变化
  window.addEventListener('resize', handleResize);
  
  // 导出设备信息
  window.deviceInfo = deviceInfo;
}

// 页面加载完成后初始化增强功能
window.addEventListener('load', () => {
  // 初始化设备适配和响应式设计
  setupResponsiveAdaptation();
  
  // 初始化性能监控
  setupPerformanceMonitoring();
  
  // 初始化懒加载功能
  setupLazyLoading();
  
  // 初始化粒子效果（非移动设备）
  if (!window.deviceInfo?.isMobile) {
    createParticleEffects();
  }
  
  // 初始化主题切换
  setupThemeToggle();
  
  // 初始化帮助按钮
  setupHelpButton();
  
  // 增强消息交互
  enhanceMessageInteractions();
  
  // 页面加载动画
  document.body.style.opacity = '0';
  document.body.style.transition = 'opacity 0.5s ease';
  setTimeout(() => {
    document.body.style.opacity = '1';
  }, 100);
  
  // 延迟初始化其他组件以提高首屏加载速度
  setTimeout(() => {
    // 可以在这里初始化非关键组件
    // 预加载一些资源等
    console.log('应用初始化完成，性能优化已启用');
  }, 1000);
});

// Add CSS for new UI elements and enhanced interactions
const additionalStyles = `
  .collapsible-wrapper {
    position: relative;
  }
  
  .collapsible-content {
    position: relative;
  }
  
  .collapsible-content::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 30px;
    background: linear-gradient(transparent, var(--background-primary));
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.3s ease;
  }
  
  .collapsible-content[style*="max-height"]::after {
    opacity: 1;
  }
  
  .toggle-button {
    transition: all 0.2s ease;
  }
  
  .toggle-button:hover {
    background: rgba(255, 255, 255, 0.15);
  }
  
  .toggle-button:active {
    transform: scale(0.95);
  }
  
  .toggle-icon {
    transition: transform 0.3s ease;
    font-size: 10px;
  }

  /* Toast notifications */
  .toast-container {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  
  .toast-notification {
    padding: 12px 20px;
    border-radius: 8px;
    color: white;
    font-weight: 500;
    opacity: 0;
    transform: translateY(-20px);
    transition: all 0.3s ease;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    max-width: 300px;
  }
  
  .toast-info {
    background: var(--info);
  }
  
  .toast-error {
    background: var(--accent);
  }
  
  .toast-success {
    background: var(--secondary);
  }
  
  /* Typing animation */
  .typing-animation {
    display: flex;
    align-items: center;
    gap: 4px;
  }
  
  .typing-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: var(--text-muted);
    animation: typing 1.4s infinite ease-in-out both;
  }
  
  .typing-dot.dot-1 { animation-delay: -0.32s; }
  .typing-dot.dot-2 { animation-delay: -0.16s; }
  
  @keyframes typing {
    0%, 80%, 100% { transform: scale(0); opacity: 0.5; }
    40% { transform: scale(1); opacity: 1; }
  }
  
  /* Button loading state */
  .button-loading {
    position: relative;
    color: transparent !important;
  }
  
  .button-loading::after {
    content: '';
    position: absolute;
    width: 16px;
    height: 16px;
    top: 50%;
    left: 50%;
    margin-left: -8px;
    margin-top: -8px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-radius: 50%;
    border-top-color: white;
    animation: spin 0.8s linear infinite;
  }
  
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
  
  /* Input focus effect */
  .input-focused {
    position: relative;
  }
  
  .input-focused::after {
    content: '';
    position: absolute;
    inset: -1px;
    border-radius: inherit;
    background: linear-gradient(45deg, var(--primary-light), transparent);
    opacity: 0.5;
    pointer-events: none;
  }
  
  /* Status transition */
  .status-transition {
    transition: all 0.3s ease;
  }
  
  /* Pulse dot for busy status */
  .pulse-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: var(--warning);
    margin-right: 8px;
    animation: pulse 2s infinite;
  }
  
  @keyframes pulse {
    0% { transform: scale(0.95); opacity: 1; }
    50% { transform: scale(1.1); opacity: 0.7; }
    100% { transform: scale(0.95); opacity: 1; }
  }
  
  /* Message timestamp */
  .message-timestamp {
    font-size: 10px;
    margin-left: 8px;
    color: var(--text-muted);
    opacity: 0.7;
  }
  
  /* Button active state */
  .button-active {
    background: linear-gradient(135deg, var(--primary-light), var(--primary)) !important;
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(79, 70, 229, 0.4);
  }
  
  /* Help and theme button styles */
  .help-button {
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 50%;
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-primary);
    cursor: pointer;
    transition: all 0.3s ease;
    backdrop-filter: blur(5px);
  }
  
  .help-button:hover {
    background: rgba(255, 255, 255, 0.2);
    transform: scale(1.05);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }
  
  .help-button:active {
    transform: scale(0.95);
  }
  
  /* System actions container */
  .system-actions {
    display: flex;
    gap: 12px;
  }
`;

// Inject additional styles
const styleElement = document.createElement('style');
styleElement.textContent = additionalStyles;
document.head.appendChild(styleElement);

