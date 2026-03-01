import { useState, useEffect, useCallback, useRef } from 'react';
import { Layout, message } from 'antd';
import ConfigPage from './Config';
import { ResizableDivider } from '../components/common';
import { FileTree } from '../components/FileTree';
import { NoteEditor } from '../components/NoteEditor';
import { AgentSidebar } from '../components/AgentSidebar';
import { useFileTree } from '../hooks/useFileTree';
import { useNoteManager } from '../hooks/useNoteManager';
import { updateFileContent } from '../api/knowledge';
import { COLORS, SHADOWS, TRANSITIONS } from '../styles/tokens';
import 'highlight.js/styles/github.css';

const { Sider, Content } = Layout;

function KnowledgePage({ leftSidebarCollapsed, aiSidebarVisible, configTabVisible, onConfigTabClose, configTabRequestId }) {
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
    activeNote,
    activeNoteState,
    setActiveMainTab,
    updateTabForConfig,
    updateNoteState,
    handleSelect,
    openRagChunk,
    handleStartEdit,
    handleCancelEdit,
    handleSave,
    handleTabClose,
  } = useNoteManager(configTabVisible, configTabRequestId, onConfigTabClose);

  // Diff 对比标签页状态
  const [diffTabConfig, setDiffTabConfig] = useState(null);

  // 拖动调整宽度状态
  const [leftSiderWidth, setLeftSiderWidth] = useState(20); // 百分比
  const [rightSiderWidth, setRightSiderWidth] = useState(28); // 百分比
  const [isDragging, setIsDragging] = useState(null); // 'left' | 'right' | null
  const containerRef = useRef(null);

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

  // 打开主区域双栏对比标签页
  const handleOpenDiffTab = useCallback((info) => {
    setDiffTabConfig(info);
    setActiveMainTab('diff:preview');
  }, [setActiveMainTab]);

  // Diff 确认保存 - 直接用 noteKey 保存，避免 activeNoteKey 因切换标签变 null
  const handleDiffConfirm = useCallback(async (content) => {
    const noteKey = diffTabConfig?.noteKey;
    if (!noteKey) {
      message.error('无法确定目标文档');
      return;
    }
    try {
      updateNoteState(noteKey, { saveLoading: true });
      await updateFileContent(noteKey, content);
      updateNoteState(noteKey, { content, editContent: content, hasLoaded: true, saveLoading: false });
      message.success('AI 生成的内容已保存到文件');
    } catch (error) {
      updateNoteState(noteKey, { saveLoading: false });
      message.error('保存失败: ' + (error.response?.data?.message || error.message));
      return;
    }
    setDiffTabConfig(prev => {
      prev?.onApplied?.();
      return null;
    });
    setActiveMainTab(`note:${noteKey}`);
  }, [diffTabConfig, updateNoteState, setActiveMainTab]);

  // Diff 取消
  const handleDiffCancel = useCallback(() => {
    const noteKey = diffTabConfig?.noteKey;
    setDiffTabConfig(prev => {
      prev?.onCancelled?.();
      return null;
    });
    if (noteKey) {
      setActiveMainTab(`note:${noteKey}`);
    }
  }, [diffTabConfig, setActiveMainTab]);

  // Tab 关闭（含 diff 标签页处理）
  const handleTabCloseWithDiff = useCallback((key) => {
    if (key === 'diff:preview') {
      handleDiffCancel();
      return;
    }
    handleTabClose(key);
  }, [handleTabClose, handleDiffCancel]);

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
          onTabClose={handleTabCloseWithDiff}
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
          diffTab={diffTabConfig ? {
            originalContent: diffTabConfig.originalContent,
            editedContent: diffTabConfig.editedContent,
            diffText: diffTabConfig.diffText,
            documentName: diffTabConfig.documentName,
            onConfirm: handleDiffConfirm,
            onCancel: handleDiffCancel,
          } : null}
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

      {/* AI Agent 侧边栏 */}
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
        <AgentSidebar
          visible={aiSidebarVisible}
          isDragging={isDragging}
          activeNote={activeNote}
          noteContent={activeNoteState?.content ?? null}
          onOpenDiffTab={handleOpenDiffTab}
          onOpenChunk={(source, index) => openRagChunk(source, index, 0)}
        />
      </Sider>
    </div>
  );
}

export default KnowledgePage;
