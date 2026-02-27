/**
 * 指标监控页面
 * 独立的全屏系统健康状态和性能监控页面
 */
import { Typography } from 'antd';
import { DashboardOutlined } from '@ant-design/icons';
import { MetricsDashboard } from '../components/RAGDebug';
import { COLORS, SHADOWS } from '../styles/tokens';

const { Title } = Typography;

function MetricsPage() {
  return (
    <div style={{
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      background: COLORS.bgBase,
    }}>
      {/* 页面标题栏 */}
      <div style={{
        height: '56px',
        padding: '0 24px',
        background: COLORS.bgCard,
        borderBottom: `1px solid ${COLORS.border}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        boxShadow: SHADOWS.sm,
      }}>
        <Title level={4} style={{ 
          margin: 0, 
          fontWeight: 600, 
          fontSize: 16,
          color: COLORS.info,
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}>
          <DashboardOutlined style={{ fontSize: 18 }} />
          指标监控
        </Title>
      </div>

      {/* 指标监控面板 */}
      <div style={{ 
        flex: 1, 
        overflow: 'auto',
      }}>
        <MetricsDashboard />
      </div>
    </div>
  );
}

export default MetricsPage;
