/**
 * 统一 Agent 状态管理 Hook
 * 替换 useAIChat + useRAG，调用 unifiedAgentStream API
 */
import { useState, useRef, useCallback, useEffect } from 'react';
import { unifiedAgentStream, readEventStream, getSessionHistory } from '../api/ai';
import { useSession } from './useSession';

export function useUnifiedAgent() {
  const { sessionId, createNewSession } = useSession();

  // 配置
  const [permissionMode, setPermissionMode] = useState('assistant');
  const [topK, setTopK] = useState(3);
  const [maxRounds, setMaxRounds] = useState(3);

  // 对话
  const [conversations, setConversations] = useState([]);
  const [userInput, setUserInput] = useState('');

  // 流式状态
  const [loading, setLoading] = useState(false);
  const [streamState, setStreamState] = useState({
    processMessages: [],
    answer: '',
    diff: '',
    sources: [],
  });

  // Diff 预览
  const [previewMode, setPreviewMode] = useState(false);
  const [pendingDiff, setPendingDiff] = useState(null); // { diff, messageIndex }

  const abortControllerRef = useRef(null);
  const streamStateRef = useRef(streamState);
  useEffect(() => {
    streamStateRef.current = streamState;
  }, [streamState]);

  // 从 API 加载会话历史并填充 conversations
  const loadSessionHistory = useCallback(async (targetSessionId) => {
    try {
      const data = await getSessionHistory(targetSessionId);
      if (data && data.messages && data.messages.length > 0) {
        const restored = data.messages.map(msg => ({
          role: msg.role,
          content: msg.content,
          timestamp: msg.timestamp ? new Date(msg.timestamp).getTime() : null,
          ...(msg.role === 'assistant' ? {
            sources: msg.retrieval_sources || [],
            diff: null,
            editedContent: null,
            diffApplied: false,
            processMessages: [],
            stats: null,
            error: null,
          } : {}),
        }));
        setConversations(restored);
      }
    } catch (error) {
      console.error('加载会话历史失败:', error);
    }
  }, []);

  // sessionId 变化时：重置状态并加载历史
  const prevSessionIdRef = useRef(sessionId);
  useEffect(() => {
    const prevId = prevSessionIdRef.current;
    prevSessionIdRef.current = sessionId;

    // 跳过首次渲染（由下面的 mount effect 处理）
    if (prevId === sessionId) return;

    // 中止正在进行的生成
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    // 清空状态
    setConversations([]);
    setUserInput('');
    setStreamState({ processMessages: [], answer: '', diff: '', sources: [] });
    setPreviewMode(false);
    setPendingDiff(null);

    // 加载历史（新创建的会话无需加载）
    if (sessionId) {
      loadSessionHistory(sessionId);
    }
  }, [sessionId, loadSessionHistory]);

  // 应用启动时加载当前会话的历史
  useEffect(() => {
    if (sessionId) {
      loadSessionHistory(sessionId);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // 发送消息
  const sendMessage = useCallback(async (inputText, documentContent, documentName) => {
    if (!inputText.trim() || loading) return;

    // 添加用户消息
    setConversations(prev => [...prev, {
      role: 'user',
      content: inputText.trim(),
      timestamp: Date.now(),
    }]);

    setLoading(true);
    setStreamState({ processMessages: [], answer: '', diff: '', sources: [] });
    abortControllerRef.current = new AbortController();

    let accAnswer = '';
    let accDiff = '';
    let editedContent = null; // 后端返回的完整编辑后文本
    let lastSources = [];
    let lastStats = null;
    let processMessages = [];

    try {
      const stream = await unifiedAgentStream(
        {
          userInput: inputText.trim(),
          sessionId,
          permissionMode,
          documentContent: documentContent || null,
          documentName: documentName || null,
          topK,
          maxRounds,
        },
        { signal: abortControllerRef.current.signal }
      );

      for await (const event of readEventStream(stream, abortControllerRef.current.signal)) {
        switch (event.type) {
          case 'status': {
            const msg = { type: 'status', content: event.content, data: event.data };
            processMessages = [...processMessages, msg];
            setStreamState(prev => ({ ...prev, processMessages }));
            break;
          }
          case 'thinking': {
            const msg = { type: 'thinking', content: event.content };
            processMessages = [...processMessages, msg];
            setStreamState(prev => ({ ...prev, processMessages }));
            break;
          }
          case 'sources': {
            lastSources = event.data || [];
            const msg = { type: 'sources', content: `${lastSources.length} 条相关内容`, data: lastSources };
            processMessages = [...processMessages, msg];
            setStreamState(prev => ({ ...prev, sources: lastSources, processMessages }));
            break;
          }
          case 'chunk':
            accAnswer += (event.content || '');
            setStreamState(prev => ({ ...prev, answer: accAnswer }));
            break;
          case 'diff':
            accDiff += (event.content || '');
            // 后端在 data 中附带了完整编辑后内容
            if (event.data?.edited_content) {
              editedContent = event.data.edited_content;
            }
            if (event.data?.formatted_content) {
              editedContent = event.data.formatted_content;
            }
            setStreamState(prev => ({ ...prev, diff: accDiff }));
            break;
          case 'prompt': {
            const msg = { type: 'prompt', content: event.content };
            processMessages = [...processMessages, msg];
            setStreamState(prev => ({ ...prev, processMessages }));
            break;
          }
          case 'error': {
            const msg = { type: 'error', content: event.content };
            processMessages = [...processMessages, msg];
            setStreamState(prev => ({ ...prev, processMessages }));
            break;
          }
          case 'complete':
            lastStats = event.data;
            break;
        }
      }

      // 流结束：归档到对话历史
      setConversations(prev => [...prev, {
        role: 'assistant',
        content: accAnswer,
        diff: accDiff || null,
        editedContent: editedContent,
        diffApplied: false,
        sources: lastSources,
        processMessages,
        stats: lastStats,
        error: null,
        timestamp: Date.now(),
      }]);
    } catch (error) {
      if (error.name !== 'AbortError') {
        setConversations(prev => [...prev, {
          role: 'assistant',
          content: accAnswer,
          diff: accDiff || null,
          editedContent: editedContent,
          diffApplied: false,
          sources: lastSources,
          processMessages,
          stats: null,
          error: error.message,
          timestamp: Date.now(),
        }]);
      } else {
        if (accAnswer || accDiff || processMessages.length > 0) {
          setConversations(prev => [...prev, {
            role: 'assistant',
            content: accAnswer,
            diff: accDiff || null,
            editedContent: editedContent,
            diffApplied: false,
            sources: lastSources,
            processMessages,
            stats: null,
            error: '(已停止)',
            timestamp: Date.now(),
          }]);
        }
      }
    } finally {
      setLoading(false);
      setStreamState({ processMessages: [], answer: '', diff: '', sources: [] });
      abortControllerRef.current = null;
    }
  }, [loading, sessionId, permissionMode, topK, maxRounds]);

  // 停止生成
  const stopGeneration = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  }, []);

  // 新建会话
  const newSession = useCallback(() => {
    createNewSession();
    setConversations([]);
    setUserInput('');
    setStreamState({ processMessages: [], answer: '', diff: '', sources: [] });
    setPreviewMode(false);
    setPendingDiff(null);
  }, [createNewSession]);

  // 打开 diff 预览
  const openDiffPreview = useCallback((messageIndex) => {
    const entry = conversations[messageIndex];
    if (entry?.diff) {
      setPendingDiff({
        diff: entry.diff,
        editedContent: entry.editedContent || null,
        messageIndex,
      });
      setPreviewMode(true);
    }
  }, [conversations]);

  // 标记 diff 已应用
  const markDiffApplied = useCallback((messageIndex) => {
    setConversations(prev => prev.map((entry, i) =>
      i === messageIndex ? { ...entry, diffApplied: true } : entry
    ));
    setPreviewMode(false);
    setPendingDiff(null);
  }, []);

  // 取消 diff 预览
  const cancelDiffPreview = useCallback(() => {
    setPreviewMode(false);
    setPendingDiff(null);
  }, []);

  return {
    // 会话
    sessionId,
    // 配置
    permissionMode, setPermissionMode,
    topK, setTopK,
    maxRounds, setMaxRounds,
    // 对话
    conversations,
    userInput, setUserInput,
    // 流式
    loading,
    streamState,
    // 预览
    previewMode,
    pendingDiff,
    // 方法
    sendMessage,
    stopGeneration,
    newSession,
    openDiffPreview,
    markDiffApplied,
    cancelDiffPreview,
  };
}

export default useUnifiedAgent;
