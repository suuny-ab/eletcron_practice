import { useState, useCallback } from 'react';

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
 * 使用 localStorage 持久化 session_id，支持手动创建新会话
 */
export function useSession() {
  const [sessionId, setSessionId] = useState(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) return stored;
    const newId = generateSessionId();
    localStorage.setItem(STORAGE_KEY, newId);
    return newId;
  });

  const createNewSession = useCallback(() => {
    const newId = generateSessionId();
    localStorage.setItem(STORAGE_KEY, newId);
    setSessionId(newId);
    return newId;
  }, []);

  return { sessionId, createNewSession };
}
