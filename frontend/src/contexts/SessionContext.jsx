import { createContext, useContext, useState, useCallback, useEffect } from 'react';
import {
  getSessions as fetchSessions,
  deleteSession as apiDeleteSession,
  renameSession as apiRenameSession,
} from '../api/ai';

const STORAGE_KEY = 'unified_agent_session_id';

function generateSessionId() {
  const timestamp = Date.now().toString(36);
  const random = Math.random().toString(36).substring(2, 8);
  return `session_${timestamp}_${random}`;
}

const SessionContext = createContext(null);

/**
 * 会话状态 Provider
 * 全局唯一实例，管理 sessionId 和会话列表
 */
export function SessionProvider({ children }) {
  const [sessionId, setSessionId] = useState(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) return stored;
    const newId = generateSessionId();
    localStorage.setItem(STORAGE_KEY, newId);
    return newId;
  });

  const [sessionList, setSessionList] = useState([]);
  const [sessionListLoading, setSessionListLoading] = useState(false);
  const [sessionListError, setSessionListError] = useState(null);

  // 创建新会话
  const createNewSession = useCallback(() => {
    const newId = generateSessionId();
    localStorage.setItem(STORAGE_KEY, newId);
    setSessionId(newId);
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
    setSessionId(prev => {
      if (prev === newSessionId) return prev;
      localStorage.setItem(STORAGE_KEY, newSessionId);
      return newSessionId;
    });
  }, []);

  // 重命名会话
  const renameSession = useCallback(async (targetSessionId, title) => {
    try {
      await apiRenameSession(targetSessionId, title);
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
      setSessionList(prev => prev.filter(s => s.session_id !== targetSessionId));

      // 如果删除的是当前会话，创建新会话
      setSessionId(prev => {
        if (prev === targetSessionId) {
          const newId = generateSessionId();
          localStorage.setItem(STORAGE_KEY, newId);
          return newId;
        }
        return prev;
      });
    } catch (error) {
      console.error('删除会话失败:', error);
      throw error;
    }
  }, []);

  // 挂载时加载会话列表
  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  const value = {
    sessionId,
    createNewSession,
    sessionList,
    sessionListLoading,
    sessionListError,
    loadSessions,
    switchSession,
    renameSession,
    deleteSession,
  };

  return (
    <SessionContext.Provider value={value}>
      {children}
    </SessionContext.Provider>
  );
}

/**
 * 获取会话上下文
 */
export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) {
    throw new Error('useSession must be used within a SessionProvider');
  }
  return ctx;
}
