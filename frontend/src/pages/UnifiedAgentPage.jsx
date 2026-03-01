import { useState, useRef, useCallback, useEffect } from 'react';
import {
  Card, Input, Button, Space, InputNumber, Typography, Tag, Collapse,
  Spin, List, Divider, Switch, Tooltip, Badge,
} from 'antd';
import {
  SendOutlined, StopOutlined, RobotOutlined, SearchOutlined,
  BulbOutlined, FileTextOutlined, CheckCircleOutlined, CloseCircleOutlined,
  PlusOutlined, LockOutlined, EditOutlined, InfoCircleOutlined,
  DiffOutlined, UserOutlined,
} from '@ant-design/icons';
import { unifiedAgentStream, readEventStream } from '../api/ai';
import { useSession } from '../hooks/useSession';
import { COLORS } from '../styles/tokens';

const { TextArea } = Input;
const { Text, Paragraph } = Typography;
const { Panel } = Collapse;

function UnifiedAgentPage() {
  // 会话管理
  const { sessionId, createNewSession } = useSession();

  // 输入状态
  const [userInput, setUserInput] = useState('');
  const [topK, setTopK] = useState(3);
  const [maxRounds, setMaxRounds] = useState(3);
  const [permissionMode, setPermissionMode] = useState('assistant');
  const [documentContent, setDocumentContent] = useState(null);
  const [documentName, setDocumentName] = useState(null);

  // 对话状态
  const [loading, setLoading] = useState(false);
  const [conversations, setConversations] = useState([]); // 多轮对话记录
  const [currentAnswer, setCurrentAnswer] = useState('');
  const [currentDiff, setCurrentDiff] = useState('');
  const [currentSources, setCurrentSources] = useState([]);
  const [currentMessages, setCurrentMessages] = useState([]); // 当前轮的过程消息


  const abortControllerRef = useRef(null);
  const messagesEndRef = useRef(null);

  // 获取当前过程消息快照（需在 handleSend 之前定义）
  const currentMessagesRef = useRef([]);
  useEffect(() => {
    currentMessagesRef.current = currentMessages;
  }, [currentMessages]);
  const getCurrentMessagesSnapshot = useCallback(() => {
    return currentMessagesRef.current;
  }, []);

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversations, currentAnswer, currentDiff, currentMessages]);

  // 发送消息
  const handleSend = useCallback(async () => {
    if (!userInput.trim() || loading) return;

    const inputText = userInput.trim();

    // 将用户消息添加到对话历史
    setConversations(prev => [...prev, {
      role: 'user',
      content: inputText,
      timestamp: Date.now(),
    }]);

    setUserInput('');
    setLoading(true);
    setCurrentAnswer('');
    setCurrentDiff('');
    setCurrentSources([]);
    setCurrentMessages([]);
    abortControllerRef.current = new AbortController();

    try {
      const stream = await unifiedAgentStream(
        {
          userInput: inputText,
          sessionId,
          permissionMode,
          documentContent,
          documentName,
          topK,
          maxRounds,
        },
        { signal: abortControllerRef.current.signal }
      );

      let accumulatedAnswer = '';
      let accumulatedDiff = '';
      let lastSources = [];
      let lastStats = null;

      for await (const event of readEventStream(stream, abortControllerRef.current.signal)) {
        switch (event.type) {
          case 'status':
            setCurrentMessages(prev => [...prev, {
              type: 'status',
              content: event.content,
              data: event.data,
            }]);
            break;

          case 'thinking':
            setCurrentMessages(prev => [...prev, {
              type: 'thinking',
              content: event.content,
            }]);
            break;

          case 'sources':
            lastSources = event.data || [];
            setCurrentSources(lastSources);
            setCurrentMessages(prev => [...prev, {
              type: 'sources',
              content: `找到 ${lastSources.length} 条相关内容`,
              data: lastSources,
            }]);
            break;

          case 'chunk':
            accumulatedAnswer += (event.content || '');
            setCurrentAnswer(accumulatedAnswer);
            break;

          case 'diff':
            accumulatedDiff += (event.content || '');
            setCurrentDiff(accumulatedDiff);
            break;

          case 'prompt':
            // 系统提示（需要选择文档、切换权限等）
            setCurrentMessages(prev => [...prev, {
              type: 'prompt',
              content: event.content,
            }]);
            break;

          case 'error':
            setCurrentMessages(prev => [...prev, {
              type: 'error',
              content: event.content,
            }]);
            break;

          case 'complete':
            lastStats = event.data;
            break;
        }
      }

      // 流结束后，将回复整合到对话历史
      const assistantEntry = {
        role: 'assistant',
        content: accumulatedAnswer,
        diff: accumulatedDiff,
        sources: lastSources,
        messages: [...getCurrentMessagesSnapshot()],
        stats: lastStats,
        timestamp: Date.now(),
      };

      setConversations(prev => [...prev, assistantEntry]);
      setCurrentAnswer('');
      setCurrentDiff('');
      setCurrentSources([]);
      setCurrentMessages([]);

    } catch (error) {
      if (error.name !== 'AbortError') {
        const errorEntry = {
          role: 'assistant',
          content: '',
          error: error.message,
          timestamp: Date.now(),
        };
        setConversations(prev => [...prev, errorEntry]);
      }
    } finally {
      setLoading(false);
      abortControllerRef.current = null;
    }
  }, [userInput, loading, sessionId, permissionMode, documentContent, documentName, topK, maxRounds, getCurrentMessagesSnapshot]);

  // 停止
  const handleStop = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setLoading(false);
  }, []);

  // 新建会话
  const handleNewSession = useCallback(() => {
    createNewSession();
    setConversations([]);
    setCurrentAnswer('');
    setCurrentDiff('');
    setCurrentSources([]);
    setCurrentMessages([]);
    setUserInput('');
  }, [createNewSession]);

  // 渲染过程消息
  const renderProcessMessage = (msg, index) => {
    switch (msg.type) {
      case 'status':
        return (
          <div key={index} style={{ marginBottom: 6 }}>
            <Tag icon={<Spin size="small" />} color="processing">
              {msg.content}
              {msg.data?.round && ` (${msg.data.round}/${msg.data.max_rounds || maxRounds}轮)`}
            </Tag>
          </div>
        );
      case 'thinking':
        return (
          <div key={index} style={{ marginBottom: 6 }}>
            <Collapse ghost size="small">
              <Panel
                header={
                  <span style={{ color: COLORS.textSecondary, fontSize: 13 }}>
                    <BulbOutlined style={{ marginRight: 6 }} />
                    Agent 思考
                  </span>
                }
                key="1"
              >
                <Paragraph style={{ margin: 0, color: COLORS.textSecondary, fontSize: 13 }}>
                  {msg.content}
                </Paragraph>
              </Panel>
            </Collapse>
          </div>
        );
      case 'sources':
        return (
          <div key={index} style={{ marginBottom: 6 }}>
            <Tag icon={<FileTextOutlined />} color="green">{msg.content}</Tag>
          </div>
        );
      case 'prompt':
        return (
          <div key={index} style={{ marginBottom: 6 }}>
            <Tag icon={<InfoCircleOutlined />} color="warning">{msg.content}</Tag>
          </div>
        );
      case 'error':
        return (
          <div key={index} style={{ marginBottom: 6 }}>
            <Tag icon={<CloseCircleOutlined />} color="error">{msg.content}</Tag>
          </div>
        );
      default:
        return null;
    }
  };

  // 渲染对话条目
  const renderConversation = (entry, index) => {
    if (entry.role === 'user') {
      return (
        <div key={index} style={{
          display: 'flex',
          justifyContent: 'flex-end',
          marginBottom: 16,
        }}>
          <div style={{
            maxWidth: '80%',
            background: COLORS.primary,
            color: '#fff',
            padding: '10px 16px',
            borderRadius: '16px 16px 4px 16px',
            fontSize: 14,
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
      <div key={index} style={{
        display: 'flex',
        justifyContent: 'flex-start',
        marginBottom: 16,
      }}>
        <div style={{ maxWidth: '85%' }}>
          {/* 过程消息 */}
          {entry.messages && entry.messages.length > 0 && (
            <Collapse ghost size="small" style={{ marginBottom: 8 }}>
              <Panel
                header={
                  <span style={{ color: COLORS.textSecondary, fontSize: 12 }}>
                    <SearchOutlined style={{ marginRight: 4 }} />
                    执行过程 ({entry.messages.length} 步)
                  </span>
                }
                key="1"
              >
                {entry.messages.map((msg, i) => renderProcessMessage(msg, i))}
              </Panel>
            </Collapse>
          )}

          {/* 检索来源 */}
          {entry.sources && entry.sources.length > 0 && (
            <Collapse ghost size="small" style={{ marginBottom: 8 }}>
              <Panel
                header={
                  <span style={{ color: COLORS.textSecondary, fontSize: 12 }}>
                    <FileTextOutlined style={{ marginRight: 4 }} />
                    检索来源 ({entry.sources.length})
                  </span>
                }
                key="1"
              >
                <List
                  size="small"
                  dataSource={entry.sources}
                  renderItem={(source) => (
                    <List.Item style={{ padding: '4px 0' }}>
                      <div style={{ width: '100%' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                          <Text strong style={{ fontSize: 12 }}>{source.filename}</Text>
                          <Tag color="blue" style={{ fontSize: 11 }}>
                            {(source.score * 100).toFixed(1)}%
                          </Tag>
                        </div>
                        <Paragraph
                          ellipsis={{ rows: 2, expandable: true }}
                          style={{ margin: 0, color: COLORS.textSecondary, fontSize: 12 }}
                        >
                          {source.content}
                        </Paragraph>
                      </div>
                    </List.Item>
                  )}
                />
              </Panel>
            </Collapse>
          )}

          {/* 错误消息 */}
          {entry.error && (
            <div style={{
              background: '#fff2f0',
              border: '1px solid #ffccc7',
              padding: '8px 12px',
              borderRadius: 8,
              color: COLORS.error,
              fontSize: 13,
            }}>
              {entry.error}
            </div>
          )}

          {/* 文本回复 */}
          {entry.content && (
            <div style={{
              background: COLORS.bgCard,
              border: `1px solid ${COLORS.borderLight}`,
              padding: '12px 16px',
              borderRadius: '16px 16px 16px 4px',
              fontSize: 14,
              lineHeight: 1.8,
              whiteSpace: 'pre-wrap',
            }}>
              {entry.content}
            </div>
          )}

          {/* Diff 输出 */}
          {entry.diff && (
            <div style={{ marginTop: 8 }}>
              <Tag icon={<DiffOutlined />} color="purple" style={{ marginBottom: 6 }}>
                文档修改 (Diff)
              </Tag>
              <pre style={{
                background: '#1e1e1e',
                color: '#d4d4d4',
                padding: 12,
                borderRadius: 8,
                fontSize: 12,
                lineHeight: 1.5,
                overflow: 'auto',
                maxHeight: 400,
                margin: 0,
              }}>
                {entry.diff}
              </pre>
            </div>
          )}

          {/* 统计信息 */}
          {entry.stats && (
            <div style={{ marginTop: 6 }}>
              <Space size={4}>
                {entry.stats.retrieval_rounds != null && (
                  <Tag style={{ fontSize: 11 }}>检索 {entry.stats.retrieval_rounds} 轮</Tag>
                )}
                {entry.stats.total_sources != null && (
                  <Tag style={{ fontSize: 11 }}>{entry.stats.total_sources} 条来源</Tag>
                )}
                {entry.stats.intent_type && (
                  <Tag style={{ fontSize: 11 }}>{entry.stats.intent_type}</Tag>
                )}
              </Space>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div style={{ padding: 24, height: '100%', overflow: 'auto', background: COLORS.bgBase }}>
      <div style={{ maxWidth: 900, margin: '0 auto', display: 'flex', flexDirection: 'column', height: 'calc(100% - 48px)' }}>
        {/* 顶部工具栏 */}
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Text strong style={{ fontSize: 20 }}>
              <RobotOutlined style={{ marginRight: 8 }} />
              AI Agent
            </Text>
            <Paragraph style={{ color: COLORS.textSecondary, marginTop: 4, marginBottom: 0, fontSize: 13 }}>
              统一智能助手 - 支持知识问答、文档操作、闲聊对话
            </Paragraph>
          </div>
          <Space>
            <Tooltip title={`会话 ID: ${sessionId}`}>
              <Tag style={{ cursor: 'default', fontSize: 11 }}>{sessionId.slice(0, 16)}...</Tag>
            </Tooltip>
            <Button
              size="small"
              icon={<PlusOutlined />}
              onClick={handleNewSession}
            >
              新会话
            </Button>
          </Space>
        </div>

        {/* 配置栏 */}
        <Card size="small" style={{ marginBottom: 12, flexShrink: 0 }}>
          <Space wrap size="middle">
            <Space size={4}>
              <Text style={{ fontSize: 13 }}>权限:</Text>
              <Tooltip title={permissionMode === 'assistant' ? '只读模式，可查询和建议' : '编辑模式，可修改文档'}>
                <Switch
                  checked={permissionMode === 'editor'}
                  onChange={(checked) => setPermissionMode(checked ? 'editor' : 'assistant')}
                  checkedChildren={<><EditOutlined /> 编辑</>}
                  unCheckedChildren={<><LockOutlined /> 助手</>}
                  style={{ minWidth: 80 }}
                />
              </Tooltip>
            </Space>
            <Divider type="vertical" />
            <Space size={4}>
              <Text style={{ fontSize: 13 }}>检索数:</Text>
              <InputNumber min={1} max={10} value={topK} onChange={setTopK} size="small" style={{ width: 60 }} />
            </Space>
            <Space size={4}>
              <Text style={{ fontSize: 13 }}>最大轮次:</Text>
              <InputNumber min={1} max={5} value={maxRounds} onChange={setMaxRounds} size="small" style={{ width: 60 }} />
            </Space>
            {documentName && (
              <>
                <Divider type="vertical" />
                <Tag icon={<FileTextOutlined />} closable onClose={() => { setDocumentContent(null); setDocumentName(null); }}>
                  {documentName}
                </Tag>
              </>
            )}
          </Space>
        </Card>

        {/* 对话区域 */}
        <div style={{
          flex: 1,
          overflow: 'auto',
          padding: '16px 0',
          minHeight: 0,
        }}>
          {conversations.length === 0 && !loading && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              color: COLORS.textTertiary,
            }}>
              <div style={{ textAlign: 'center' }}>
                <RobotOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                <div style={{ fontSize: 16 }}>开始对话</div>
                <div style={{ fontSize: 13, marginTop: 8 }}>
                  输入问题进行知识检索，或关联文档进行编辑操作
                </div>
              </div>
            </div>
          )}

          {/* 历史对话 */}
          {conversations.map((entry, index) => renderConversation(entry, index))}

          {/* 当前正在生成的回复 */}
          {loading && (
            <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: 16 }}>
              <div style={{ maxWidth: '85%' }}>
                {/* 实时过程消息 */}
                {currentMessages.length > 0 && (
                  <div style={{ marginBottom: 8 }}>
                    {currentMessages.map((msg, i) => renderProcessMessage(msg, i))}
                  </div>
                )}

                {/* 实时检索来源 */}
                {currentSources.length > 0 && (
                  <div style={{ marginBottom: 8 }}>
                    <Tag icon={<FileTextOutlined />} color="green">
                      找到 {currentSources.length} 条相关内容
                    </Tag>
                  </div>
                )}

                {/* 实时回答 */}
                {currentAnswer && (
                  <div style={{
                    background: COLORS.bgCard,
                    border: `1px solid ${COLORS.borderLight}`,
                    padding: '12px 16px',
                    borderRadius: '16px 16px 16px 4px',
                    fontSize: 14,
                    lineHeight: 1.8,
                    whiteSpace: 'pre-wrap',
                  }}>
                    {currentAnswer}
                    <span style={{
                      display: 'inline-block',
                      width: 6,
                      height: 16,
                      background: COLORS.primary,
                      marginLeft: 2,
                      animation: 'blink 1s step-end infinite',
                      verticalAlign: 'text-bottom',
                    }} />
                  </div>
                )}

                {/* 实时 Diff */}
                {currentDiff && (
                  <div style={{ marginTop: 8 }}>
                    <Tag icon={<DiffOutlined />} color="purple" style={{ marginBottom: 6 }}>
                      文档修改中...
                    </Tag>
                    <pre style={{
                      background: '#1e1e1e',
                      color: '#d4d4d4',
                      padding: 12,
                      borderRadius: 8,
                      fontSize: 12,
                      lineHeight: 1.5,
                      overflow: 'auto',
                      maxHeight: 400,
                      margin: 0,
                    }}>
                      {currentDiff}
                    </pre>
                  </div>
                )}

                {/* 无内容时显示加载状态 */}
                {!currentAnswer && !currentDiff && currentMessages.length === 0 && (
                  <div style={{
                    background: COLORS.bgCard,
                    border: `1px solid ${COLORS.borderLight}`,
                    padding: '12px 16px',
                    borderRadius: '16px 16px 16px 4px',
                  }}>
                    <Spin size="small" />
                    <Text style={{ marginLeft: 8, color: COLORS.textSecondary }}>思考中...</Text>
                  </div>
                )}
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* 输入区域 */}
        <Card size="small" style={{ flexShrink: 0 }}>
          <Space.Compact style={{ width: '100%' }}>
            <TextArea
              placeholder="输入你的问题..."
              value={userInput}
              onChange={(e) => setUserInput(e.target.value)}
              autoSize={{ minRows: 2, maxRows: 4 }}
              style={{ flex: 1 }}
              onPressEnter={(e) => {
                if (e.ctrlKey || e.metaKey) {
                  handleSend();
                }
              }}
            />
          </Space.Compact>
          <div style={{ marginTop: 10, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              Ctrl + Enter 发送
            </Text>
            <Space>
              {loading ? (
                <Button danger icon={<StopOutlined />} onClick={handleStop}>
                  停止
                </Button>
              ) : (
                <Button
                  type="primary"
                  icon={<SendOutlined />}
                  onClick={handleSend}
                  disabled={!userInput.trim()}
                >
                  发送
                </Button>
              )}
            </Space>
          </div>
        </Card>
      </div>

      <style>{`
        @keyframes blink {
          50% { opacity: 0; }
        }
      `}</style>
    </div>
  );
}

export default UnifiedAgentPage;
