// 后端 API 基础 URL（开发环境）
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

/**
 * 读取事件流式响应
 * @param {ReadableStream} stream - 流式响应
 * @param {AbortSignal} signal - 中断信号
 * @returns {AsyncGenerator<Object>} 返回事件对象
 */
export async function* readEventStream(stream, signal) {
  const reader = stream.getReader();
  const decoder = new TextDecoder();

  try {
    while (true) {
      if (signal && signal.aborted) {
        console.log('[readEventStream] Stream aborted by user');
        break;
      }

      const { done, value } = await reader.read();

      if (done) {
        console.log('[readEventStream] Stream done');
        break;
      }

      const chunk = decoder.decode(value, { stream: true });
      console.log('[readEventStream] Received chunk:', chunk);

      // 解析 JSON 格式的数据（每行一个 JSON 对象）
      const lines = chunk.split('\n');
      for (const line of lines) {
        const trimmedLine = line.trim();
        if (!trimmedLine) continue; // 跳过空行

        // 支持 SSE 格式（data: {...}）和纯 JSON 格式（{...}）
        const data = trimmedLine.startsWith('data: ') ? trimmedLine.slice(6) : trimmedLine;
        try {
          const parsed = JSON.parse(data);
          console.log('[readEventStream] Parsed:', parsed);

          if (parsed.type === 'complete') {
            console.log('[readEventStream] Stream complete');
            return;
          }

          if (parsed.type === 'error') {
            throw new Error(parsed.content || parsed.message || '请求失败');
          }

          if (parsed.error) {
            throw new Error(parsed.error);
          }

          yield parsed;
        } catch (e) {
          console.warn('[readEventStream] Failed to parse line:', trimmedLine, e);
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * RAG 调试接口 - 获取详细检索步骤信息
 * @param {string} question - 用户问题
 * @param {AbortSignal} signal - 中断信号
 * @returns {Promise<Object>} 调试信息
 */
export async function ragDebug(question, signal) {
  const response = await fetch(`${API_BASE_URL}/api/ai/rag/debug`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ question }),
    signal,
  });

  if (!response.ok) {
    const text = await response.text().catch(() => '');
    throw new Error(`HTTP ${response.status}: ${text || response.statusText}`);
  }

  const result = await response.json();
  if (!result.success) {
    throw new Error(result.message || 'RAG 调试请求失败');
  }

  return result.data;
}

/**
 * 统一 Agent 接口
 * 整合闲聊、RAG 知识检索、文档建议/编辑/格式化
 * @param {Object} params - 请求参数
 * @param {string} params.userInput - 用户输入
 * @param {string} params.sessionId - 会话 ID
 * @param {string} params.permissionMode - 权限模式 (assistant / editor)
 * @param {string|null} params.documentContent - 文档内容
 * @param {string|null} params.documentName - 文档名称
 * @param {number} params.topK - 检索数量
 * @param {number} params.maxRounds - 最大检索轮次
 * @param {Object} options - 请求选项
 * @param {AbortSignal} options.signal - 中断信号
 * @returns {ReadableStream} 流式响应
 */
export async function unifiedAgentStream(params, options = {}) {
  const {
    userInput,
    sessionId = '',
    permissionMode = 'assistant',
    documentContent = null,
    documentName = null,
    topK = 3,
    maxRounds = 3,
  } = params;
  const { signal } = options;

  const response = await fetch(`${API_BASE_URL}/api/ai/agent`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      user_input: userInput,
      session_id: sessionId,
      permission_mode: permissionMode,
      document_content: documentContent,
      document_name: documentName,
      top_k: topK,
      max_rounds: maxRounds,
    }),
    signal,
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.body;
}
