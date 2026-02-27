/**
 * RAG 检索问答状态管理 Hook
 * 负责知识库问答的状态管理
 */
import { useState, useRef, useCallback } from 'react';
import { message } from 'antd';
import { ragAskStream, readEventStream } from '../api/ai';

export function useRAG() {
  const [ragMessages, setRagMessages] = useState([]);
  const [ragSources, setRagSources] = useState([]);
  const [ragTopK, setRagTopK] = useState(3);
  const [ragLoading, setRagLoading] = useState(false);
  const [currentQueryId, setCurrentQueryId] = useState(0);
  const queryIdRef = useRef(0);
  const abortControllerRef = useRef(null);

  // 取消当前查询
  const cancelQuery = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setRagLoading(false);
  }, []);

  // 发送 RAG 问答请求
  const sendRagQuery = useCallback(async (question, options = {}) => {
    if (!question.trim()) {
      message.warning('请输入问题');
      return;
    }

    // 增加查询 ID
    queryIdRef.current += 1;
    const thisQueryId = queryIdRef.current;
    setCurrentQueryId(thisQueryId);

    setRagLoading(true);
    setRagSources([]);
    abortControllerRef.current = new AbortController();

    // 添加用户消息
    setRagMessages(prev => [...prev, {
      role: 'user',
      content: question,
      timestamp: Date.now(),
    }]);

    // 添加 AI 消息占位
    setRagMessages(prev => [...prev, {
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      isStreaming: true,
    }]);

    try {
      const stream = await ragAskStream(
        { question, top_k: options.topK || ragTopK },
        { signal: abortControllerRef.current.signal }
      );

      let fullContent = '';
      let sources = [];

      for await (const event of readEventStream(stream, abortControllerRef.current.signal)) {
        // 检查是否仍是当前查询
        if (queryIdRef.current !== thisQueryId) return;

        if (event.type === 'chunk') {
          fullContent += event.content || '';
          setRagMessages(prev => {
            const newMessages = [...prev];
            if (newMessages.length > 0) {
              newMessages[newMessages.length - 1] = {
                ...newMessages[newMessages.length - 1],
                content: fullContent,
              };
            }
            return newMessages;
          });
        } else if (event.type === 'source') {
          sources.push(event.data);
          setRagSources([...sources]);
        } else if (event.type === 'complete') {
          // 流结束
          break;
        }
      }

      // 标记流式传输完成
      setRagMessages(prev => {
        const newMessages = [...prev];
        if (newMessages.length > 0) {
          newMessages[newMessages.length - 1] = {
            ...newMessages[newMessages.length - 1],
            isStreaming: false,
          };
        }
        return newMessages;
      });

      return { content: fullContent, sources };
    } catch (error) {
      if (error.name !== 'AbortError') {
        message.error('RAG 问答请求失败: ' + error.message);
        // 移除失败的 AI 消息
        setRagMessages(prev => prev.slice(0, -1));
      }
      throw error;
    } finally {
      setRagLoading(false);
      abortControllerRef.current = null;
    }
  }, [ragTopK]);

  // 重置 RAG 状态
  const resetRag = useCallback(() => {
    setRagMessages([]);
    setRagSources([]);
    setCurrentQueryId(0);
    queryIdRef.current = 0;
  }, []);

  // 清空对话历史
  const clearHistory = useCallback(() => {
    setRagMessages([]);
    setRagSources([]);
  }, []);

  return {
    // 状态
    ragMessages,
    ragSources,
    ragTopK,
    ragLoading,
    currentQueryId,

    // 状态设置器
    setRagMessages,
    setRagSources,
    setRagTopK,

    // 方法
    sendRagQuery,
    cancelQuery,
    resetRag,
    clearHistory,
  };
}

export default useRAG;
