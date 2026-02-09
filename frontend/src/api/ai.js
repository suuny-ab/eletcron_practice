import axios from 'axios';

// 后端 API 基础 URL（开发环境）
const API_BASE_URL = 'http://localhost:8000';

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
 * @returns {AsyncGenerator} 流式响应生成器
 */
export async function aiAdvise(filename, question) {
  const response = await fetch(`${API_BASE_URL}/ai/advise`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ filename, question }),
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
 * @returns {AsyncGenerator} 流式响应生成器
 */
export async function aiEdit(filename, requirement) {
  const response = await fetch(`${API_BASE_URL}/ai/edit`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ filename, requirement }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.body;
}

/**
 * 一键排版接口
 * @param {string} filename - 文件名
 * @returns {AsyncGenerator} 流式响应生成器
 */
export async function aiOptimize(filename) {
  const response = await fetch(`${API_BASE_URL}/ai/optimize`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ filename }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.body;
}

/**
 * 读取流式响应
 * @param {ReadableStream} stream - 流式响应
 * @returns {AsyncGenerator<string>} 文本生成器
 */
export async function* readStream(stream) {
  const reader = stream.getReader();
  const decoder = new TextDecoder();

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        console.log('[readStream] Stream done');
        break;
      }

      const chunk = decoder.decode(value, { stream: true });
      console.log('[readStream] Received chunk:', chunk);
      // 解析 JSON 格式的数据（每行一个 JSON 对象）
      const lines = chunk.split('\n');
      for (const line of lines) {
        const trimmedLine = line.trim();
        if (!trimmedLine) continue; // 跳过空行

        // 支持 SSE 格式（data: {...}）和纯 JSON 格式（{...}）
        const data = trimmedLine.startsWith('data: ') ? trimmedLine.slice(6) : trimmedLine;
        try {
          const parsed = JSON.parse(data);
          console.log('[readStream] Parsed:', parsed);
          if (parsed.content) {
            console.log('[readStream] Yielding content:', parsed.content);
            yield parsed.content;
          } else if (parsed.error) {
            throw new Error(parsed.error);
          }
          // 忽略其他消息类型（如 StreamComplete）
        } catch {
          // 忽略解析错误
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
