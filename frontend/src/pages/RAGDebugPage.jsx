/**
 * RAG 调试页面
 * 独立的全屏 RAG 调试可视化界面
 */
import { Typography } from 'antd';
import { BugOutlined } from '@ant-design/icons';
import { RAGDebugPanel } from '../components/RAGDebug';
import { COLORS } from '../styles/tokens';

const { Title } = Typography;

function RAGDebugPage() {
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
          color: COLORS.rag,
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}>
          <BugOutlined style={{ fontSize: 18 }} />
          RAG 调试
        </Title>
      </div>

      {/* RAG 调试面板 */}
      <div style={{ 
        flex: 1, 
        overflow: 'auto',
      }}>
        <RAGDebugPanel />
      </div>
    </div>
  );
}

export default RAGDebugPage;
