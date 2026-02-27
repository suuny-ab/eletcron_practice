/**
 * RAG 调试面板组件
 * 可视化展示 RAG 检索流程的各个阶段
 */
import React, { useState, useCallback } from 'react';
import {
  Card,
  Input,
  Button,
  Collapse,
  Table,
  Tag,
  Space,
  Statistic,
  Row,
  Col,
  Typography,
  Tooltip,
  Empty,
  Spin,
  InputNumber,
  message,
} from 'antd';
import {
  SearchOutlined,
  ThunderboltOutlined,
  MergeCellsOutlined,
  OrderedListOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { ragDebug } from '../../api/ai';

const { TextArea } = Input;
const { Panel } = Collapse;
const { Text, Title } = Typography;

/**
 * 分词展示组件
 */
const TokensDisplay = ({ tokens }) => {
  if (!tokens || tokens.length === 0) return <Text type="secondary">-</Text>;
  
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
      {tokens.slice(0, 20).map((token, idx) => (
        <Tag key={idx} color="blue" style={{ margin: 0 }}>
          {token}
        </Tag>
      ))}
      {tokens.length > 20 && (
        <Tag color="default">+{tokens.length - 20} 更多</Tag>
      )}
    </div>
  );
};

/**
 * 得分条组件
 */
const ScoreBar = ({ score, color = '#1890ff' }) => {
  const percentage = Math.min(Math.max(score * 100, 0), 100);
  return (
    <Tooltip title={`原始值: ${score.toFixed(4)}`}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <div style={{ flex: 1, height: 6, background: '#f0f0f0', borderRadius: 3, overflow: 'hidden', minWidth: 40 }}>
          <div
            style={{
              width: `${percentage}%`,
              height: '100%',
              background: color,
              borderRadius: 3,
            }}
          />
        </div>
        <Text style={{ fontSize: 11, color: '#666', whiteSpace: 'nowrap' }}>{score.toFixed(2)}</Text>
      </div>
    </Tooltip>
  );
};

/**
 * 来源标签组件
 */
const SourceTag = ({ source }) => {
  const config = {
    vector: { color: 'purple', text: '向量' },
    bm25: { color: 'orange', text: 'BM25' },
    both: { color: 'green', text: '双重命中' },
  };
  const { color, text } = config[source] || { color: 'default', text: source };
  return <Tag color={color}>{text}</Tag>;
};

/**
 * RAG 调试面板
 */
