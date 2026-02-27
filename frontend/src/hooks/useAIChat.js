/**
 * AI 对话状态管理 Hook
 * 负责 AI 建议、编辑模式的对话状态管理
 */
import { useState, useRef, useCallback } from 'react';
import { message } from 'antd';
import { aiAdvise, aiEdit, aiOptimize, readEventStream } from '../api/ai';

export function useAIChat() {
  const [aiMode, setAiMode] = useState('advise'); // 'advise' | 'edit' | 'rag'
  const [chatMessages, setChatMessages] = useState([]);
  const [userInput, setUserInput] = useState('');
  const [aiGenerating, setAiGenerating] = useState(false);
  const [previewMode, setPreviewMode] = useState(false);
  const [originalContent, setOriginalContent] = useState('');
  const [generatedContent, setGeneratedContent] = useState('');
  const abortControllerRef = useRef(null);

  // 取消当前生成
  const cancelGeneration = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setAiGenerating(false);
  }, []);

  // 发送 AI 建议请求
  const sendAdviseMessage = useCallback(async (filename, question, onChunk) => {
    if (!filename || !question.trim()) {
      message.warning('请选择文件并输入问题');
      return;
    }

    setAiGenerating(true);
    abortControllerRef.current = new AbortController();

    try {
      const response = await aiAdvise(
        filename,
        question,
        abortControllerRef.current.signal
      );

      let fullContent = '';
      for await (const event of readEventStream(response, abortControllerRef.current.signal)) {
        if (event.type === 'chunk' && event.content) {
          fullContent += event.content;
          onChunk?.(event.content, fullContent);
        }
      }

      return fullContent;
    } catch (error) {
      if (error.name !== 'AbortError') {
        message.error('AI 请求失败: ' + error.message);
      }
      throw error;
    } finally {
      setAiGenerating(false);
      abortControllerRef.current = null;
    }
  }, []);

  // 发送 AI 编辑请求
  const sendEditRequest = useCallback(async (filename, requirement, onChunk) => {
    if (!filename || !requirement.trim()) {
      message.warning('请选择文件并输入编辑需求');
      return;
    }

    setAiGenerating(true);
    abortControllerRef.current = new AbortController();

    try {
      const response = await aiEdit(
        filename,
        requirement,
        abortControllerRef.current.signal
      );

      let fullContent = '';
      for await (const event of readEventStream(response, abortControllerRef.current.signal)) {
        if (event.type === 'chunk' && event.content) {
          fullContent += event.content;
          onChunk?.(event.content, fullContent);
        }
      }

      return fullContent;
    } catch (error) {
      if (error.name !== 'AbortError') {
        message.error('AI 编辑请求失败: ' + error.message);
      }
      throw error;
    } finally {
      setAiGenerating(false);
      abortControllerRef.current = null;
    }
  }, []);

  // 发送一键排版请求
  const sendOptimizeRequest = useCallback(async (filename, onChunk) => {
    if (!filename) {
      message.warning('请选择文件');
      return;
    }

    setAiGenerating(true);
    abortControllerRef.current = new AbortController();

    try {
      const response = await aiOptimize(
        filename,
        abortControllerRef.current.signal
      );

      let fullContent = '';
      for await (const event of readEventStream(response, abortControllerRef.current.signal)) {
        if (event.type === 'chunk' && event.content) {
          fullContent += event.content;
          onChunk?.(event.content, fullContent);
        }
      }

      return fullContent;
    } catch (error) {
      if (error.name !== 'AbortError') {
        message.error('排版优化请求失败: ' + error.message);
      }
      throw error;
    } finally {
      setAiGenerating(false);
      abortControllerRef.current = null;
    }
  }, []);

  // 重置对话状态
  const resetChat = useCallback(() => {
    setChatMessages([]);
    setUserInput('');
    setPreviewMode(false);
    setOriginalContent('');
    setGeneratedContent('');
  }, []);

  // 添加消息到对话历史
  const addMessage = useCallback((role, content) => {
    setChatMessages(prev => [...prev, { role, content, timestamp: Date.now() }]);
  }, []);

  // 更新最后一条消息
  const updateLastMessage = useCallback((content) => {
    setChatMessages(prev => {
      const newMessages = [...prev];
      if (newMessages.length > 0) {
        newMessages[newMessages.length - 1] = {
          ...newMessages[newMessages.length - 1],
          content,
        };
      }
      return newMessages;
    });
  }, []);

  return {
    // 状态
    aiMode,
    chatMessages,
    userInput,
    aiGenerating,
    previewMode,
    originalContent,
    generatedContent,

    // 状态设置器
    setAiMode,
    setChatMessages,
    setUserInput,
    setPreviewMode,
    setOriginalContent,
    setGeneratedContent,

    // 方法
    cancelGeneration,
    sendAdviseMessage,
    sendEditRequest,
    sendOptimizeRequest,
    resetChat,
    addMessage,
    updateLastMessage,
  };
}

export default useAIChat;
