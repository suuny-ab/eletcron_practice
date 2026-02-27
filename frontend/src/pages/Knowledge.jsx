import { useState, useEffect, useCallback, useRef } from 'react';
import { Layout, message } from 'antd';
import ConfigPage from './Config';
import { ResizableDivider } from '../components/common';
import { FileTree } from '../components/FileTree';
import { NoteEditor } from '../components/NoteEditor';
import { AISidebar } from '../components/AISidebar';
import { useFileTree } from '../hooks/useFileTree';
import { useAIChat } from '../hooks/useAIChat';
import { useRAG } from '../hooks/useRAG';
import { useNoteManager } from '../hooks/useNoteManager';
import { COLORS, SHADOWS, TRANSITIONS } from '../styles/tokens';
import 'highlight.js/styles/github.css';

const { Sider, Content } = Layout;

function KnowledgePage({ leftSidebarCollapsed, setLeftSidebarCollapsed, aiSidebarVisible, setAiSidebarVisible, configTabVisible, onConfigTabClose, configTabRequestId }) {
  // 文件树状态
  const {
    treeData, loading, expandedKeys, selectedKeys,
    setExpandedKeys, setSelectedKeys,
    initializeTree, refreshTree, toggleExpandAll,
  } = useFileTree();

  // 笔记管理状态
  const {
    openNotes,
    openChunks,
    noteStates,
    noteDefaults,
    activeMainTab,
    activeNoteKey,
    activeNote,
    activeNoteState,
    setActiveMainTab,
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
  } = useNoteManager(configTabVisible, configTabRequestId, onConfigTabClose);

  // AI 对话状态
  const {
    aiMode,
    chatMessages,
    userInput,
    aiGenerating,
    previewMode,
    originalContent,
    generatedContent,
    setAiMode,
    setChatMessages,
    setUserInput,
    setPreviewMode,
    setOriginalContent,
    setGeneratedContent,
    cancelGeneration,
    sendAdviseMessage,
    sendEditRequest,
    sendOptimizeRequest,
    resetChat,
    addMessage,
    updateLastMessage,
  } = useAIChat();

  // RAG 状态
  const {
    ragMessages,
    ragSources,
    ragTopK,
    ragLoading,
    currentQueryId,
    setRagMessages,
    setRagSources,
    setRagTopK,
    sendRagQuery,
    cancelQuery,
    resetRag,
    clearHistory,
  } = useRAG();

  // 拖动调整宽度状态
  const [leftSiderWidth, setLeftSiderWidth] = useState(20); // 百分比
  const [rightSiderWidth, setRightSiderWidth] = useState(28); // 百分比
  const [isDragging, setIsDragging] = useState(null); // 'left' | 'right' | null
  const containerRef = useRef(null);

  const fileContent = activeNoteState.content;
  const selectedFile = activeNote ? { key: activeNote.key, title: activeNote.title } : null;

  // 页面加载时读取文件树
  useEffect(() => {
    initializeTree();
  }, [initializeTree]);

  // 配置标签页切换
  useEffect(() => {
    updateTabForConfig(configTabVisible, configTabRequestId);
  }, [configTabVisible, configTabRequestId, updateTabForConfig]);

  // 切换到配置标签页
  useEffect(() => {
    if (configTabRequestId > 0) {
      setActiveMainTab('config');
    }
  }, [configTabRequestId, setActiveMainTab]);

  // 切换笔记时重置AI聊天状态
  useEffect(() => {
    if (activeNoteKey) {
      resetChat();
    }
  }, [activeNoteKey, resetChat]);

  // 切换到 RAG 模式时清空对话历史
  useEffect(() => {
    if (aiMode === 'rag') {
      clearHistory();
    }
  }, [aiMode, clearHistory]);


  // AI 消息发送
  const handleSendAiMessage = useCallback(async () => {
    if (!userInput.trim()) {
      message.warning('请输入问题');
      return;
    }

    // RAG 模式：知识库问答
    if (aiMode === 'rag') {
      const question = userInput.trim();
      setUserInput('');

      // 清空分块标签
      setOpenChunks([]);

      try {
        await sendRagQuery(question, { topK: ragTopK });
      } catch (error) {
        if (error.name !== 'AbortError') {
          message.error('RAG 问答失败: ' + error.message);
        }
      }
      return;
    }

    // 非 RAG 模式需要选择笔记
    if (!activeNoteKey) {
      message.warning('请选择笔记');
      return;
    }

    // AI编辑模式
    if (aiMode === 'edit') {
      setPreviewMode(true);
      setOriginalContent(fileContent);
      setGeneratedContent('');

      try {
        const content = await sendEditRequest(activeNoteKey, userInput, (chunk) => {
          setGeneratedContent(prev => prev + (chunk || ''));
        });
      } catch (error) {
        if (error.name !== 'AbortError') {
          message.error('AI 编辑失败: ' + error.message);
          setPreviewMode(false);
          setOriginalContent('');
          setGeneratedContent('');
        }
      }
      return;
    }

    // AI建议模式：在对话中显示
    addMessage('user', userInput);
    setUserInput('');

    try {
      await sendAdviseMessage(activeNoteKey, userInput, (chunk, fullContent) => {
        updateLastMessage(fullContent);
      });
    } catch (error) {
      if (error.name !== 'AbortError') {
        setChatMessages(prev => [...prev, {
          role: 'assistant',
          content: `错误：${error.message}`
        }]);
      }
    }
  }, [userInput, aiMode, activeNoteKey, fileContent, ragTopK, sendRagQuery, sendEditRequest, sendAdviseMessage, addMessage, updateLastMessage, setUserInput, setPreviewMode, setOriginalContent, setGeneratedContent, setOpenChunks]);

  // 一键排版
  const handleOneClickOptimize = useCallback(async () => {
    if (!activeNoteKey) {
      message.warning('请先选择笔记');
      return;
    }

    setPreviewMode(true);
    setOriginalContent(fileContent);
    setGeneratedContent('');

    try {
      const content = await sendOptimizeRequest(activeNoteKey, (chunk) => {
        setGeneratedContent(prev => prev + (chunk || ''));
      });
    } catch (error) {
      if (error.name !== 'AbortError') {
        message.error('排版失败: ' + error.message);
        setPreviewMode(false);
        setOriginalContent('');
        setGeneratedContent('');
      }
    }
  }, [activeNoteKey, fileContent, sendOptimizeRequest, setPreviewMode, setOriginalContent, setGeneratedContent]);

  // 取消 AI 生成或结果
  const handleCancelAiResult = useCallback(() => {
    if (aiGenerating) {
      cancelGeneration();
    }
    if (ragLoading) {
      cancelQuery();
    }
    setPreviewMode(false);
    setOriginalContent('');
    setGeneratedContent('');
  }, [aiGenerating, ragLoading, cancelGeneration, cancelQuery, setPreviewMode, setOriginalContent, setGeneratedContent]);



  const handleLeftDragState = useCallback((dragging) => setIsDragging(dragging ? 'left' : null), []);
  const handleRightDragState = useCallback((dragging) => setIsDragging(dragging ? 'right' : null), []);

  return (
    <div 
      ref={containerRef}
      style={{
        flex: 1,
        display: 'flex',
        height: '100%',
        overflow: 'hidden',
        background: COLORS.bgBase,
        width: '100%',
      }}>
      {/* 左侧边栏 */}
      <Sider
        width={`${leftSiderWidth}%`}
        collapsed={leftSidebarCollapsed}
        collapsedWidth={0}
        collapsible
        trigger={null}
        style={{
          background: COLORS.bgCard,
          borderRight: `1px solid ${COLORS.border}`,
          boxShadow: SHADOWS.siderLeft,
          transition: isDragging ? 'none' : TRANSITIONS.default,
          margin: 0,
          height: '100%',
        }}
      >
        <FileTree
          treeData={treeData}
          loading={loading}
          expandedKeys={expandedKeys}
          selectedKeys={selectedKeys}
          onExpand={setExpandedKeys}
          onSelect={(selectedKeys, info) => handleSelect(selectedKeys, info, setSelectedKeys)}
          onRefresh={refreshTree}
          onToggleExpandAll={toggleExpandAll}
        />
      </Sider>

      {/* 左侧分割线 */}
      <ResizableDivider
        side="left"
        containerRef={containerRef}
        onWidthChange={setLeftSiderWidth}
        onDragStateChange={handleLeftDragState}
      />

      {/* 主内容区 */}
      <Content style={{ padding: '0', height: '100%', overflow: 'hidden', flex: 1, margin: 0, maxWidth: 'none' }}>
        <NoteEditor
          activeTab={activeMainTab}
          onTabChange={setActiveMainTab}
          onTabClose={handleTabClose}
          openNotes={openNotes}
          openChunks={openChunks}
          noteStates={noteStates}
          noteDefaults={noteDefaults}
          configTabVisible={configTabVisible}
          configTabContent={<ConfigPage embedded />}
          onStartEdit={handleStartEdit}
          onCancelEdit={handleCancelEdit}
          onSave={handleSave}
          onNoteStateChange={updateNoteState}
        />
      </Content>

      {/* 右侧分割线 */}
      <ResizableDivider
        side="right"
        visible={aiSidebarVisible}
        containerRef={containerRef}
        onWidthChange={setRightSiderWidth}
        onDragStateChange={handleRightDragState}
      />

      {/* AI 侧边栏 */}
      <Sider
        width={`${rightSiderWidth}%`}
        collapsed={!aiSidebarVisible}
        collapsedWidth={0}
        style={{
          background: COLORS.bgCard,
          borderLeft: `1px solid ${COLORS.border}`,
          boxShadow: SHADOWS.siderRight,
          overflow: 'hidden',
          transition: isDragging ? 'none' : TRANSITIONS.default,
          margin: 0,
          height: '100%',
        }}
      >
        <AISidebar
          visible={aiSidebarVisible}
          aiMode={aiMode}
          onModeChange={setAiMode}
          chatMessages={chatMessages}
          ragMessages={ragMessages}
          ragSources={ragSources}
          userInput={userInput}
          onInputChange={setUserInput}
          onSend={handleSendAiMessage}
          onOptimize={handleOneClickOptimize}
          ragTopK={ragTopK}
          onTopKChange={setRagTopK}
          previewMode={previewMode}
          generatedContent={generatedContent}
          aiGenerating={aiGenerating}
          ragLoading={ragLoading}
          onConfirmPreview={handleConfirmAiResult}
          onCancelPreview={handleCancelAiResult}
          selectedFile={selectedFile}
          onOpenChunk={(source, index) => openRagChunk(source, index, currentQueryId)}
          isDragging={isDragging}
        />
      </Sider>
    </div>
  );
}

export default KnowledgePage;