export function RAGDebugPanel() {
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(3);
  const [loading, setLoading] = useState(false);
  const [debugInfo, setDebugInfo] = useState(null);

  // 执行调试查询
  const handleDebugQuery = useCallback(async () => {
    if (!query.trim()) {
      message.warning('请输入查询内容');
      return;
    }

    setLoading(true);
    try {
      const info = await ragDebug(query, topK);
      setDebugInfo(info);
    } catch (error) {
      message.error('调试查询失败: ' + error.message);
    } finally {
      setLoading(false);
    }
  }, [query, topK]);

  // 向量检索结果表格列
  const vectorColumns = [
    {
      title: '#',
      dataIndex: 'index',
      key: 'index',
      width: 40,
      render: (_, __, idx) => idx + 1,
    },
    {
      title: '文件名',
      dataIndex: 'filename',
      key: 'filename',
      width: 180,
      ellipsis: true,
      render: (text) => (
        <Tooltip title={text}>
          <Text code>{text}</Text>
        </Tooltip>
      ),
    },
    {
      title: '原始距离',
      dataIndex: 'raw_distance',
      key: 'raw_distance',
      width: 90,
      render: (val) => <Text type="secondary">{val?.toFixed(4)}</Text>,
    },
    {
      title: '相似度',
      dataIndex: 'similarity_score',
      key: 'similarity_score',
      width: 110,
      render: (val) => <ScoreBar score={val || 0} color="#722ed1" />,
    },
    {
      title: '归一化得分',
      dataIndex: 'normalized_score',
      key: 'normalized_score',
      width: 110,
      render: (val) => <ScoreBar score={val || 0} color="#1890ff" />,
    },
    {
      title: '内容预览',
      dataIndex: 'content',
      key: 'content',
      ellipsis: true,
      render: (text) => (
        <Tooltip title={text}>
          <Text>{text?.slice(0, 80)}...</Text>
        </Tooltip>
      ),
    },
  ];

  // BM25 检索结果表格列
  const bm25Columns = [
    {
      title: '#',
      dataIndex: 'index',
      key: 'index',
      width: 40,
      render: (_, __, idx) => idx + 1,
    },
    {
      title: '文件名',
      dataIndex: 'filename',
      key: 'filename',
      width: 180,
      ellipsis: true,
      render: (text) => (
        <Tooltip title={text}>
          <Text code>{text}</Text>
        </Tooltip>
      ),
    },
    {
      title: '原始得分',
      dataIndex: 'raw_score',
      key: 'raw_score',
      width: 90,
      render: (val) => <Text type="secondary">{val?.toFixed(4)}</Text>,
    },
    {
      title: '归一化得分',
      dataIndex: 'normalized_score',
      key: 'normalized_score',
      width: 110,
      render: (val) => <ScoreBar score={val || 0} color="#fa8c16" />,
    },
    {
      title: '分词结果',
      dataIndex: 'tokens',
      key: 'tokens',
      width: 180,
      render: (tokens) => <TokensDisplay tokens={tokens} />,
    },
    {
      title: '内容预览',
      dataIndex: 'content',
      key: 'content',
      ellipsis: true,
      render: (text) => (
        <Tooltip title={text}>
          <Text>{text?.slice(0, 60)}...</Text>
        </Tooltip>
      ),
    },
  ];

  // 混合候选表格列
  const hybridColumns = [
    {
      title: '#',
      dataIndex: 'index',
      key: 'index',
      width: 40,
      render: (_, __, idx) => idx + 1,
    },
    {
      title: '文件名',
      dataIndex: 'filename',
      key: 'filename',
      width: 160,
      ellipsis: true,
      render: (text) => <Text code>{text}</Text>,
    },
    {
      title: '来源',
      dataIndex: 'source',
      key: 'source',
      width: 80,
      render: (source) => <SourceTag source={source} />,
    },
    {
      title: '向量得分',
      dataIndex: 'vector_score',
      key: 'vector_score',
      width: 100,
      render: (val) => <ScoreBar score={val || 0} color="#722ed1" />,
    },
    {
      title: 'BM25 得分',
      dataIndex: 'bm25_score',
      key: 'bm25_score',
      width: 100,
      render: (val) => <ScoreBar score={val || 0} color="#fa8c16" />,
    },
    {
      title: '混合得分',
      dataIndex: 'hybrid_score',
      key: 'hybrid_score',
      width: 100,
      render: (val) => <ScoreBar score={val || 0} color="#52c41a" />,
    },
    {
      title: '内容预览',
      dataIndex: 'content',
      key: 'content',
      ellipsis: true,
      render: (text) => <Text>{text?.slice(0, 50)}...</Text>,
    },
  ];

  // 重排序结果表格列
  const rerankColumns = [
    {
      title: '原始排名',
      dataIndex: 'original_rank',
      key: 'original_rank',
      width: 90,
      render: (val) => <Tag color="blue">#{val + 1}</Tag>,
    },
    {
      title: '最终排名',
      dataIndex: 'final_rank',
      key: 'final_rank',
      width: 90,
      render: (val, record) =>
        record.selected ? (
          <Tag color="green">#{val + 1}</Tag>
        ) : (
          <Tag color="default">-</Tag>
        ),
    },
    {
      title: '状态',
      dataIndex: 'selected',
      key: 'selected',
      width: 80,
      render: (selected) =>
        selected ? (
          <Tag icon={<CheckCircleOutlined />} color="success">
            已选中
          </Tag>
        ) : (
          <Tag color="default">已过滤</Tag>
        ),
    },
    {
      title: '文件名',
      dataIndex: 'filename',
      key: 'filename',
      width: 180,
      ellipsis: true,
      render: (text) => <Text code>{text}</Text>,
    },
    {
      title: '混合得分',
      dataIndex: 'hybrid_score',
      key: 'hybrid_score',
      width: 100,
      render: (val) => <ScoreBar score={val || 0} color="#52c41a" />,
    },
    {
      title: '内容预览',
      dataIndex: 'content',
      key: 'content',
      ellipsis: true,
      render: (text) => <Text>{text?.slice(0, 60)}...</Text>,
    },
  ];

  return (
    <div style={{ padding: '24px', maxWidth: 1400, margin: '0 auto' }}>
      <div style={{ marginBottom: 24 }}>
        <Title level={3} style={{ marginBottom: 8 }}>RAG 调试面板</Title>
        <Text type="secondary">
          可视化展示 RAG 检索流程：向量检索、BM25 检索、混合评分、LLM 重排序
        </Text>
      </div>

      {/* 查询输入区 */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <TextArea
              placeholder="输入查询内容以调试 RAG 检索流程..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              rows={2}
              onPressEnter={(e) => {
                if (e.ctrlKey) handleDebugQuery();
              }}
            />
          </Col>
          <Col>
            <Space direction="vertical">
              <InputNumber
                addonBefore="Top-K"
                min={1}
                max={10}
                value={topK}
                onChange={setTopK}
                style={{ width: 120 }}
              />
              <Button
                type="primary"
                icon={<SearchOutlined />}
                onClick={handleDebugQuery}
                loading={loading}
                block
              >
                调试查询
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 加载状态 */}
      {loading && (
        <div style={{ textAlign: 'center', padding: '60px' }}>
          <Spin size="large" tip="正在分析检索流程..." />
        </div>
      )}

      {/* 调试结果 */}
      {debugInfo && !loading && (
        <>
          {/* 查询信息和检索配置 */}
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={16}>
              <Card size="small" style={{ height: '100%' }}>
                <div style={{ marginBottom: 12 }}>
                  <Text strong style={{ display: 'block', marginBottom: 4 }}>查询内容</Text>
                  <Text>{debugInfo.query}</Text>
                </div>
                <div>
                  <Text strong style={{ display: 'block', marginBottom: 4 }}>查询分词</Text>
                  <TokensDisplay tokens={debugInfo.query_tokens} />
                </div>
              </Card>
            </Col>
            <Col span={8}>
              <Card title="检索配置" size="small" style={{ height: '100%' }}>
                <Row gutter={[12, 12]}>
                  <Col span={12}>
                    <Statistic
                      title="向量 Top-K"
                      value={debugInfo.config?.vector_top_k}
                      valueStyle={{ fontSize: 18 }}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="BM25 Top-K"
                      value={debugInfo.config?.bm25_top_k}
                      valueStyle={{ fontSize: 18 }}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="向量权重"
                      value={debugInfo.config?.vector_weight}
                      precision={2}
                      valueStyle={{ fontSize: 18 }}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="BM25 权重"
                      value={debugInfo.config?.bm25_weight}
                      precision={2}
                      valueStyle={{ fontSize: 18 }}
                    />
                  </Col>
                </Row>
              </Card>
            </Col>
          </Row>

          {/* 耗时统计 */}
          <Card
            title={
              <Space>
                <ClockCircleOutlined />
                <span>各阶段耗时</span>
              </Space>
            }
            size="small"
            style={{ marginBottom: 16 }}
          >
            <Row gutter={16}>
              <Col span={4}>
                <Statistic
                  title="向量检索"
                  value={debugInfo.timing?.vector_search_ms}
                  suffix="ms"
                  valueStyle={{ color: '#722ed1', fontSize: 18 }}
                />
              </Col>
              <Col span={4}>
                <Statistic
                  title="BM25 检索"
                  value={debugInfo.timing?.bm25_search_ms}
                  suffix="ms"
                  valueStyle={{ color: '#fa8c16', fontSize: 18 }}
                />
              </Col>
              <Col span={4}>
                <Statistic
                  title="混合评分"
                  value={debugInfo.timing?.merge_ms}
                  suffix="ms"
                  valueStyle={{ color: '#1890ff', fontSize: 18 }}
                />
              </Col>
              <Col span={4}>
                <Statistic
                  title="LLM 重排序"
                  value={debugInfo.timing?.rerank_ms}
                  suffix="ms"
                  valueStyle={{ color: '#52c41a', fontSize: 18 }}
                />
              </Col>
              <Col span={4}>
                <Statistic
                  title="总耗时"
                  value={debugInfo.timing?.total_ms}
                  suffix="ms"
                  valueStyle={{ color: '#f5222d', fontWeight: 'bold', fontSize: 18 }}
                />
              </Col>
              <Col span={4}>
                <Statistic
                  title="结果数量"
                  value={debugInfo.final_sources?.length || 0}
                  suffix="条"
                  valueStyle={{ fontSize: 18 }}
                />
              </Col>
            </Row>
          </Card>

          {/* 检索步骤详情 */}
          <Collapse
            defaultActiveKey={['vector', 'bm25', 'hybrid', 'rerank']}
            style={{ marginBottom: 16 }}
          >
            {/* 向量检索 */}
            <Panel
              header={
                <Space>
                  <ThunderboltOutlined style={{ color: '#722ed1' }} />
                  <span>步骤 1：向量检索</span>
                  <Tag color="purple">{debugInfo.vector_search?.length || 0} 条结果</Tag>
                </Space>
              }
              key="vector"
            >
              {debugInfo.vector_search?.length > 0 ? (
                <Table
                  columns={vectorColumns}
                  dataSource={debugInfo.vector_search}
                  rowKey={(_, idx) => idx}
                  size="small"
                  pagination={false}
                  scroll={{ x: 900 }}
                />
              ) : (
                <Empty description="无向量检索结果" />
              )}
            </Panel>

            {/* BM25 检索 */}
            <Panel
              header={
                <Space>
                  <FileTextOutlined style={{ color: '#fa8c16' }} />
                  <span>步骤 2：BM25 检索</span>
                  <Tag color="orange">{debugInfo.bm25_search?.length || 0} 条结果</Tag>
                </Space>
              }
              key="bm25"
            >
              {debugInfo.bm25_search?.length > 0 ? (
                <Table
                  columns={bm25Columns}
                  dataSource={debugInfo.bm25_search}
                  rowKey={(_, idx) => idx}
                  size="small"
                  pagination={false}
                  scroll={{ x: 1000 }}
                />
              ) : (
                <Empty description="无 BM25 检索结果" />
              )}
            </Panel>

            {/* 混合候选 */}
            <Panel
              header={
                <Space>
                  <MergeCellsOutlined style={{ color: '#1890ff' }} />
                  <span>步骤 3：混合评分</span>
                  <Tag color="blue">{debugInfo.hybrid_candidates?.length || 0} 个候选</Tag>
                </Space>
              }
              key="hybrid"
            >
              {debugInfo.hybrid_candidates?.length > 0 ? (
                <Table
                  columns={hybridColumns}
                  dataSource={debugInfo.hybrid_candidates}
                  rowKey={(_, idx) => idx}
                  size="small"
                  pagination={false}
                  scroll={{ x: 1000 }}
                />
              ) : (
                <Empty description="无混合候选" />
              )}
            </Panel>

            {/* LLM 重排序 */}
            <Panel
              header={
                <Space>
                  <OrderedListOutlined style={{ color: '#52c41a' }} />
                  <span>步骤 4：LLM 重排序</span>
                  <Tag color="green">
                    已选中 {debugInfo.rerank_results?.filter((r) => r.selected).length || 0} 条
                  </Tag>
                </Space>
              }
              key="rerank"
            >
              {debugInfo.rerank_results?.length > 0 ? (
                <Table
                  columns={rerankColumns}
                  dataSource={debugInfo.rerank_results}
                  rowKey={(_, idx) => idx}
                  size="small"
                  pagination={false}
                  scroll={{ x: 900 }}
                  rowClassName={(record) => (record.selected ? 'selected-row' : '')}
                />
              ) : (
                <Empty description="无重排序结果" />
              )}
            </Panel>
          </Collapse>

          {/* 最终结果 */}
          <Card
            title={
              <Space>
                <CheckCircleOutlined style={{ color: '#52c41a' }} />
                <span>最终检索结果</span>
                <Tag color="success">{debugInfo.final_sources?.length || 0} 篇文档</Tag>
              </Space>
            }
          >
            {debugInfo.final_sources?.length > 0 ? (
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                {debugInfo.final_sources.map((source, idx) => (
                  <Card
                    key={idx}
                    type="inner"
                    title={
                      <Space>
                        <Tag color="blue">#{idx + 1}</Tag>
                        <Text code style={{ fontSize: 13 }}>{source.filename}</Text>
                        <Text type="secondary">得分: {source.score?.toFixed(4)}</Text>
                      </Space>
                    }
                    size="small"
                    style={{ background: '#fafafa' }}
                  >
                    <Text style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{source.content}</Text>
                  </Card>
                ))}
              </Space>
            ) : (
              <Empty description="未检索到相关文档" />
            )}
          </Card>
        </>
      )}

      {/* 空状态 */}
      {!debugInfo && !loading && (
        <div style={{ textAlign: 'center', padding: '80px 20px' }}>
          <Empty
            description="输入查询内容并点击「调试查询」以分析 RAG 检索流程"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        </div>
      )}

      <style>{`
        .selected-row {
          background-color: #f6ffed !important;
        }
        .ant-card-head-title {
          padding: 12px 0;
        }
        .ant-statistic-title {
          font-size: 12px;
        }
      `}</style>
    </div>
  );
}

export default RAGDebugPanel;
