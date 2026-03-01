import { useState, useCallback, useEffect } from 'react';
import {
  getSessions as fetchSessions,
  deleteSession as apiDeleteSession,
  renameSession as apiRenameSession,
} from '../api/ai';

const STORAGE_KEY = 'unified_agent_session_id';

/**
 * 生成唯一会话 ID
 */
function generateSessionId() {
  const timestamp = Date.now().toString(36);
  const random = Math.random().toString(36).substring(2, 8);
  return `session_${timestamp}_${random}`;
}

/**
 * 会话管理 Hook
 * 使用 localStorage 持久化 session_id，支持会话列表管理
 */
export function useSession() {
  // 当前会话 ID
  const [sessionId, setSessionId] = useState(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) return stored;
    const newId = generateSessionId();
    localStorage.setItem(STORAGE_KEY, newId);
    return newId;
  });

  // 会话列表
  const [sessionList, setSessionList] = useState([]);
  const [sessionListLoading, setSessionListLoading] = useState(false);
  const [sessionListError, setSessionListError] = useState(null);

  // 创建新会话
  const createNewSession = useCallback(() => {
    const newId = generateSessionId();
    localStorage.setItem(STORAGE_KEY, newId);
    setSessionId(newId);
    // 触发会话切换事件
    window.dispatchEvent(new CustomEvent('session-switched', { detail: { sessionId: newId, isNew: true } }));
    return newId;
  }, []);

  // 加载会话列表
  const loadSessions = useCallback(async () => {
    setSessionListLoading(true);
    setSessionListError(null);
    try {
      const sessions = await fetchSessions('updated_at');
      setSessionList(sessions);
    } catch (error) {
      console.error('加载会话列表失败:', error);
      setSessionListError(error.message);
    } finally {
      setSessionListLoading(false);
    }
  }, []);

  // 切换会话
  const switchSession = useCallback((newSessionId) => {
    if (newSessionId === sessionId) return;
    
    localStorage.setItem(STORAGE_KEY, newSessionId);
    setSessionId(newSessionId);
    // 触发会话切换事件，通知 useUnifiedAgent 清空对话
    window.dispatchEvent(new CustomEvent('session-switched', { detail: { sessionId: newSessionId, isNew: false } }));
  }, [sessionId]);

  // 重命名会话
  const renameSession = useCallback(async (targetSessionId, title) => {
    try {
      await apiRenameSession(targetSessionId, title);
      // 更新本地列表
      setSessionList(prev => prev.map(s => 
        s.session_id === targetSessionId ? { ...s, title } : s
      ));
    } catch (error) {
      console.error('重命名会话失败:', error);
      throw error;
    }
  }, []);

  // 删除会话
  const deleteSession = useCallback(async (targetSessionId) => {
    try {
      await apiDeleteSession(targetSessionId);
      // 更新本地列表
      setSessionList(prev => prev.filter(s => s.session_id !== targetSessionId));
      
      // 如果删除的是当前会话，创建新会话
      if (targetSessionId === sessionId) {
        createNewSession();
      }
    } catch (error) {
      console.error('删除会话失败:', error);
      throw error;
    }
  }, [sessionId, createNewSession]);

  // 监听其他 useSession 实例触发的会话切换，同步 sessionId
  useEffect(() => {
    const handleSync = (event) => {
      const { sessionId: newId } = event.detail || {};
      if (newId) {
        setSessionId(prev => prev === newId ? prev : newId);
      }
    };
    window.addEventListener('session-switched', handleSync);
    return () => window.removeEventListener('session-switched', handleSync);
  }, []);

  // 组件挂载时加载会话列表
  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  return {
    // 当前会话
    sessionId,
    createNewSession,
    
    // 会话列表管理
    sessionList,
    sessionListLoading,
    sessionListError,
    loadSessions,
    switchSession,
    renameSession,
    deleteSession,
  };
}
