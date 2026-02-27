import axios from 'axios';

// 后端 API 基础 URL（开发环境）
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

// 创建 axios 实例
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60秒超时
  headers: {
    'Content-Type': 'application/json',
  },
});

// 注意：apiClient 暂未使用，如需要可启用

/**
 * AI 建议接口
 * @param {string} filename - 文件名
 * @param {string} question - 用户问题
 * @param {AbortSignal} signal - 中断信号
 * @returns {AsyncGenerator} 流式响应生成器
 */
export async function aiAdvise(filename, question, signal) {
  const response = await fetch(`${API_BASE_URL}/api/ai/advise`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ filename, question }),
    signal,
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.body;
}

/**
 * AI 编辑接口
 * @param {string} filename - 文件名
 * @param {string} requirement - 编辑要求
 * @param {AbortSignal} signal - 中断信号
 * @returns {AsyncGenerator} 流式响应生成器
 */
export async function aiEdit(filename, requirement, signal) {
  const response = await fetch(`${API_BASE_URL}/api/ai/edit`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ filename, requirement }),
    signal,
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.body;
}

/**
 * 一键排版接口
 * @param {string} filename - 文件名
 * @param {AbortSignal} signal - 中断信号
 * @returns {AsyncGenerator} 流式响应生成器
 */
export async function aiOptimize(filename, signal) {
  const response = await fetch(`${API_BASE_URL}/api/ai/optimize`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ filename }),
    signal,
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.body;
}

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
 * AI 知识库问答接口（RAG）
 * @param {string} question - 用户问题
 * @param {number} topK - 检索的文档数量
 * @param {AbortSignal} signal - 中断信号
 * @returns {ReadableStream} 流式响应
 */
export async function ragAskStream(question, topK = 3, signal) {
  const response = await fetch(`${API_BASE_URL}/api/ai/rag`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ question, top_k: topK }),
    signal,
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.body;
}

/**
 * RAG 调试接口 - 获取详细检索步骤信息
 * @param {string} question - 用户问题
 * @param {number} topK - 检索的文档数量
 * @param {AbortSignal} signal - 中断信号
 * @returns {Promise<Object>} 调试信息
 */
export async function ragDebug(question, topK = 3, signal) {
  const response = await fetch(`${API_BASE_URL}/api/ai/rag/debug`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ question, top_k: topK }),
    signal,
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const result = await response.json();
  if (!result.success) {
    throw new Error(result.message || 'RAG 调试请求失败');
  }

  return result.data;
}
