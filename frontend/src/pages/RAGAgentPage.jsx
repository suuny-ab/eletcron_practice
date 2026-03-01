import { useState, useRef, useCallback, useEffect } from 'react';
import { Card, Input, Button, Space, InputNumber, Typography, Tag, Collapse, Spin, List } from 'antd';
import { SendOutlined, StopOutlined, RobotOutlined, SearchOutlined, BulbOutlined, FileTextOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { ragAgentStream, readEventStream } from '../api/ai';
import { COLORS } from '../styles/tokens';

const { TextArea } = Input;
const { Text, Paragraph } = Typography;
const { Panel } = Collapse;

function RAGAgentPage() {
  const [question, setQuestion] = useState('');
  const [maxRounds, setMaxRounds] = useState(3);
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState([]);
  const [answer, setAnswer] = useState('');
  const [sources, setSources] = useState([]);
  const [stats, setStats] = useState(null);
  const abortControllerRef = useRef(null);
  const messagesEndRef = useRef(null);

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, answer]);

  // 发送查询
  const handleSend = useCallback(async () => {
    if (!question.trim() || loading) return;

    setLoading(true);
    setMessages([]);
    setAnswer('');
    setSources([]);
    setStats(null);
    abortControllerRef.current = new AbortController();

    try {
      const stream = await ragAgentStream(
        { question: question.trim(), max_rounds: maxRounds },
        { signal: abortControllerRef.current.signal }
      );

      for await (const event of readEventStream(stream, abortControllerRef.current.signal)) {
        console.log('[RAGAgentPage] Event:', event);

        switch (event.type) {
          case 'status':
            setMessages(prev => [...prev, {
              type: 'status',
              content: event.content,
              data: event.data,
              timestamp: Date.now()
            }]);
            break;

          case 'thinking':
            setMessages(prev => [...prev, {
              type: 'thinking',
              content: event.content,
              timestamp: Date.now()
            }]);
            break;

          case 'sources':
            setSources(event.data || []);
            setMessages(prev => [...prev, {
              type: 'sources',
              content: `找到 ${event.data?.length || 0} 条相关内容`,
              data: event.data,
              timestamp: Date.now()
            }]);
            break;

          case 'chunk':
            setAnswer(prev => prev + (event.content || ''));
            break;

          case 'error':
            setMessages(prev => [...prev, {
              type: 'error',
              content: event.content,
              timestamp: Date.now()
            }]);
            break;

          case 'complete':
            setStats(event.data);
            setMessages(prev => [...prev, {
              type: 'complete',
              content: '完成',
              data: event.data,
              timestamp: Date.now()
            }]);
            break;
        }
      }
    } catch (error) {
      if (error.name !== 'AbortError') {
        setMessages(prev => [...prev, {
          type: 'error',
          content: `请求失败: ${error.message}`,
          timestamp: Date.now()
        }]);
      }
    } finally {
      setLoading(false);
      abortControllerRef.current = null;
    }
  }, [question, maxRounds, loading]);

  // 停止查询
  const handleStop = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setLoading(false);
  }, []);

  // 渲染消息
  const renderMessage = (msg, index) => {
    const { type, content, data, timestamp } = msg;

    switch (type) {
      case 'status':
        return (
          <div key={index} style={{ marginBottom: 8 }}>
            <Tag icon={<Spin size="small" />} color="processing">
              {content}
              {data?.round && ` (${data.round}/${data.max_rounds || maxRounds}轮)`}
            </Tag>
          </div>
        );

      case 'thinking':
        return (
          <div key={index} style={{ marginBottom: 8 }}>
            <Collapse ghost size="small">
              <Panel
                header={
                  <span style={{ color: COLORS.textSecondary }}>
                    <BulbOutlined style={{ marginRight: 8 }} />
                    Agent 思考
                  </span>
                }
                key="1"
              >
                <Paragraph style={{ margin: 0, color: COLORS.textSecondary, fontSize: 13 }}>
                  {content}
                </Paragraph>
              </Panel>
            </Collapse>
          </div>
        );

      case 'sources':
        return (
          <div key={index} style={{ marginBottom: 8 }}>
            <Tag icon={<FileTextOutlined />} color="green">
              {content}
            </Tag>
          </div>
        );

      case 'error':
        return (
          <div key={index} style={{ marginBottom: 8 }}>
            <Tag icon={<CloseCircleOutlined />} color="error">
              {content}
            </Tag>
          </div>
        );

      case 'complete':
        return (
          <div key={index} style={{ marginBottom: 8 }}>
            <Tag icon={<CheckCircleOutlined />} color="success">
              完成 - 检索 {data?.retrieval_rounds || 0} 轮，共 {data?.total_sources || 0} 条来源
            </Tag>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div style={{ padding: 24, height: '100%', overflow: 'auto', background: COLORS.bgBase }}>
      <div style={{ maxWidth: 1200, margin: '0 auto' }}>
        {/* 标题 */}
        <div style={{ marginBottom: 24 }}>
          <Text strong style={{ fontSize: 20 }}>
            <RobotOutlined style={{ marginRight: 8 }} />
            RAG Agent 测试
          </Text>
          <Paragraph style={{ color: COLORS.textSecondary, marginTop: 8, marginBottom: 0 }}>
            基于 LangGraph 的智能 RAG 流程，支持多轮检索、结果评估、查询重构
          </Paragraph>
        </div>

        {/* 配置区域 */}
        <Card size="small" style={{ marginBottom: 16 }}>
          <Space wrap>
            <span>最大检索轮次:</span>
            <InputNumber
              min={1}
              max={5}
              value={maxRounds}
              onChange={setMaxRounds}
              style={{ width: 80 }}
            />
          </Space>
        </Card>

        {/* 输入区域 */}
        <Card size="small" style={{ marginBottom: 16 }}>
          <Space.Compact style={{ width: '100%' }}>
            <TextArea
              placeholder="输入你的问题..."
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              autoSize={{ minRows: 2, maxRows: 4 }}
              style={{ flex: 1 }}
              onPressEnter={(e) => {
                if (e.ctrlKey || e.metaKey) {
                  handleSend();
                }
              }}
            />
          </Space.Compact>
          <div style={{ marginTop: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              Ctrl + Enter 发送
            </Text>
            <Space>
              {loading ? (
                <Button
                  danger
                  icon={<StopOutlined />}
                  onClick={handleStop}
                >
                  停止
                </Button>
              ) : (
                <Button
                  type="primary"
                  icon={<SendOutlined />}
                  onClick={handleSend}
                  disabled={!question.trim()}
                >
                  发送
                </Button>
              )}
            </Space>
          </div>
        </Card>

        {/* 执行过程 */}
        {messages.length > 0 && (
          <Card
            title={
              <span>
                <SearchOutlined style={{ marginRight: 8 }} />
                执行过程
              </span>
            }
            size="small"
            style={{ marginBottom: 16 }}
          >
            <div style={{ maxHeight: 300, overflow: 'auto' }}>
              {messages.map((msg, index) => renderMessage(msg, index))}
              <div ref={messagesEndRef} />
            </div>
          </Card>
        )}

        {/* 检索来源 */}
        {sources.length > 0 && (
          <Card
            title={
              <span>
                <FileTextOutlined style={{ marginRight: 8 }} />
                检索来源 ({sources.length})
              </span>
            }
            size="small"
            style={{ marginBottom: 16 }}
          >
            <List
              size="small"
              dataSource={sources}
              renderItem={(source, index) => (
                <List.Item>
                  <div style={{ width: '100%' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <Text strong>{source.filename}</Text>
                      <Tag color="blue">相关度: {(source.score * 100).toFixed(1)}%</Tag>
                    </div>
                    <Paragraph
                      ellipsis={{ rows: 2, expandable: true }}
                      style={{ margin: 0, color: COLORS.textSecondary, fontSize: 13 }}
                    >
                      {source.content}
                    </Paragraph>
                  </div>
                </List.Item>
              )}
            />
          </Card>
        )}

        {/* 回答 */}
        {(answer || loading) && (
          <Card
            title={
              <span>
                <RobotOutlined style={{ marginRight: 8 }} />
                回答
                {loading && <Spin size="small" style={{ marginLeft: 8 }} />}
              </span>
            }
            size="small"
          >
            <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.8 }}>
              {answer || (loading ? '等待生成...' : '')}
            </div>
          </Card>
        )}

        {/* 统计信息 */}
        {stats && (
          <Card size="small" style={{ marginTop: 16 }}>
            <Space>
              <Tag>检索轮次: {stats.retrieval_rounds}</Tag>
              <Tag>总来源数: {stats.total_sources}</Tag>
            </Space>
          </Card>
        )}
      </div>
    </div>
  );
}

export default RAGAgentPage;
