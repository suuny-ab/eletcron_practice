import axios from 'axios';

// 后端 API 基础 URL（开发环境）
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

/**
 * RAG 问答接口
 * @param {string} question - 用户问题
 * @param {number} topK - 检索的文档数量
 * @returns {Promise<Object>} 返回 { answer, sources: [{ filename, content, score }] }
 */
export async function ragAsk(question, topK = 3) {
  const response = await fetch(`${API_BASE_URL}/rag/ask`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ question, top_k: topK }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || `HTTP error! status: ${response.status}`);
  }

  return response.json();
}

/**
 * RAG 流式问答接口
 * @param {string} question - 用户问题
 * @param {number} topK - 检索的文档数量
 * @param {AbortSignal} signal - 中断信号
 * @returns {ReadableStream} 流式响应
 */
export async function ragAskStream(question, topK = 3, signal) {
  const response = await fetch(`${API_BASE_URL}/rag/ask`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ question, top_k: topK, stream: true }),
    signal,
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.body;
}

/**
 * 读取 RAG 流式响应
 * @param {ReadableStream} stream - 流式响应
 * @param {AbortSignal} signal - 中断信号
 * @returns {AsyncGenerator<Object>} 返回 { type: 'answer' | 'source', content, data? }
 */
export async function* readRagStream(stream, signal) {
  const reader = stream.getReader();
  const decoder = new TextDecoder();

  try {
    while (true) {
      if (signal && signal.aborted) {
        console.log('[readRagStream] Stream aborted by user');
        break;
      }

      const { done, value } = await reader.read();

      if (done) {
        console.log('[readRagStream] Stream done');
        break;
      }

      const chunk = decoder.decode(value, { stream: true });
      console.log('[readRagStream] Received chunk:', chunk);

      // 解析 JSON 格式的数据（每行一个 JSON 对象）
      const lines = chunk.split('\n');
      for (const line of lines) {
        const trimmedLine = line.trim();
        if (!trimmedLine) continue;

        // 支持 SSE 格式（data: {...}）和纯 JSON 格式（{...}）
        const data = trimmedLine.startsWith('data: ') ? trimmedLine.slice(6) : trimmedLine;
        try {
          const parsed = JSON.parse(data);
          console.log('[readRagStream] Parsed:', parsed);

          if (parsed.type === 'answer' && parsed.content) {
            yield { type: 'answer', content: parsed.content };
          } else if (parsed.type === 'source' && parsed.data) {
            yield { type: 'source', data: parsed.data };
          } else if (parsed.type === 'complete' || parsed.type === 'StreamComplete') {
            console.log('[readRagStream] Stream complete');
            break;
          } else if (parsed.error) {
            throw new Error(parsed.error);
          }
        } catch (e) {
          console.warn('[readRagStream] Failed to parse line:', trimmedLine, e);
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
