import { useEffect, useRef, useCallback } from 'react';
import {
  Typography, Input, Button, Space, Tag, Collapse, Spin,
  Switch, Tooltip,
} from 'antd';
import {
  SendOutlined, StopOutlined, RobotOutlined, SearchOutlined,
  BulbOutlined, FileTextOutlined, CloseCircleOutlined,
  PlusOutlined, LockOutlined, EditOutlined, InfoCircleOutlined,
  DiffOutlined, CheckCircleOutlined,
} from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import { remarkPlugins, rehypePlugins, createMarkdownComponents } from '../../utils/markdownStyles.jsx';
import { SourceList } from './SourceCard';
import { useUnifiedAgent } from '../../hooks/useUnifiedAgent';
import { COLORS } from '../../styles/tokens';

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

function AgentSidebar({ visible, isDragging, activeNote, noteContent, onOpenDiffTab, onOpenChunk }) {
  const {
    permissionMode, setPermissionMode,
    conversations,
    userInput, setUserInput,
    loading,
    streamState,
    sendMessage,
    stopGeneration,
    newSession,
    openDiffPreview,
    markDiffApplied,
    cancelDiffPreview,
  } = useUnifiedAgent();

  const messagesEndRef = useRef(null);
  const lastAutoOpenedRef = useRef(-1);

  // 自动滚动
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversations, streamState.answer, streamState.diff, streamState.processMessages]);

  // 发送
  const handleSend = useCallback(() => {
    if (!userInput.trim() || loading) return;
    const text = userInput.trim();
    setUserInput('');
    sendMessage(text, noteContent, activeNote?.title || null);
  }, [userInput, loading, setUserInput, sendMessage, noteContent, activeNote]);

  // 在主区域打开双栏对比标签页
  const handleOpenDiffInMain = useCallback((index) => {
    const entry = conversations[index];
    if (!entry?.diff) return;

    // 标记 hook 内部状态
    openDiffPreview(index);

    // 通知父组件在主区域打开对比标签
    if (onOpenDiffTab) {
      onOpenDiffTab({
        originalContent: noteContent || '',
        editedContent: entry.editedContent || '',
        diffText: entry.diff,
        documentName: activeNote?.title || '未命名文档',
        noteKey: activeNote?.key || null,
        onApplied: () => markDiffApplied(index),
        onCancelled: () => cancelDiffPreview(),
      });
    }
  }, [conversations, openDiffPreview, onOpenDiffTab, noteContent, activeNote, markDiffApplied, cancelDiffPreview]);

  // 流式结束后自动打开新 diff 的对比标签页
  useEffect(() => {
    if (loading) return;
    for (let i = conversations.length - 1; i >= 0; i--) {
      const entry = conversations[i];
      if (entry.role === 'assistant' && entry.diff && !entry.diffApplied) {
        if (i > lastAutoOpenedRef.current) {
          lastAutoOpenedRef.current = i;
          handleOpenDiffInMain(i);
        }
        break;
      }
    }
  }, [conversations, loading, handleOpenDiffInMain]);

  // 渲染过程消息 tag
  const renderProcessTag = (msg, index) => {
    switch (msg.type) {
      case 'status':
        return (
          <div key={index} style={{ marginBottom: 4 }}>
            <Tag icon={<Spin size="small" />} color="processing" style={{ fontSize: 11 }}>
              {msg.content}
              {msg.data?.round && ` (${msg.data.round}轮)`}
            </Tag>
          </div>
        );
      case 'thinking':
        return (
          <div key={index} style={{ marginBottom: 4 }}>
            <Collapse ghost size="small">
              <Collapse.Panel
                header={<span style={{ color: COLORS.textSecondary, fontSize: 11 }}><BulbOutlined /> 思考</span>}
                key="1"
              >
                <Paragraph style={{ margin: 0, color: COLORS.textSecondary, fontSize: 11 }}>{msg.content}</Paragraph>
              </Collapse.Panel>
            </Collapse>
          </div>
        );
      case 'sources':
        return (
          <div key={index} style={{ marginBottom: 4 }}>
            <Tag icon={<FileTextOutlined />} color="green" style={{ fontSize: 11 }}>{msg.content}</Tag>
          </div>
        );
      case 'prompt':
        return (
          <div key={index} style={{ marginBottom: 4 }}>
            <Tag icon={<InfoCircleOutlined />} color="warning" style={{ fontSize: 11 }}>{msg.content}</Tag>
          </div>
        );
      case 'error':
        return (
          <div key={index} style={{ marginBottom: 4 }}>
            <Tag icon={<CloseCircleOutlined />} color="error" style={{ fontSize: 11 }}>{msg.content}</Tag>
          </div>
        );
      default:
        return null;
    }
  };

  // 渲染单条对话
  const renderMessage = (entry, index) => {
    if (entry.role === 'user') {
      return (
        <div key={index} style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
          <div style={{
            maxWidth: '85%',
            background: COLORS.primary,
            color: '#fff',
            padding: '8px 12px',
            borderRadius: '12px 12px 4px 12px',
            fontSize: 13,
            lineHeight: 1.6,
            whiteSpace: 'pre-wrap',
          }}>
            {entry.content}
          </div>
        </div>
      );
    }

    // assistant 消息
    return (
      <div key={index} style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: 12 }}>
        <div style={{ maxWidth: '92%', width: '100%' }}>
          {/* 过程消息 */}
          {entry.processMessages && entry.processMessages.length > 0 && (
            <Collapse ghost size="small" style={{ marginBottom: 4 }}>
              <Collapse.Panel
                header={
                  <span style={{ color: COLORS.textSecondary, fontSize: 11 }}>
                    <SearchOutlined style={{ marginRight: 4 }} />
                    执行过程 ({entry.processMessages.length})
                  </span>
                }
                key="1"
              >
                {entry.processMessages.map((msg, i) => renderProcessTag(msg, i))}
              </Collapse.Panel>
            </Collapse>
          )}

          {/* 检索来源 */}
          {entry.sources && entry.sources.length > 0 && (
            <SourceList sources={entry.sources} onOpenChunk={onOpenChunk || (() => {})} />
          )}

          {/* 错误信息 */}
          {entry.error && (
            <div style={{
              background: '#fff2f0',
              border: '1px solid #ffccc7',
              padding: '6px 10px',
              borderRadius: 6,
              color: COLORS.error,
              fontSize: 12,
              marginBottom: 4,
            }}>
              {entry.error}
            </div>
          )}

          {/* 文本回复 */}
          {entry.content && (
            <div style={{
              background: COLORS.bgHover,
              padding: '10px 12px',
              borderRadius: '12px 12px 12px 4px',
              fontSize: 13,
              lineHeight: 1.7,
            }}>
              <ReactMarkdown
                remarkPlugins={remarkPlugins}
                rehypePlugins={rehypePlugins}
                components={createMarkdownComponents('compact')}
              >
                {entry.content}
              </ReactMarkdown>
            </div>
          )}

          {/* Diff 状态提示 */}
          {entry.diff && (
            <div style={{
              marginTop: 6,
              padding: '8px 12px',
              background: '#f6f1fe',
              borderRadius: 8,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}>
              <Tag icon={<DiffOutlined />} color="purple" style={{ margin: 0, fontSize: 11 }}>
                文档已修改
              </Tag>
              {entry.diffApplied && (
                <Tag icon={<CheckCircleOutlined />} color="success" style={{ margin: 0, fontSize: 11 }}>
                  已应用
                </Tag>
              )}
            </div>
          )}

          {/* 统计 */}
          {entry.stats && (
            <div style={{ marginTop: 4 }}>
              <Space size={4}>
                {entry.stats.intent_type && (
                  <Tag style={{ fontSize: 10 }}>{entry.stats.intent_type}</Tag>
                )}
                {entry.stats.retrieval_rounds != null && (
                  <Tag style={{ fontSize: 10 }}>检索 {entry.stats.retrieval_rounds} 轮</Tag>
                )}
                {entry.stats.total_sources != null && (
                  <Tag style={{ fontSize: 10 }}>{entry.stats.total_sources} 条来源</Tag>
                )}
              </Space>
            </div>
          )}
        </div>
      </div>
    );
  };

  // 渲染流式输出（当前正在生成）
  const renderStreaming = () => {
    if (!loading) return null;
    const { processMessages, answer, diff, sources } = streamState;
    const hasContent = answer || diff || processMessages.length > 0;

    return (
      <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: 12 }}>
        <div style={{ maxWidth: '92%', width: '100%' }}>
          {/* 实时过程消息 */}
          {processMessages.length > 0 && (
            <div style={{ marginBottom: 4 }}>
              {processMessages.map((msg, i) => renderProcessTag(msg, i))}
            </div>
          )}

          {/* 实时来源 */}
          {sources.length > 0 && (
            <div style={{ marginBottom: 4 }}>
              <Tag icon={<FileTextOutlined />} color="green" style={{ fontSize: 11 }}>
                {sources.length} 条相关内容
              </Tag>
            </div>
          )}

          {/* 实时回答 */}
          {answer && (
            <div style={{
              background: COLORS.bgHover,
              padding: '10px 12px',
              borderRadius: '12px 12px 12px 4px',
              fontSize: 13,
              lineHeight: 1.7,
            }}>
              <ReactMarkdown
                remarkPlugins={remarkPlugins}
                rehypePlugins={rehypePlugins}
                components={createMarkdownComponents('compact')}
              >
                {answer}
              </ReactMarkdown>
              <span style={{
                display: 'inline-block',
                width: 5,
                height: 14,
                background: COLORS.primary,
                marginLeft: 2,
                animation: 'agentBlink 1s step-end infinite',
                verticalAlign: 'text-bottom',
              }} />
            </div>
          )}

          {/* 实时 Diff */}
          {diff && (
            <div style={{ marginTop: 6 }}>
              <Tag icon={<DiffOutlined />} color="purple" style={{ fontSize: 11, marginBottom: 4 }}>
                文档修改中...
              </Tag>
              <pre style={{
                margin: 0,
                padding: '8px 12px',
                background: '#1e1e1e',
                color: '#d4d4d4',
                fontSize: 11,
                lineHeight: 1.4,
                maxHeight: 200,
                overflow: 'auto',
                borderRadius: 6,
              }}>
                {diff}
              </pre>
            </div>
          )}

          {/* 空内容加载态 */}
          {!hasContent && (
            <div style={{
              background: COLORS.bgHover,
              padding: '10px 12px',
              borderRadius: '12px 12px 12px 4px',
            }}>
              <Spin size="small" />
              <Text style={{ marginLeft: 6, color: COLORS.textSecondary, fontSize: 12 }}>思考中...</Text>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div style={{
      height: '100%',
      background: COLORS.bgBase,
      display: 'flex',
      flexDirection: 'column',
      opacity: visible ? 1 : 0,
      pointerEvents: visible ? 'auto' : 'none',
      transition: isDragging ? 'none' : 'opacity 0.2s ease',
    }}>
      <div style={{ height: '100%', background: COLORS.bgCard, display: 'flex', flexDirection: 'column' }}>
            {/* 标题栏 */}
            <div style={{
              padding: '12px 16px',
              borderBottom: `1px solid ${COLORS.borderLight}`,
              background: '#fafafa',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Space size={6}>
                  <Text strong style={{ fontSize: 14 }}>
                    <RobotOutlined style={{ marginRight: 4 }} /> AI Agent
                  </Text>
                  {activeNote && (
                    <Tag icon={<FileTextOutlined />} style={{ fontSize: 10, margin: 0 }}>
                      {activeNote.title?.length > 12
                        ? activeNote.title.slice(0, 12) + '...'
                        : activeNote.title}
                    </Tag>
                  )}
                </Space>
                <Space size={4}>
                  <Tooltip title={`${permissionMode === 'assistant' ? '助手' : '编辑'}模式`}>
                    <Switch
                      size="small"
                      checked={permissionMode === 'editor'}
                      onChange={(c) => setPermissionMode(c ? 'editor' : 'assistant')}
                      checkedChildren={<EditOutlined />}
                      unCheckedChildren={<LockOutlined />}
                    />
                  </Tooltip>
                  <Tooltip title="新会话">
                    <Button size="small" type="text" icon={<PlusOutlined />} onClick={newSession} />
                  </Tooltip>
                </Space>
              </div>
            </div>

            {/* 对话区域 */}
            <div style={{
              flex: 1,
              overflow: 'auto',
              padding: '12px',
              minHeight: 0,
            }}>
              {conversations.length === 0 && !loading && (
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: '100%',
                  color: COLORS.textTertiary,
                  textAlign: 'center',
                  padding: '0 16px',
                }}>
                  <div>
                    <RobotOutlined style={{ fontSize: 36, marginBottom: 12 }} />
                    <div style={{ fontSize: 13, marginBottom: 4 }}>开始对话</div>
                    <div style={{ fontSize: 11 }}>
                      {activeNote
                        ? `当前文档: ${activeNote.title}`
                        : '选择文档后可进行编辑操作'}
                    </div>
                  </div>
                </div>
              )}

              {conversations.map((entry, index) => renderMessage(entry, index))}
              {renderStreaming()}
              <div ref={messagesEndRef} />
            </div>

            {/* 输入区域 */}
            <div style={{
              padding: '12px',
              borderTop: `1px solid ${COLORS.borderLight}`,
            }}>
              <TextArea
                placeholder={activeNote ? `关于 ${activeNote.title} 的问题...` : '输入你的问题...'}
                value={userInput}
                onChange={(e) => setUserInput(e.target.value)}
                autoSize={{ minRows: 2, maxRows: 5 }}
                onPressEnter={(e) => {
                  if (!e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                style={{ marginBottom: 8 }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Text type="secondary" style={{ fontSize: 11 }}>
                  Enter 发送, Shift+Enter 换行
                </Text>
                {loading ? (
                  <Button size="small" danger icon={<StopOutlined />} onClick={stopGeneration}>
                    停止
                  </Button>
                ) : (
                  <Button
                    size="small"
                    type="primary"
                    icon={<SendOutlined />}
                    onClick={handleSend}
                    disabled={!userInput.trim()}
                  >
                    发送
                  </Button>
                )}
              </div>
            </div>
      </div>

      <style>{`
        @keyframes agentBlink {
          50% { opacity: 0; }
        }
      `}</style>
    </div>
  );
}

export default AgentSidebar;
