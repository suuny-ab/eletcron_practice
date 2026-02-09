import { useState, useEffect, useRef } from 'react';
import { Tree, Card, message, Spin, Typography, Empty, Layout, Button, Space, Tag, Input, Select, Tabs } from 'antd';
import { FolderOutlined, FileOutlined, ReloadOutlined, FolderOpenOutlined, EditOutlined, CheckOutlined, CloseOutlined, SendOutlined, BgColorsOutlined, EditOutlined as EditOutlined2, ThunderboltOutlined, MenuUnfoldOutlined, MenuFoldOutlined } from '@ant-design/icons';
import { getFileTree, getFileContent, updateFileContent } from '../api/knowledge';
import { aiAdvise, aiEdit, aiOptimize, readStream } from '../api/ai';
import ConfigPage from './Config';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import rehypeRaw from 'rehype-raw';
import 'highlight.js/styles/github.css';

const { DirectoryTree } = Tree;
const { Text, Paragraph } = Typography;
const { Sider, Content } = Layout;
const { TextArea } = Input;

function KnowledgePage({ leftSidebarCollapsed, setLeftSidebarCollapsed, aiSidebarVisible, setAiSidebarVisible, configTabVisible, onConfigTabClose, configTabRequestId }) {
  const [treeData, setTreeData] = useState([]);
  const [loading, setLoading] = useState(false);
  const hasInitialized = useRef(false);
  const [expandedKeys, setExpandedKeys] = useState([]);
  const [openNotes, setOpenNotes] = useState([]);
  const [noteStates, setNoteStates] = useState({});
  const [activeMainTab, setActiveMainTab] = useState('notes');

  // AI 侧边栏状态
  const [aiMode, setAiMode] = useState('advise'); // 'advise' | 'edit'
  const [chatMessages, setChatMessages] = useState([]);
  const [userInput, setUserInput] = useState('');
  const [aiGenerating, setAiGenerating] = useState(false);
  const [previewMode, setPreviewMode] = useState(false);
  const [originalContent, setOriginalContent] = useState('');
  const [generatedContent, setGeneratedContent] = useState('');
  const abortControllerRef = useRef(null);

  const noteDefaults = {
    content: '',
    editContent: '',
    isEditing: false,
    contentLoading: false,
    saveLoading: false,
    hasLoaded: false,
  };

  const updateNoteState = (noteKey, patch) => {
    if (!noteKey) return;
    setNoteStates(prev => ({
      ...prev,
      [noteKey]: {
        ...noteDefaults,
        ...prev[noteKey],
        ...patch,
      }
    }));
  };

  const activeNoteKey = activeMainTab.startsWith('note:') ? activeMainTab.slice(5) : null;
  const activeNote = activeNoteKey ? openNotes.find(note => note.key === activeNoteKey) : null;
  const activeNoteState = activeNoteKey && noteStates[activeNoteKey] ? noteStates[activeNoteKey] : noteDefaults;
  const selectedFile = activeNote ? { key: activeNote.key, title: activeNote.title } : null;
  const fileContent = activeNoteState.content;

  // 拖动调整宽度状态
  const [leftSiderWidth, setLeftSiderWidth] = useState(25); // 百分比
  const [rightSiderWidth, setRightSiderWidth] = useState(30); // 百分比
  const [isDragging, setIsDragging] = useState(null); // 'left' | 'right' | null
  const containerRef = useRef(null);

  // 切换展开/收起
  const toggleExpand = () => {
    const getAllKeys = (nodes) => {
      let keys = [];
      nodes.forEach(node => {
        if (node.children) {
          keys.push(node.key);
          keys = keys.concat(getAllKeys(node.children));
        }
      });
      return keys;
    };
    if (expandedKeys.length === 0) {
      setExpandedKeys(getAllKeys(treeData));
    } else {
      setExpandedKeys([]);
    }
  };

  // 加载文件树
  const loadTree = async () => {
    setLoading(true);
    try {
      const response = await getFileTree();
      setTreeData(response.data.tree);
      message.success('文件树加载成功');
    } catch (error) {
      if (error.response?.status === 404) {
        message.error('请先配置知识库路径');
      } else {
        message.error('加载文件树失败: ' + (error.response?.data?.message || error.message));
      }
    } finally {
      setLoading(false);
    }
  };

  // 页面加载时读取文件树
  useEffect(() => {
    if (!hasInitialized.current) {
      hasInitialized.current = true;
      loadTree();
    }
  }, []);

  useEffect(() => {
    if (configTabVisible) {
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
  }, [configTabVisible, activeMainTab, openNotes]);

  useEffect(() => {
    if (configTabRequestId > 0) {
      setActiveMainTab('config');
    }
  }, [configTabRequestId]);

  useEffect(() => {
    if (activeNoteKey) {
      setUserInput('');
      setChatMessages([]);
      setPreviewMode(false);
      setOriginalContent('');
      setGeneratedContent('');
    }
  }, [activeNoteKey]);
  // 处理文件选择
  const handleSelect = async (selectedKeys, info) => {
    const node = info.node;
    if (node.is_leaf) {
      // 检查文件扩展名
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
        updateNoteState(noteKey, { contentLoading: false });
        message.error('读取文件失败: ' + (error.response?.data?.message || error.message));
      }
    }
  };

  const getNoteState = (noteKey) => noteStates[noteKey] || noteDefaults;

  // 开始编辑
  const handleStartEdit = (noteKey) => {
    const noteState = getNoteState(noteKey);
    updateNoteState(noteKey, { editContent: noteState.content, isEditing: true });
  };

  // 取消编辑
  const handleCancelEdit = (noteKey) => {
    const noteState = getNoteState(noteKey);
    updateNoteState(noteKey, { editContent: noteState.content, isEditing: false });
  };

  // 保存编辑
  const handleSave = async (noteKey) => {
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
  };

  // AI 消息发送
  const handleSendAiMessage = async () => {
    if (!userInput.trim() || !activeNoteKey) {
      message.warning('请输入问题并选择笔记');
      return;
    }

    // AI编辑模式：切换到预览模式
    if (aiMode === 'edit') {
      setPreviewMode(true);
      setOriginalContent(fileContent);
      setGeneratedContent('');
      setAiGenerating(true);

      // 创建 AbortController 用于中断请求
      abortControllerRef.current = new AbortController();

      try {
        const stream = await aiEdit(activeNoteKey, userInput, abortControllerRef.current.signal);

        // 流式读取响应
        for await (const chunk of readStream(stream, abortControllerRef.current.signal)) {
          console.log('[handleSendAiMessage] Received chunk:', chunk);
          setGeneratedContent(prev => {
            const newContent = prev + chunk;
            console.log('[handleSendAiMessage] Generated content length:', newContent.length);
            return newContent;
          });
        }
        console.log('[handleSendAiMessage] Stream finished');
      } catch (error) {
        console.error('[handleSendAiMessage] Error:', error);
        message.error('AI 编辑失败: ' + error.message);
        setPreviewMode(false);
        setOriginalContent('');
        setGeneratedContent('');
      } finally {
        console.log('[handleSendAiMessage] Finally block, setting aiGenerating to false');
        setAiGenerating(false);
        abortControllerRef.current = null;
      }
      return;
    }

    // AI建议模式：在对话中显示
    const newMessage = { role: 'user', content: userInput };
    setChatMessages(prev => [...prev, newMessage]);
    setUserInput('');
    setAiGenerating(true);

    // 创建 AbortController 用于中断请求
    abortControllerRef.current = new AbortController();

    try {
      const stream = await aiAdvise(activeNoteKey, userInput, abortControllerRef.current.signal);

      // 先添加一个空的AI响应消息
      setChatMessages(prev => [...prev, { role: 'assistant', content: '' }]);

      // 流式读取响应
      for await (const chunk of readStream(stream, abortControllerRef.current.signal)) {
        setChatMessages(prev => {
          const newMessages = [...prev];
          const lastIndex = newMessages.length - 1;
          // 创建新对象，避免引用问题
          newMessages[lastIndex] = {
            ...newMessages[lastIndex],
            content: newMessages[lastIndex].content + chunk
          };
          return newMessages;
        });
      }
    } catch (error) {
      message.error('AI 请求失败: ' + error.message);
      setChatMessages(prev => [...prev, {
        role: 'assistant',
        content: `错误：${error.message}`
      }]);
    } finally {
      setAiGenerating(false);
      abortControllerRef.current = null;
    }
  };

  // 一键排版
  const handleOneClickOptimize = async () => {
    if (!activeNoteKey) {
      message.warning('请先选择笔记');
      return;
    }

    console.log('[handleOneClickOptimize] Starting optimization for file:', activeNoteKey);
    setPreviewMode(true);
    setOriginalContent(fileContent);
    setGeneratedContent('');
    setAiGenerating(true);

    // 创建 AbortController 用于中断请求
    abortControllerRef.current = new AbortController();

    try {
      const stream = await aiOptimize(activeNoteKey, abortControllerRef.current.signal);
      console.log('[handleOneClickOptimize] Stream received');

      // 流式读取响应
      for await (const chunk of readStream(stream, abortControllerRef.current.signal)) {
        console.log('[handleOneClickOptimize] Received chunk:', chunk);
        setGeneratedContent(prev => {
          const newContent = prev + chunk;
          console.log('[handleOneClickOptimize] Generated content length:', newContent.length);
          return newContent;
        });
      }
      console.log('[handleOneClickOptimize] Stream finished');
    } catch (error) {
      console.error('[handleOneClickOptimize] Error:', error);
      message.error('排版失败: ' + error.message);
      setPreviewMode(false);
      setOriginalContent('');
      setGeneratedContent('');
    } finally {
      console.log('[handleOneClickOptimize] Finally block, setting aiGenerating to false');
      setAiGenerating(false);
      abortControllerRef.current = null;
    }
  };

  // 确认保存 AI 生成的内容
  const handleConfirmAiResult = async () => {
    if (!activeNoteKey) return;

    updateNoteState(activeNoteKey, { saveLoading: true });
    try {
      await updateFileContent(activeNoteKey, generatedContent);
      updateNoteState(activeNoteKey, { content: generatedContent, editContent: generatedContent, hasLoaded: true });
      setPreviewMode(false);
      message.success('AI 生成的内容已保存到文件');
    } catch (error) {
      message.error('保存失败: ' + (error.response?.data?.message || error.message));
    } finally {
      updateNoteState(activeNoteKey, { saveLoading: false });
    }
  };

  // 取消 AI 生成或结果
  const handleCancelAiResult = () => {
    // 如果正在生成，中断请求
    if (aiGenerating && abortControllerRef.current) {
      abortControllerRef.current.abort();
      console.log('[handleCancelAiResult] Aborting AI generation');
    }
    setPreviewMode(false);
    setOriginalContent('');
    setGeneratedContent('');
    setAiGenerating(false);
  };

  // 拖动处理函数
  const handleMouseDown = (side) => (e) => {
    e.preventDefault();
    setIsDragging(side);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  };

  const handleMouseMove = (e) => {
    if (!isDragging || !containerRef.current) return;

    const containerRect = containerRef.current.getBoundingClientRect();
    const containerWidth = containerRect.width;
    const mouseX = e.clientX - containerRect.left;
    
    if (isDragging === 'left') {
      // 拖动左侧分割线
      const newLeftWidth = Math.max(20, Math.min(40, (mouseX / containerWidth) * 100));
      setLeftSiderWidth(newLeftWidth);
    } else if (isDragging === 'right') {
      // 拖动右侧分割线
      // 鼠标位置相对于容器的百分比
      const mousePercent = (mouseX / containerWidth) * 100;
      // 右侧边栏的宽度 = 100% - 鼠标位置（因为分割线在右侧边栏的左边）
      const newRightWidth = Math.max(20, Math.min(40, 100 - mousePercent));
      setRightSiderWidth(newRightWidth);
    }
  };

  const handleMouseUp = () => {
    if (isDragging) {
      setIsDragging(null);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    }
  };

  // 添加全局鼠标事件监听
  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, leftSiderWidth, rightSiderWidth, aiSidebarVisible]);

  const handleMainTabEdit = (targetKey, action) => {
    if (action !== 'remove') return;

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
    }
  };

  const renderNoteTab = (noteKey) => {
    const noteState = getNoteState(noteKey);
    const noteInfo = openNotes.find(note => note.key === noteKey);
    const noteTitle = noteInfo?.title || noteKey;

    return (
      <Card
        title={
          <Space>
            <FileOutlined style={{ color: '#1890ff' }} />
            <Text strong style={{ fontSize: 16 }}>{noteTitle}</Text>
            <Tag color="blue">Markdown</Tag>
          </Space>
        }
        extra={
          <Space>
            {!noteState.isEditing && (
              <Button
                type="text"
                icon={<EditOutlined />}
                onClick={() => handleStartEdit(noteKey)}
              >
                编辑
              </Button>
            )}
          </Space>
        }
        bordered={false}
        style={{
          height: '100%',
          borderRadius: 0,
          boxShadow: 'none',
        }}
        bodyStyle={{
          padding: noteState.content ? '24px' : '48px',
          height: 'calc(100% - 60px)',
          overflow: 'auto',
        }}
      >
        <Spin spinning={noteState.contentLoading || noteState.saveLoading}>
          {noteState.isEditing ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', height: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                <Button icon={<CloseOutlined />} onClick={() => handleCancelEdit(noteKey)}>
                  取消
                </Button>
                <Button type="primary" icon={<CheckOutlined />} onClick={() => handleSave(noteKey)}>
                  保存
                </Button>
              </div>
              <TextArea
                value={noteState.editContent}
                onChange={(e) => updateNoteState(noteKey, { editContent: e.target.value })}
                style={{
                  fontFamily: 'SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace',
                  fontSize: 14,
                  lineHeight: 1.6,
                  height: 'calc(100vh - 250px)',
                  minHeight: '500px',
                }}
                placeholder="输入 Markdown 内容..."
              />
            </div>
          ) : (
            noteState.content ? (
              <div style={{
                padding: '20px',
                backgroundColor: '#fff',
                borderRadius: '8px',
              }}>
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[rehypeHighlight, rehypeRaw]}
                  components={{
                    h1: ({ children }) => <h1 style={{ fontSize: '2em', fontWeight: 'bold', marginTop: '1.5em', marginBottom: '0.8em', borderBottom: '1px solid #eaecef', paddingBottom: '0.3em' }}>{children}</h1>,
                    h2: ({ children }) => <h2 style={{ fontSize: '1.5em', fontWeight: 'bold', marginTop: '1.5em', marginBottom: '0.8em', borderBottom: '1px solid #eaecef', paddingBottom: '0.3em' }}>{children}</h2>,
                    h3: ({ children }) => <h3 style={{ fontSize: '1.25em', fontWeight: 'bold', marginTop: '1.5em', marginBottom: '0.8em' }}>{children}</h3>,
                    p: ({ children }) => <p style={{ lineHeight: '1.8', marginBottom: '1em', color: '#24292e' }}>{children}</p>,
                    ul: ({ children }) => <ul style={{ paddingLeft: '2em', marginBottom: '1em', lineHeight: '1.8' }}>{children}</ul>,
                    ol: ({ children }) => <ol style={{ paddingLeft: '2em', marginBottom: '1em', lineHeight: '1.8' }}>{children}</ol>,
                    li: ({ children }) => <li style={{ marginBottom: '0.5em' }}>{children}</li>,
                    code: ({ inline, className, children, ...props }) => {
                      if (inline) {
                        return <code style={{
                          backgroundColor: 'rgba(27, 31, 35, 0.05)',
                          padding: '0.2em 0.4em',
                          borderRadius: '3px',
                          fontFamily: 'SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace',
                          fontSize: '85%'
                        }} {...props}>{children}</code>;
                      }
                      return <code className={className} {...props}>{children}</code>;
                    },
                    pre: ({ children }) => <pre style={{
                      backgroundColor: '#ffffff',
                      padding: '16px',
                      borderRadius: '6px',
                      overflow: 'auto',
                      marginBottom: '1em',
                      border: '1px solid #e8e8e8'
                    }}>{children}</pre>,
                    blockquote: ({ children }) => <blockquote style={{
                      borderLeft: '4px solid #dfe2e5',
                      padding: '0 1em',
                      color: '#6a737d',
                      marginLeft: '0',
                      marginBottom: '1em'
                    }}>{children}</blockquote>,
                    table: ({ children }) => <table style={{
                      width: '100%',
                      borderCollapse: 'collapse',
                      marginBottom: '1em'
                    }}>{children}</table>,
                    thead: ({ children }) => <thead>{children}</thead>,
                    tbody: ({ children }) => <tbody>{children}</tbody>,
                    tr: ({ children }) => <tr style={{ borderBottom: '1px solid #eaecef' }}>{children}</tr>,
                    th: ({ children }) => <th style={{
                      padding: '6px 13px',
                      fontWeight: '600',
                      borderBottom: '1px solid #dfe2e5',
                      backgroundColor: '#f6f8fa',
                      textAlign: 'left'
                    }}>{children}</th>,
                    td: ({ children }) => <td style={{
                      padding: '6px 13px',
                      borderBottom: '1px solid #eaecef',
                      textAlign: 'left'
                    }}>{children}</td>,
                    a: ({ children, href }) => <a href={href} style={{ color: '#0366d6', textDecoration: 'none' }}>{children}</a>,
                  }}
                >
                  {noteState.content}
                </ReactMarkdown>
              </div>
            ) : (
              <Empty
                description={
                  <Space direction="vertical" size="small">
                    <Paragraph type="secondary">请在左侧文件树中选择文件</Paragraph>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      仅支持预览和编辑 Markdown 格式文件
                    </Text>
                  </Space>
                }
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                style={{ marginTop: 80 }}
              />
            )
          )}
        </Spin>
      </Card>
    );
  };

  const noteTabs = openNotes.map(note => ({
    key: `note:${note.key}`,
    label: note.title || note.key,
    closable: true,
    children: renderNoteTab(note.key),
  }));

  const tabItems = [
    ...(openNotes.length > 0 ? noteTabs : [{
      key: 'notes',
      label: '笔记',
      closable: false,
      children: (
        <Empty
          description={
            <Space direction="vertical" size="small">
              <Paragraph type="secondary">请在左侧文件树中选择文件</Paragraph>
              <Text type="secondary" style={{ fontSize: 12 }}>
                仅支持预览和编辑 Markdown 格式文件
              </Text>
            </Space>
          }
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          style={{ marginTop: 80 }}
        />
      )
    }]),
    ...(configTabVisible ? [
      {
        key: 'config',
        label: '系统配置',
        closable: true,
        children: <ConfigPage embedded />,
      }
    ] : [])
  ];

  return (
    <div 
      ref={containerRef}
      style={{
        flex: 1,
        display: 'flex',
        height: '100%',
        overflow: 'hidden',
        background: '#f5f7fa',
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
          background: '#fff',
          borderRight: '1px solid #e8e8e8',
          boxShadow: '2px 0 8px rgba(0,0,0,0.06)',
          transition: isDragging ? 'none' : 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          margin: 0,
          height: '100%',
        }}
      >
        <div style={{
          height: '100%',
          padding: '0',
          background: '#f5f7fa',
          display: 'flex',
          flexDirection: 'column',
        }}>
          <div style={{ height: '100%', background: '#fff', display: 'flex', flexDirection: 'column' }}>
          <div style={{
            padding: '16px',
            borderBottom: '1px solid #f0f0f0',
            background: '#fff',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}>
            <Button
              type="text"
              size="small"
              icon={expandedKeys.length > 0 ? <FolderOutlined /> : <FolderOpenOutlined />}
              onClick={toggleExpand}
              style={{ width: 32, height: 32, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            />
            <Button
              type="text"
              size="small"
              icon={<ReloadOutlined />}
              onClick={loadTree}
              style={{ width: 32, height: 32, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            />
          </div>

          <div style={{ padding: '16px', flex: 1, overflowY: 'auto' }}>
            <Spin spinning={loading}>
              {treeData.length > 0 ? (
                <DirectoryTree
                  showIcon
                  expandedKeys={expandedKeys}
                  onExpand={setExpandedKeys}
                  onSelect={handleSelect}
                  treeData={treeData}
                  icon={({ is_leaf }) =>
                    is_leaf ? <FileOutlined style={{ color: '#1890ff' }} /> : <FolderOutlined style={{ color: '#faad14' }} />
                  }
                  style={{ fontSize: 14 }}
                />
              ) : (
                <Empty
                  description="暂无文件"
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  style={{ marginTop: 60 }}
                />
              )}
            </Spin>
          </div>
        </div>
        </div>
      </Sider>

      {/* 左侧分割线 */}
      <div
        onMouseDown={handleMouseDown('left')}
        style={{
          width: '4px',
          height: '100%',
          background: '#e8e8e8',
          cursor: 'col-resize',
          position: 'relative',
          zIndex: 10,
        }}
        onMouseEnter={(e) => { e.target.style.background = '#1890ff'; }}
        onMouseLeave={(e) => { e.target.style.background = '#e8e8e8'; }}
      >
        <div style={{
          position: 'absolute',
          left: '1px',
          top: '50%',
          transform: 'translateY(-50%)',
          width: '2px',
          height: '20px',
          background: '#999',
          borderRadius: '2px',
        }} />
      </div>

      {/* 主内容区 */}
      <Content style={{ padding: '0', height: '100%', overflow: 'hidden', flex: 1, margin: 0, maxWidth: 'none' }}>
        <div style={{
          height: '100%',
          padding: '0',
          background: '#f5f7fa',
        }}>
          <Tabs
            className="knowledge-tabs"
            type="editable-card"
            hideAdd
            activeKey={activeMainTab}
            onChange={setActiveMainTab}
            onEdit={handleMainTabEdit}
            items={tabItems}
            tabBarStyle={{
              margin: 0,
              padding: '0 16px',
              background: '#fff',
              borderBottom: '1px solid #f0f0f0',
            }}
            style={{ height: '100%' }}
          />
          <style>{`
            .knowledge-tabs {
              height: 100%;
              display: flex;
              flex-direction: column;
            }
            .knowledge-tabs .ant-tabs-content-holder {
              flex: 1;
              min-height: 0;
            }
            .knowledge-tabs .ant-tabs-content,
            .knowledge-tabs .ant-tabs-tabpane {
              height: 100%;
            }
          `}</style>
        </div>
      </Content>

      {/* 右侧分割线 */}
      <div
        onMouseDown={aiSidebarVisible ? handleMouseDown('right') : undefined}
        style={{
          width: aiSidebarVisible ? '4px' : '0',
          height: '100%',
          background: '#e8e8e8',
          cursor: aiSidebarVisible ? 'col-resize' : 'default',
          position: 'relative',
          zIndex: 10,
          transition: isDragging ? 'none' : 'width 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          pointerEvents: aiSidebarVisible ? 'auto' : 'none',
        }}
        onMouseEnter={(e) => { if (aiSidebarVisible) e.target.style.background = '#1890ff'; }}
        onMouseLeave={(e) => { if (aiSidebarVisible) e.target.style.background = '#e8e8e8'; }}
      >
        {aiSidebarVisible && (
          <div style={{
            position: 'absolute',
            left: '1px',
            top: '50%',
            transform: 'translateY(-50%)',
            width: '2px',
            height: '20px',
            background: '#999',
            borderRadius: '2px',
          }} />
        )}
      </div>

      {/* AI 侧边栏 */}
      <Sider
        width={`${rightSiderWidth}%`}
        collapsed={!aiSidebarVisible}
        collapsedWidth={0}
        style={{
          background: '#fff',
          borderLeft: '1px solid #e8e8e8',
          boxShadow: '-2px 0 8px rgba(0,0,0,0.06)',
          overflow: 'hidden',
          transition: isDragging ? 'none' : 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          margin: 0,
          height: '100%',
        }}
      >
        <div style={{
          height: '100%',
          padding: '0',
          background: '#f5f7fa',
          display: 'flex',
          flexDirection: 'column',
          opacity: aiSidebarVisible ? 1 : 0,
          pointerEvents: aiSidebarVisible ? 'auto' : 'none',
          transition: isDragging ? 'none' : 'opacity 0.2s ease',
        }}>
          <div style={{ height: '100%', background: '#fff', display: 'flex', flexDirection: 'column' }}>
          <div style={{
            padding: '16px',
            borderBottom: '1px solid #f0f0f0',
            background: '#fafafa',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}>
              <Text strong>{previewMode ? 'AI 排版预览' : (aiMode === 'advise' ? 'AI 建议' : 'AI 编辑')}</Text>
              <Space size="small">
                {aiGenerating && <span style={{ color: '#1890ff' }}>(生成中...)</span>}
              </Space>
            </div>
            {previewMode ? (
              /* 预览模式：显示AI编辑后的内容 */
              <div style={{ height: '100%', minHeight: 0, display: 'flex', flexDirection: 'column' }}>
                <div style={{ flex: 1, minHeight: 0, padding: '16px', overflow: 'auto' }}>
                  <div style={{ fontSize: 12, color: '#999', marginBottom: 8 }}>
                    内容长度: {generatedContent.length} 字符
                  </div>
                  <ReactMarkdown
                    key={generatedContent}
                    remarkPlugins={[remarkGfm]}
                    rehypePlugins={[rehypeHighlight, rehypeRaw]}
                    components={{
                      h1: ({ children }) => <h1 style={{ fontSize: '1.8em', fontWeight: 'bold', marginTop: '1.2em', marginBottom: '0.6em', borderBottom: '1px solid #eaecef', paddingBottom: '0.3em' }}>{children}</h1>,
                      h2: ({ children }) => <h2 style={{ fontSize: '1.4em', fontWeight: 'bold', marginTop: '1.2em', marginBottom: '0.6em', borderBottom: '1px solid #eaecef', paddingBottom: '0.3em' }}>{children}</h2>,
                      h3: ({ children }) => <h3 style={{ fontSize: '1.2em', fontWeight: 'bold', marginTop: '1.2em', marginBottom: '0.6em' }}>{children}</h3>,
                      p: ({ children }) => <p style={{ lineHeight: '1.8', marginBottom: '1em', color: '#24292e' }}>{children}</p>,
                      ul: ({ children }) => <ul style={{ paddingLeft: '2em', marginBottom: '1em', lineHeight: '1.8' }}>{children}</ul>,
                      ol: ({ children }) => <ol style={{ paddingLeft: '2em', marginBottom: '1em', lineHeight: '1.8' }}>{children}</ol>,
                      li: ({ children }) => <li style={{ marginBottom: '0.5em' }}>{children}</li>,
                      code: ({ inline, className, children, ...props }) => {
                        if (inline) {
                          return <code style={{
                            backgroundColor: 'rgba(27, 31, 35, 0.05)',
                            padding: '0.2em 0.4em',
                            borderRadius: '3px',
                            fontFamily: 'SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace',
                            fontSize: '85%'
                          }} {...props}>{children}</code>;
                        }
                        return <code className={className} {...props}>{children}</code>;
                      },
                      pre: ({ children }) => <pre style={{
                        backgroundColor: '#ffffff',
                        padding: '12px',
                        borderRadius: '6px',
                        overflow: 'auto',
                        marginBottom: '1em',
                        border: '1px solid #e8e8e8'
                      }}>{children}</pre>,
                      blockquote: ({ children }) => <blockquote style={{
                        borderLeft: '4px solid #dfe2e5',
                        padding: '0 1em',
                        color: '#6a737d',
                        marginLeft: '0',
                        marginBottom: '1em'
                      }}>{children}</blockquote>,
                      table: ({ children }) => <table style={{
                        width: '100%',
                        borderCollapse: 'collapse',
                        marginBottom: '1em'
                      }}>{children}</table>,
                      thead: ({ children }) => <thead>{children}</thead>,
                      tbody: ({ children }) => <tbody>{children}</tbody>,
                      tr: ({ children }) => <tr style={{ borderBottom: '1px solid #eaecef' }}>{children}</tr>,
                      th: ({ children }) => <th style={{
                        padding: '6px 13px',
                        fontWeight: '600',
                        borderBottom: '1px solid #dfe2e5',
                        backgroundColor: '#f6f8fa',
                        textAlign: 'left'
                      }}>{children}</th>,
                      td: ({ children }) => <td style={{
                        padding: '6px 13px',
                        borderBottom: '1px solid #eaecef',
                        textAlign: 'left'
                      }}>{children}</td>,
                      a: ({ children, href }) => <a href={href} style={{ color: '#0366d6', textDecoration: 'none' }}>{children}</a>,
                    }}
                  >
                    {generatedContent || (aiGenerating && '等待 AI 生成内容...')}
                  </ReactMarkdown>
                </div>
                <div style={{
                  padding: '12px',
                  borderTop: '1px solid #f0f0f0',
                  display: 'flex',
                  gap: '8px',
                }}>
                  <Button
                    icon={<CloseOutlined />}
                    onClick={handleCancelAiResult}
                    disabled={!aiGenerating && !generatedContent}
                    style={{ flex: 1 }}
                  >
                    {aiGenerating ? '取消生成' : '取消'}
                  </Button>
                  <Button
                    type="primary"
                    icon={<CheckOutlined />}
                    onClick={handleConfirmAiResult}
                    disabled={aiGenerating || !generatedContent}
                    style={{ flex: 1 }}
                  >
                    确认保存
                  </Button>
                </div>
              </div>
            ) : (
              /* 对话模式 */
              <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              {/* 上方 2/3：对话显示 */}
              <div style={{
                flex: 2,
                padding: '16px',
                overflow: 'auto',
                borderBottom: '1px solid #f0f0f0',
              }}>
                <Space direction="vertical" style={{ width: '100%' }} size="middle">
                  {chatMessages.length === 0 && (
                    <Empty
                      description={
                        <Space direction="vertical" size="small">
                          <Text type="secondary">开始与 AI 对话</Text>
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            {aiMode === 'advise' ? 'AI 建议模式' : 'AI 编辑模式'}
                          </Text>
                        </Space>
                      }
                      image={Empty.PRESENTED_IMAGE_SIMPLE}
                    />
                  )}
                  {chatMessages.map((msg, index) => (
                    <div
                      key={index}
                      style={{
                        padding: '12px',
                        borderRadius: '8px',
                        background: msg.role === 'user' ? '#e6f7ff' : '#f6f8fa',
                        maxWidth: '85%',
                        alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                      }}
                    >
                      <Text strong style={{ display: 'block', marginBottom: '4px', fontSize: 12 }}>
                        {msg.role === 'user' ? '用户' : 'AI'}
                      </Text>
                      {msg.role === 'assistant' ? (
                        <div style={{ fontSize: 13, lineHeight: '1.6' }}>
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            rehypePlugins={[rehypeHighlight, rehypeRaw]}
                            components={{
                              h1: ({ children }) => <h1 style={{ fontSize: '1.5em', fontWeight: 'bold', marginTop: '0.8em', marginBottom: '0.4em' }}>{children}</h1>,
                              h2: ({ children }) => <h2 style={{ fontSize: '1.3em', fontWeight: 'bold', marginTop: '0.8em', marginBottom: '0.4em' }}>{children}</h2>,
                              h3: ({ children }) => <h3 style={{ fontSize: '1.1em', fontWeight: 'bold', marginTop: '0.6em', marginBottom: '0.3em' }}>{children}</h3>,
                              p: ({ children }) => <p style={{ margin: '0.4em 0' }}>{children}</p>,
                              ul: ({ children }) => <ul style={{ paddingLeft: '1.5em', margin: '0.4em 0' }}>{children}</ul>,
                              ol: ({ children }) => <ol style={{ paddingLeft: '1.5em', margin: '0.4em 0' }}>{children}</ol>,
                              li: ({ children }) => <li style={{ marginBottom: '0.2em' }}>{children}</li>,
                              code: ({ inline, className, children, ...props }) => {
                                if (inline) {
                                  return <code style={{
                                    backgroundColor: 'rgba(27, 31, 35, 0.05)',
                                    padding: '0.1em 0.3em',
                                    borderRadius: '3px',
                                    fontFamily: 'SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace',
                                    fontSize: '0.9em'
                                  }} {...props}>{children}</code>;
                                }
                                return <code className={className} {...props}>{children}</code>;
                              },
                              pre: ({ children }) => <pre style={{
                                backgroundColor: '#ffffff',
                                padding: '8px',
                                borderRadius: '4px',
                                overflow: 'auto',
                                margin: '0.4em 0',
                                fontSize: '12px',
                                border: '1px solid #e8e8e8'
                              }}>{children}</pre>,
                              blockquote: ({ children }) => <blockquote style={{
                                borderLeft: '3px solid #dfe2e5',
                                padding: '0 0.8em',
                                color: '#6a737d',
                                margin: '0.4em 0',
                                fontSize: '0.95em'
                              }}>{children}</blockquote>,
                            }}
                          >
                            {msg.content}
                          </ReactMarkdown>
                        </div>
                      ) : (
                        <Paragraph style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: 13 }}>
                          {msg.content}
                        </Paragraph>
                      )}
                    </div>
                  ))}
                  {aiGenerating && (
                    <div style={{
                      padding: '12px',
                      borderRadius: '8px',
                      background: '#f6f8fa',
                      maxWidth: '85%',
                    }}>
                      <Text type="secondary">AI 正在生成...</Text>
                    </div>
                  )}
                </Space>
              </div>

              {/* 下方 1/3：输入区域 */}
              <div style={{
                flex: 1,
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
              }}>
                {/* 输入框 */}
                <TextArea
                  value={userInput}
                  onChange={(e) => setUserInput(e.target.value)}
                  placeholder={aiMode === 'advise' ? '请输入您的问题...' : '请输入编辑要求...'}
                  onPressEnter={(e) => {
                    if (!e.shiftKey) {
                      e.preventDefault();
                      handleSendAiMessage();
                    }
                  }}
                  autoSize={{ minRows: 3, maxRows: 6 }}
                  style={{ flex: 1 }}
                />

                {/* 底部操作栏 */}
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  {/* 模式选择下拉框 */}
                  <Select
                    value={aiMode}
                    onChange={setAiMode}
                    style={{ width: 100 }}
                    size="small"
                  >
                    <Select.Option value="advise">
                      <Space size="small">
                        <ThunderboltOutlined />
                        AI 建议
                      </Space>
                    </Select.Option>
                    <Select.Option value="edit">
                      <Space size="small">
                        <EditOutlined2 />
                        AI 编辑
                      </Space>
                    </Select.Option>
                  </Select>

                  {/* 一键排版按钮 */}
                  <Button
                    type="primary"
                    icon={<BgColorsOutlined />}
                    onClick={handleOneClickOptimize}
                    disabled={aiGenerating || !selectedFile}
                    style={{ flex: 1 }}
                  >
                    一键排版
                  </Button>

                  {/* 发送按钮 */}
                  <Button
                    type="primary"
                    icon={<SendOutlined />}
                    onClick={handleSendAiMessage}
                    disabled={aiGenerating || !userInput.trim()}
                    style={{ flex: 1 }}
                  >
                    发送
                  </Button>
                </div>
              </div>
            </div>
            )}
          </div>
        </div>
        </Sider>
    </div>
  );
}

export default KnowledgePage;
