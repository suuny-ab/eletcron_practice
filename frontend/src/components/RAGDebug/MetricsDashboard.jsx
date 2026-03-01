/**
 * 指标仪表盘组件（增强版）
 * 系统概览 + 时序趋势图 + 分组指标卡片
 */
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Typography,
  Space,
  Tag,
  Button,
  Spin,
  Alert,
  Divider,
  Segmented,
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
  ApiOutlined,
  RobotOutlined,
  MessageOutlined,
} from '@ant-design/icons';
import { TimeSeriesChart } from '../Metrics/TimeSeriesChart';
import { fetchHealthDetail, fetchMetrics, fetchTimeseries } from '../../api/metrics';
import { COLORS } from '../../styles/tokens';

const { Title, Text } = Typography;

// ---------- 工具函数 ----------

function formatUptime(seconds) {
  if (!seconds) return '0秒';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}小时 ${m}分 ${s}秒`;
  if (m > 0) return `${m}分 ${s}秒`;
  return `${s}秒`;
}

// ---------- 子组件 ----------

const ServiceStatusCard = ({ service }) => {
  const cfg = {
    healthy: { color: 'success', icon: <CheckCircleOutlined />, text: '正常' },
    degraded: { color: 'warning', icon: <ExclamationCircleOutlined />, text: '降级' },
    unhealthy: { color: 'error', icon: <ExclamationCircleOutlined />, text: '异常' },
    not_configured: { color: 'default', icon: <ExclamationCircleOutlined />, text: '未配置' },
  };
  const nameMap = { config: '配置服务', rag: 'RAG 服务', ai: 'AI 服务' };
  const c = cfg[service.status] || cfg.not_configured;

  return (
    <Card size="small" style={{ height: '100%' }}>
      <Space direction="vertical" style={{ width: '100%' }}>
        <Space>
          <Text strong>{nameMap[service.name] || service.name}</Text>
          <Tag icon={c.icon} color={c.color}>{c.text}</Tag>
        </Space>
        {service.details && Object.keys(service.details).length > 0 && (
          <div style={{ fontSize: 12 }}>
            {Object.entries(service.details).map(([k, v]) => (
              <div key={k}>
                <Text type="secondary">{k}: </Text>
                <Text>{String(v)}</Text>
              </div>
            ))}
          </div>
        )}
      </Space>
    </Card>
  );
};

const HistogramCard = ({ name, data, icon, color }) => {
  if (!data) return null;
  const avgMs = (data.avg * 1000).toFixed(2);
  const minMs = (data.min * 1000).toFixed(2);
  const maxMs = (data.max * 1000).toFixed(2);

  return (
    <Card size="small">
      <Statistic
        title={<Space>{icon}<span>{name}</span></Space>}
        value={data.count}
        suffix="次"
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

const CounterCard = ({ name, data, icon, color }) => {
  if (!data) return null;
  return (
    <Card size="small">
      <Statistic
        title={<Space>{icon}<span>{name}</span></Space>}
        value={data.value}
        valueStyle={{ color }}
      />
    </Card>
  );
};

// ---------- 时序图表系列定义 ----------

const HTTP_SERIES = [
  {
    key: 'http_req',
    label: 'HTTP 请求数',
    extract: (dp) => dp.counters?.['http.requests.count'] ?? 0,
    color: '#1890ff',
  },
  {
    key: 'http_err',
    label: 'HTTP 5xx',
    extract: (dp) => dp.counters?.['http.errors.count'] ?? 0,
    color: '#f5222d',
  },
];

const LLM_DURATION_SERIES = [
  {
    key: 'llm_avg',
    label: 'LLM 平均耗时',
    extract: (dp) => {
      const h = dp.histograms?.['llm.call.duration_seconds'];
      return h ? +(h.avg * 1000).toFixed(1) : 0;
    },
    color: '#fa8c16',
  },
];

const RAG_SERIES = [
  {
    key: 'rag_avg',
    label: 'RAG 检索平均耗时',
    extract: (dp) => {
      const h = dp.histograms?.['rag.retrieval.duration_seconds'];
      return h ? +(h.avg * 1000).toFixed(1) : 0;
    },
    color: '#722ed1',
  },
];

const AGENT_SERIES = [
  {
    key: 'wf_avg',
    label: '工作流平均耗时',
    extract: (dp) => {
      const h = dp.histograms?.['agent.workflow.duration_seconds'];
      return h ? +(h.avg * 1000).toFixed(1) : 0;
    },
    color: '#13c2c2',
  },
];

const TS_WINDOW_OPTIONS = [
  { value: 5, label: '5分钟' },
  { value: 15, label: '15分钟' },
  { value: 30, label: '30分钟' },
  { value: 60, label: '1小时' },
];

// ---------- 主组件 ----------

export function MetricsDashboard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [healthData, setHealthData] = useState(null);
  const [metricsData, setMetricsData] = useState(null);
  const [tsData, setTsData] = useState([]);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [tsWindow, setTsWindow] = useState(30);

  const refreshData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [health, metrics, ts] = await Promise.all([
        fetchHealthDetail(),
        fetchMetrics(),
        fetchTimeseries(tsWindow),
      ]);
      setHealthData(health);
      setMetricsData(metrics);
      setTsData(ts.data_points || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [tsWindow]);

  useEffect(() => { refreshData(); }, [refreshData]);

  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(refreshData, 10000);
    return () => clearInterval(id);
  }, [autoRefresh, refreshData]);

  const counters = metricsData?.counters || {};
  const histograms = metricsData?.histograms || {};

  // RAG 指标
  const ragDuration = histograms['rag.retrieval.duration_seconds'];
  const ragQueries = counters['rag.retrieval.queries'];
  const ragService = healthData?.services?.find((s) => s.name === 'rag');
  const ragFiles = ragService?.details?.indexed_files || 0;
  const ragChunks = ragService?.details?.indexed_chunks || 0;

  // LLM 指标
  const llmCalls = counters['llm.calls'];
  const llmTokens = counters['llm.tokens_used'];

  // HTTP 指标
  const httpTotal = counters['http.requests.count'];
  const httpErrors = counters['http.errors.count'];
  const httpDuration = histograms['http.requests.duration_seconds'];

  // Agent 指标
  const agentWfCount = counters['agent.workflow.count'];
  const agentWfDuration = histograms['agent.workflow.duration_seconds'];
  const agentWfErrors = counters['agent.workflow.error.count'];

  // 会话/记忆指标
  const sessionCreates = counters['session.create.count'];
  const memoryTurns = counters['memory.turn.add.count'];

  const statusMap = { healthy: '正常', degraded: '降级', unhealthy: '异常' };

  return (
    <div style={{ padding: '24px' }}>
      {/* 顶部工具栏 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={3} style={{ margin: 0 }}>系统指标仪表盘</Title>
        <Space>
          <Segmented
            options={TS_WINDOW_OPTIONS}
            value={tsWindow}
            onChange={setTsWindow}
            size="small"
          />
          <Button
            icon={autoRefresh ? <SyncOutlined spin /> : <SyncOutlined />}
            onClick={() => setAutoRefresh(!autoRefresh)}
            type={autoRefresh ? 'primary' : 'default'}
            size="small"
          >
            {autoRefresh ? '自动刷新中' : '自动刷新'}
          </Button>
          <Button icon={<ReloadOutlined />} onClick={refreshData} loading={loading} size="small">
            刷新
          </Button>
        </Space>
      </div>

      {error && (
        <Alert message="加载指标失败" description={error} type="error" showIcon style={{ marginBottom: 16 }} />
      )}

      {loading && !healthData ? (
        <div style={{ textAlign: 'center', padding: 60 }}>
          <Spin size="large" tip="加载指标中..." />
        </div>
      ) : (
        <>
          {/* === 系统概览 === */}
          <Card title="系统概览" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col span={6}>
                <Statistic
                  title="系统状态"
                  value={statusMap[healthData?.status] || healthData?.status?.toUpperCase()}
                  valueStyle={{
                    color: healthData?.status === 'healthy' ? COLORS.success :
                           healthData?.status === 'degraded' ? COLORS.warning : COLORS.error
                  }}
                  prefix={healthData?.status === 'healthy' ? <CheckCircleOutlined /> : <ExclamationCircleOutlined />}
                />
              </Col>
              <Col span={6}>
                <Statistic title="运行时间" value={formatUptime(healthData?.uptime_seconds)} prefix={<ClockCircleOutlined />} />
              </Col>
              <Col span={6}>
                <Statistic title="Python 版本" value={healthData?.python_version || '-'} />
              </Col>
              <Col span={6}>
                <Statistic title="运行平台" value={healthData?.platform?.split('-')[0] || '-'} />
              </Col>
            </Row>
          </Card>

          {/* 服务状态 */}
          <Card title="服务状态" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              {healthData?.services?.map((svc) => (
                <Col span={8} key={svc.name}>
                  <ServiceStatusCard service={svc} />
                </Col>
              ))}
            </Row>
          </Card>

          {/* === 时序趋势图 === */}
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={12}>
              <Card title={<Space><ApiOutlined /><span>HTTP 请求趋势</span></Space>} size="small">
                <TimeSeriesChart dataPoints={tsData} series={HTTP_SERIES} height={220} unit="次" />
              </Card>
            </Col>
            <Col span={12}>
              <Card title={<Space><ThunderboltOutlined /><span>LLM 耗时趋势</span></Space>} size="small">
                <TimeSeriesChart dataPoints={tsData} series={LLM_DURATION_SERIES} height={220} unit="ms" />
              </Card>
            </Col>
          </Row>

          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={12}>
              <Card title={<Space><SearchOutlined /><span>RAG 检索耗时趋势</span></Space>} size="small">
                <TimeSeriesChart dataPoints={tsData} series={RAG_SERIES} height={220} unit="ms" />
              </Card>
            </Col>
            <Col span={12}>
              <Card title={<Space><RobotOutlined /><span>Agent 工作流耗时趋势</span></Space>} size="small">
                <TimeSeriesChart dataPoints={tsData} series={AGENT_SERIES} height={220} unit="ms" />
              </Card>
            </Col>
          </Row>

          {/* === HTTP 指标 === */}
          <Card
            title={<Space><ApiOutlined /><span>HTTP 请求指标</span></Space>}
            style={{ marginBottom: 16 }}
          >
            <Row gutter={16}>
              <Col span={8}>
                <CounterCard name="总请求数" data={httpTotal} icon={<ApiOutlined />} color="#1890ff" />
              </Col>
              <Col span={8}>
                <HistogramCard name="请求耗时" data={httpDuration} icon={<ClockCircleOutlined />} color="#1890ff" />
              </Col>
              <Col span={8}>
                <CounterCard name="5xx 错误数" data={httpErrors} icon={<ExclamationCircleOutlined />} color="#f5222d" />
              </Col>
            </Row>
          </Card>

          {/* === RAG 指标 === */}
          <Card
            title={<Space><SearchOutlined /><span>RAG 性能指标</span></Space>}
            style={{ marginBottom: 16 }}
          >
            <Row gutter={16}>
              <Col span={8}>
                <HistogramCard name="检索耗时" data={ragDuration} icon={<ThunderboltOutlined />} color="#722ed1" />
              </Col>
              <Col span={8}>
                <CounterCard name="查询总次数" data={ragQueries} icon={<SearchOutlined />} color="#1890ff" />
              </Col>
              <Col span={8}>
                <Card size="small">
                  <Statistic
                    title={<Space><DatabaseOutlined /><span>索引统计</span></Space>}
                    value={ragFiles}
                    suffix="个文件"
                    valueStyle={{ color: COLORS.success }}
                  />
                  <Divider style={{ margin: '8px 0' }} />
                  <Text type="secondary">已索引 {ragChunks} 个文档块</Text>
                </Card>
              </Col>
            </Row>
          </Card>

          {/* === LLM 调用 === */}
          <Card
            title={<Space><ThunderboltOutlined /><span>LLM 调用统计</span></Space>}
            style={{ marginBottom: 16 }}
          >
            <Row gutter={16}>
              <Col span={8}>
                <CounterCard name="LLM 调用次数" data={llmCalls} icon={<ThunderboltOutlined />} color="#fa8c16" />
              </Col>
              <Col span={8}>
                <CounterCard name="Token 消耗量" data={llmTokens} icon={<DatabaseOutlined />} color="#13c2c2" />
              </Col>
              <Col span={8}>
                <HistogramCard
                  name="LLM 调用耗时"
                  data={histograms['llm.call.duration_seconds']}
                  icon={<ClockCircleOutlined />}
                  color="#fa8c16"
                />
              </Col>
            </Row>
          </Card>

          {/* === Agent 工作流 === */}
          <Card
            title={<Space><RobotOutlined /><span>Agent 工作流指标</span></Space>}
            style={{ marginBottom: 16 }}
          >
            <Row gutter={16}>
              <Col span={8}>
                <CounterCard name="工作流执行次数" data={agentWfCount} icon={<RobotOutlined />} color="#13c2c2" />
              </Col>
              <Col span={8}>
                <HistogramCard name="工作流耗时" data={agentWfDuration} icon={<ClockCircleOutlined />} color="#13c2c2" />
              </Col>
              <Col span={8}>
                <CounterCard name="工作流错误数" data={agentWfErrors} icon={<ExclamationCircleOutlined />} color="#f5222d" />
              </Col>
            </Row>
          </Card>

          {/* === 会话 / 记忆 === */}
          <Card
            title={<Space><MessageOutlined /><span>会话 / 记忆指标</span></Space>}
            style={{ marginBottom: 16 }}
          >
            <Row gutter={16}>
              <Col span={8}>
                <CounterCard name="会话创建数" data={sessionCreates} icon={<MessageOutlined />} color="#667eea" />
              </Col>
              <Col span={8}>
                <CounterCard name="对话轮次" data={memoryTurns} icon={<MessageOutlined />} color="#667eea" />
              </Col>
              <Col span={8}>
                <Card size="small">
                  <Text type="secondary">
                    指标数据已支持持久化，服务重启后自动恢复历史时序数据。
                  </Text>
                </Card>
              </Col>
            </Row>
          </Card>


        </>
      )}
    </div>
  );
}

export default MetricsDashboard;
