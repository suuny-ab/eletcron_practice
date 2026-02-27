/**
 * 笔记管理 Hook
 * 负责笔记标签页、笔记状态、笔记操作的管理
 */
import { useState, useMemo, useCallback } from 'react';
import { message } from 'antd';
import { getFileContent, updateFileContent } from '../api/knowledge';

const NOTE_DEFAULTS = {
  content: '',
  editContent: '',
  isEditing: false,
  contentLoading: false,
  saveLoading: false,
  hasLoaded: false,
};

export function useNoteManager(configTabVisible, configTabRequestId, onConfigTabClose) {
  // 笔记标签页状态
  const [openNotes, setOpenNotes] = useState([]);
  const [openChunks, setOpenChunks] = useState([]);
  const [noteStates, setNoteStates] = useState({});
  const [activeMainTab, setActiveMainTab] = useState('notes');

  // 计算激活的笔记
  const activeNoteKey = useMemo(() =>
    activeMainTab.startsWith('note:') ? activeMainTab.slice(5) : null,
    [activeMainTab]
  );

  const activeNote = useMemo(() =>
    activeNoteKey ? openNotes.find(note => note.key === activeNoteKey) : null,
    [activeNoteKey, openNotes]
  );

  const activeNoteState = activeNoteKey && noteStates[activeNoteKey] ? noteStates[activeNoteKey] : NOTE_DEFAULTS;

  // 配置标签页切换逻辑
  const updateTabForConfig = useCallback((isVisible, requestId) => {
    if (isVisible) {
      setActiveMainTab('config');
      return;
    }

    if (activeMainTab === 'config') {
      if (openNotes.length > 0) {
        setActiveMainTab(`note:${openNotes[openNotes.length - 1].key}`);
      } else {
        setActiveMainTab('notes');
      }
    }
  }, [activeMainTab, openNotes]);

  // 更新笔记状态
  const updateNoteState = useCallback((noteKey, patch) => {
    if (!noteKey) return;
    setNoteStates(prev => ({
      ...prev,
      [noteKey]: {
        ...NOTE_DEFAULTS,
        ...prev[noteKey],
        ...patch,
      }
    }));
  }, []);

  // 获取笔记状态
  const getNoteState = useCallback((noteKey) => noteStates[noteKey] || NOTE_DEFAULTS, [noteStates]);

  // 处理文件选择
  const handleSelect = useCallback(async (selectedKeys, info, setSelectedKeys) => {
    const node = info.node;
    if (node.is_leaf) {
      setSelectedKeys(selectedKeys);

      const fileName = node.key;
      const isMarkdown = fileName.toLowerCase().endsWith('.md');

      if (!isMarkdown) {
        message.warning('仅支持预览 Markdown 格式文件');
        return;
      }

      const noteKey = node.key;
      const tabKey = `note:${noteKey}`;

      setOpenNotes(prev => {
        if (prev.some(note => note.key === noteKey)) {
          return prev;
        }
        return [...prev, { key: noteKey, title: node.title || noteKey }];
      });
      setActiveMainTab(tabKey);

      const cachedState = noteStates[noteKey];
      if (cachedState?.hasLoaded) {
        return;
      }

      updateNoteState(noteKey, { contentLoading: true, isEditing: false });
      try {
        const response = await getFileContent(noteKey);
        const content = response.data?.content || '';
        updateNoteState(noteKey, {
          content,
          editContent: content,
          contentLoading: false,
          hasLoaded: true,
        });
      } catch (error) {
        message.error('加载文件失败: ' + (error.response?.data?.message || error.message));
      }
    }
  }, [noteStates, updateNoteState]);

  // 打开RAG分块
  const openRagChunk = useCallback((source, index, currentQueryId) => {
    if (!source) {
      message.warning('暂无分块内容');
      return;
    }

    const filename = source.filename || '未命名';
    const title = `${index + 1}. ${filename.split('/').pop()}`;
    const chunkKey = `chunk:${currentQueryId}:${index}`;
    const chunkTab = {
      key: chunkKey,
      title,
      content: source.content || '',
      score: source.score,
      filename,
      order: index + 1,
    };

    setOpenChunks(prev => {
      if (prev.some(chunk => chunk.key === chunkKey)) {
        return prev;
      }
      return [...prev, chunkTab];
    });
    setActiveMainTab(chunkKey);
  }, []);

  // 开始编辑
  const handleStartEdit = useCallback((noteKey) => {
    const noteState = getNoteState(noteKey);
    updateNoteState(noteKey, { editContent: noteState.content, isEditing: true });
  }, [getNoteState, updateNoteState]);

  // 取消编辑
  const handleCancelEdit = useCallback((noteKey) => {
    const noteState = getNoteState(noteKey);
    updateNoteState(noteKey, { editContent: noteState.content, isEditing: false });
  }, [getNoteState, updateNoteState]);

  // 保存编辑
  const handleSave = useCallback(async (noteKey) => {
    if (!noteKey) return;

    const noteState = getNoteState(noteKey);
    updateNoteState(noteKey, { saveLoading: true });
    try {
      await updateFileContent(noteKey, noteState.editContent);
      updateNoteState(noteKey, { content: noteState.editContent, isEditing: false, hasLoaded: true });
      message.success('文件保存成功');
    } catch (error) {
      message.error('保存失败: ' + (error.response?.data?.message || error.message));
    } finally {
      updateNoteState(noteKey, { saveLoading: false });
    }
  }, [getNoteState, updateNoteState]);

  // 关闭标签页
  const handleTabClose = useCallback((targetKey) => {
    if (targetKey === 'config') {
      onConfigTabClose?.();
      return;
    }

    if (targetKey.startsWith('note:')) {
      const noteKey = targetKey.replace('note:', '');
      setOpenNotes(prev => {
        const next = prev.filter(note => note.key !== noteKey);
        if (activeMainTab === targetKey) {
          if (configTabVisible) {
            setActiveMainTab('config');
          } else if (next.length > 0) {
            setActiveMainTab(`note:${next[next.length - 1].key}`);
          } else if (openChunks.length > 0) {
            setActiveMainTab(openChunks[openChunks.length - 1].key);
          } else {
            setActiveMainTab('notes');
          }
        }
        return next;
      });
      setNoteStates(prev => {
        const next = { ...prev };
        delete next[noteKey];
        return next;
      });
      return;
    }

    if (targetKey.startsWith('chunk:')) {
      setOpenChunks(prev => {
        const next = prev.filter(chunk => chunk.key !== targetKey);
        if (activeMainTab === targetKey) {
          if (configTabVisible) {
            setActiveMainTab('config');
          } else if (next.length > 0) {
            setActiveMainTab(next[next.length - 1].key);
          } else if (openNotes.length > 0) {
            setActiveMainTab(`note:${openNotes[openNotes.length - 1].key}`);
          } else {
            setActiveMainTab('notes');
          }
        }
        return next;
      });
    }
  }, [activeMainTab, configTabVisible, openNotes, openChunks, onConfigTabClose]);

  // 在文件树中查找节点并展开父目录
  const findAndExpandPath = useCallback((filename, treeData, setExpandedKeys) => {
    const pathParts = filename.split('/').filter(p => p);
    const keysToExpand = [];

    const traverseTree = (nodes, currentPath = []) => {
      for (const node of nodes) {
        const nodePath = [...currentPath, node.title];
        const pathString = nodePath.join('/');

        for (let i = 0; i < pathParts.length; i++) {
          const targetPath = pathParts.slice(0, i + 1).join('/');
          if (pathString === targetPath) {
            keysToExpand.push(node.key);
            break;
          }
        }

        if (node.children) {
          traverseTree(node.children, nodePath);
        }
      }
    };

    traverseTree(treeData);

    if (keysToExpand.length > 0) {
      setExpandedKeys(prev => [...new Set([...prev, ...keysToExpand])]);
    }
  }, []);

  // 确认保存AI生成的内容
  const handleConfirmAiResult = useCallback(async (generatedContent) => {
    if (!activeNoteKey) return;

    updateNoteState(activeNoteKey, { saveLoading: true });
    try {
      await updateFileContent(activeNoteKey, generatedContent);
      updateNoteState(activeNoteKey, { content: generatedContent, editContent: generatedContent, hasLoaded: true });
      message.success('AI 生成的内容已保存到文件');
    } catch (error) {
      message.error('保存失败: ' + (error.response?.data?.message || error.message));
    } finally {
      updateNoteState(activeNoteKey, { saveLoading: false });
    }
  }, [activeNoteKey, updateNoteState]);

  return {
    // 状态
    openNotes,
    openChunks,
    noteStates,
    noteDefaults: NOTE_DEFAULTS,
    activeMainTab,
    activeNoteKey,
    activeNote,
    activeNoteState,
    configTabVisible,

    // 状态设置器
    setActiveMainTab,

    // 方法
    updateTabForConfig,
    updateNoteState,
    getNoteState,
    handleSelect,
    openRagChunk,
    handleStartEdit,
    handleCancelEdit,
    handleSave,
    handleTabClose,
    findAndExpandPath,
    handleConfirmAiResult,
  };
}

export default useNoteManager;
