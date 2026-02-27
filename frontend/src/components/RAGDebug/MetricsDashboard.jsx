/**
 * RAG 指标仪表盘组件
 * 展示系统运行指标和性能数据
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Progress,
  Typography,
  Space,
  Tag,
  Button,
  Spin,
  Alert,
  Tooltip,
  Divider,
} from 'antd';
import {
  ReloadOutlined,
  ClockCircleOutlined,
  ThunderboltOutlined,
  DatabaseOutlined,
  SearchOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  SyncOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;

// API 基础 URL
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

/**
 * 获取健康状态详情
 */
async function fetchHealthDetail() {
  const response = await fetch(`${API_BASE_URL}/api/health/detail`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

/**
 * 获取指标数据
 */
async function fetchMetrics() {
  const response = await fetch(`${API_BASE_URL}/api/health/metrics`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

/**
 * 格式化运行时间
 */
function formatUptime(seconds) {
  if (!seconds) return '0秒';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  
  if (hours > 0) {
    return `${hours}小时 ${minutes}分 ${secs}秒`;
  } else if (minutes > 0) {
    return `${minutes}分 ${secs}秒`;
  }
  return `${secs}秒`;
}

/**
 * 服务状态卡片
 */
const ServiceStatusCard = ({ service }) => {
  const statusConfig = {
    healthy: { color: 'success', icon: <CheckCircleOutlined />, text: '正常' },
    degraded: { color: 'warning', icon: <ExclamationCircleOutlined />, text: '降级' },
    unhealthy: { color: 'error', icon: <ExclamationCircleOutlined />, text: '异常' },
    not_configured: { color: 'default', icon: <ExclamationCircleOutlined />, text: '未配置' },
  };

  const nameMap = {
    config: '配置服务',
    rag: 'RAG 服务',
    ai: 'AI 服务',
  };

  const config = statusConfig[service.status] || statusConfig.not_configured;

  return (
    <Card size="small" style={{ height: '100%' }}>
      <Space direction="vertical" style={{ width: '100%' }}>
        <Space>
          <Text strong>{nameMap[service.name] || service.name}</Text>
          <Tag icon={config.icon} color={config.color}>
            {config.text}
          </Tag>
        </Space>
        {service.details && Object.keys(service.details).length > 0 && (
          <div style={{ fontSize: 12 }}>
            {Object.entries(service.details).map(([key, value]) => (
              <div key={key}>
                <Text type="secondary">{key}: </Text>
                <Text>{String(value)}</Text>
              </div>
            ))}
          </div>
        )}
      </Space>
    </Card>
  );
};

/**
 * 直方图指标卡片
 */
const HistogramCard = ({ name, data, icon, color }) => {
  if (!data) return null;

  const avgMs = (data.avg * 1000).toFixed(2);
  const minMs = (data.min * 1000).toFixed(2);
  const maxMs = (data.max * 1000).toFixed(2);

  return (
    <Card size="small">
      <Statistic
        title={
          <Space>
            {icon}
            <span>{name}</span>
          </Space>
        }
        value={data.count}
        suffix="次请求"
        valueStyle={{ color }}
      />
      <Divider style={{ margin: '8px 0' }} />
      <Row gutter={8}>
        <Col span={8}>
          <Text type="secondary" style={{ fontSize: 11 }}>平均</Text>
          <div style={{ fontWeight: 500 }}>{avgMs}ms</div>
        </Col>
        <Col span={8}>
          <Text type="secondary" style={{ fontSize: 11 }}>最小</Text>
          <div style={{ fontWeight: 500 }}>{minMs}ms</div>
        </Col>
        <Col span={8}>
          <Text type="secondary" style={{ fontSize: 11 }}>最大</Text>
          <div style={{ fontWeight: 500 }}>{maxMs}ms</div>
        </Col>
      </Row>
    </Card>
  );
};

/**
 * 计数器指标卡片
 */
const CounterCard = ({ name, data, icon, color }) => {
  if (!data) return null;

  return (
    <Card size="small">
      <Statistic
        title={
          <Space>
            {icon}
            <span>{name}</span>
          </Space>
        }
        value={data.value}
        valueStyle={{ color }}
      />
    </Card>
  );
};

/**
 * 指标仪表盘
 */
export function MetricsDashboard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [healthData, setHealthData] = useState(null);
  const [metricsData, setMetricsData] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(false);

  // 刷新数据
  const refreshData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [health, metrics] = await Promise.all([
        fetchHealthDetail(),
        fetchMetrics(),
      ]);
      setHealthData(health);
      setMetricsData(metrics);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // 初始加载
  useEffect(() => {
    refreshData();
  }, [refreshData]);

  // 自动刷新
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(refreshData, 5000);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshData]);

  // 解析指标
  const counters = metricsData?.counters || {};
  const histograms = metricsData?.histograms || {};

  // RAG 相关指标
  const ragRetrievalDuration = histograms['rag.retrieval.duration_seconds'];
  const ragRetrievalQueries = counters['rag.retrieval.queries'];

  // 从健康检查数据中获取 RAG 服务的索引统计（持久化数据）
  const ragService = healthData?.services?.find(s => s.name === 'rag');
  const ragIndexFiles = ragService?.details?.indexed_files || 0;
  const ragIndexChunks = ragService?.details?.indexed_chunks || 0;

  // LLM 相关指标
  const llmCalls = counters['llm.calls'];
  const llmTokensUsed = counters['llm.tokens_used'];

  // 状态映射
  const statusMap = {
    healthy: '正常',
    degraded: '降级',
    unhealthy: '异常',
  };

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={3} style={{ margin: 0 }}>RAG 指标仪表盘</Title>
        <Space>
          <Button
            icon={autoRefresh ? <SyncOutlined spin /> : <SyncOutlined />}
            onClick={() => setAutoRefresh(!autoRefresh)}
            type={autoRefresh ? 'primary' : 'default'}
          >
            {autoRefresh ? '自动刷新中' : '自动刷新'}
          </Button>
          <Button icon={<ReloadOutlined />} onClick={refreshData} loading={loading}>
            刷新
          </Button>
        </Space>
      </div>

      {error && (
        <Alert
          message="加载指标失败"
          description={error}
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {loading && !healthData ? (
        <div style={{ textAlign: 'center', padding: 60 }}>
          <Spin size="large" tip="加载指标中..." />
        </div>
      ) : (
        <>
          {/* 系统概览 */}
          <Card title="系统概览" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col span={6}>
                <Statistic
                  title="系统状态"
                  value={statusMap[healthData?.status] || healthData?.status?.toUpperCase()}
                  valueStyle={{
                    color: healthData?.status === 'healthy' ? '#52c41a' : 
                           healthData?.status === 'degraded' ? '#faad14' : '#f5222d'
                  }}
                  prefix={
                    healthData?.status === 'healthy' ? <CheckCircleOutlined /> : 
                    <ExclamationCircleOutlined />
                  }
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="运行时间"
                  value={formatUptime(healthData?.uptime_seconds)}
                  prefix={<ClockCircleOutlined />}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="Python 版本"
                  value={healthData?.python_version || '-'}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="运行平台"
                  value={healthData?.platform?.split('-')[0] || '-'}
                />
              </Col>
            </Row>
          </Card>

          {/* 服务状态 */}
          <Card title="服务状态" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              {healthData?.services?.map((service) => (
                <Col span={8} key={service.name}>
                  <ServiceStatusCard service={service} />
                </Col>
              ))}
            </Row>
          </Card>

          {/* RAG 性能指标 */}
          <Card 
            title={
              <Space>
                <SearchOutlined />
                <span>RAG 性能指标</span>
              </Space>
            }
            style={{ marginBottom: 16 }}
          >
            <Row gutter={16}>
              <Col span={8}>
                <HistogramCard
                  name="检索耗时"
                  data={ragRetrievalDuration}
                  icon={<ThunderboltOutlined />}
                  color="#722ed1"
                />
              </Col>
              <Col span={8}>
                <CounterCard
                  name="查询总次数"
                  data={ragRetrievalQueries}
                  icon={<SearchOutlined />}
                  color="#1890ff"
                />
              </Col>
              <Col span={8}>
                <Card size="small">
                  <Statistic
                    title={
                      <Space>
                        <DatabaseOutlined />
                        <span>索引统计</span>
                      </Space>
                    }
                    value={ragIndexFiles}
                    suffix="个文件"
                    valueStyle={{ color: '#52c41a' }}
                  />
                  <Divider style={{ margin: '8px 0' }} />
                  <Text type="secondary">
                    已索引 {ragIndexChunks} 个文档块
                  </Text>
                </Card>
              </Col>
            </Row>
          </Card>

          {/* LLM 调用统计 */}
          <Card 
            title={
              <Space>
                <ThunderboltOutlined />
                <span>LLM 调用统计</span>
              </Space>
            }
          >
            <Row gutter={16}>
              <Col span={8}>
                <CounterCard
                  name="LLM 调用次数"
                  data={llmCalls}
                  icon={<ThunderboltOutlined />}
                  color="#fa8c16"
                />
              </Col>
              <Col span={8}>
                <CounterCard
                  name="Token 消耗量"
                  data={llmTokensUsed}
                  icon={<DatabaseOutlined />}
                  color="#13c2c2"
                />
              </Col>
              <Col span={8}>
                <Card size="small">
                  <Text type="secondary">
                    更多指标将在系统运行时自动收集。
                    服务重启后指标会重置。
                  </Text>
                </Card>
              </Col>
            </Row>
          </Card>

          {/* 原始指标数据 */}
          {(Object.keys(counters).length > 0 || Object.keys(histograms).length > 0) && (
            <Card 
              title="原始指标数据" 
              style={{ marginTop: 16 }}
              size="small"
            >
              <Row gutter={16}>
                <Col span={12}>
                  <Title level={5}>计数器</Title>
                  {Object.keys(counters).length > 0 ? (
                    <pre style={{ 
                      background: '#f5f5f5', 
                      padding: 12, 
                      borderRadius: 4,
                      fontSize: 12,
                      overflow: 'auto',
                      maxHeight: 200,
                    }}>
                      {JSON.stringify(counters, null, 2)}
                    </pre>
                  ) : (
                    <Text type="secondary">暂无计数器指标</Text>
                  )}
                </Col>
                <Col span={12}>
                  <Title level={5}>直方图</Title>
                  {Object.keys(histograms).length > 0 ? (
                    <pre style={{ 
                      background: '#f5f5f5', 
                      padding: 12, 
                      borderRadius: 4,
                      fontSize: 12,
                      overflow: 'auto',
                      maxHeight: 200,
                    }}>
                      {JSON.stringify(histograms, null, 2)}
                    </pre>
                  ) : (
                    <Text type="secondary">暂无直方图指标</Text>
                  )}
                </Col>
              </Row>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

export default MetricsDashboard;
