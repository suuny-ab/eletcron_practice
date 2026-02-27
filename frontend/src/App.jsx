import { useState } from 'react';
import { ConfigProvider, Layout, Typography, Button, Space, Tooltip, ButtonGroup } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { VerticalLeftOutlined, VerticalRightOutlined, SettingOutlined, BookOutlined, BugOutlined, DashboardOutlined } from '@ant-design/icons';
import KnowledgePage from './pages/Knowledge';
import RAGDebugPage from './pages/RAGDebugPage';
import MetricsPage from './pages/MetricsPage';
import { COLORS, SHADOWS, Z_INDEX, antThemeToken, antComponentTheme } from './styles/tokens';

const { Title } = Typography;

function App() {
  const [leftSidebarCollapsed, setLeftSidebarCollapsed] = useState(false);
  const [aiSidebarVisible, setAiSidebarVisible] = useState(false);
  const [configTabVisible, setConfigTabVisible] = useState(false);
  const [configTabRequestId, setConfigTabRequestId] = useState(0);
  const [currentPage, setCurrentPage] = useState('knowledge'); // 'knowledge' | 'debug' | 'metrics'

  const handleOpenConfigTab = () => {
    setConfigTabVisible(true);
    setConfigTabRequestId((prev) => prev + 1);
  };

  const pageTitle = {
    knowledge: '知识库',
    debug: 'RAG 调试',
    metrics: '指标监控',
  };

  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: antThemeToken,
        components: antComponentTheme,
        motion: true,
        motionDurationMid: 0.3,
      }}
    >
      <Layout style={{ height: '100vh', width: '100vw', margin: 0, padding: 0, overflow: 'hidden', background: COLORS.bgBase }}>
        <div style={{
          height: 52,
          background: COLORS.bgCard,
          borderBottom: `1px solid ${COLORS.border}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 20px',
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          zIndex: Z_INDEX.header,
          boxShadow: SHADOWS.sm,
          margin: 0,
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
          }}>
            <Title level={4} style={{ margin: 0, fontWeight: 600, fontSize: 16 }}>
              <BookOutlined /> {pageTitle[currentPage]}
            </Title>
            <ButtonGroup size="small" style={{ marginLeft: 12 }}>
              <Button
                type={currentPage === 'knowledge' ? 'primary' : 'default'}
                onClick={() => setCurrentPage('knowledge')}
              >
                知识库
              </Button>
              <Button
                type={currentPage === 'debug' ? 'primary' : 'default'}
                icon={<BugOutlined />}
                onClick={() => setCurrentPage('debug')}
              >
                RAG 调试
              </Button>
              <Button
                type={currentPage === 'metrics' ? 'primary' : 'default'}
                icon={<DashboardOutlined />}
                onClick={() => setCurrentPage('metrics')}
              >
                指标监控
              </Button>
            </ButtonGroup>
          </div>
          {currentPage === 'knowledge' && (
            <Space size={8}>
              <Button
                type="text"
                icon={<VerticalLeftOutlined />}
                onClick={() => setLeftSidebarCollapsed(!leftSidebarCollapsed)}
                style={{ fontSize: 16, width: 40, height: 40, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              />
              <Button
                type="text"
                icon={<VerticalRightOutlined />}
                onClick={() => setAiSidebarVisible(!aiSidebarVisible)}
                style={{ fontSize: 16, width: 40, height: 40, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              />
              <Tooltip title="系统配置">
                <Button
                  type="text"
                  icon={<SettingOutlined />}
                  onClick={handleOpenConfigTab}
                  style={{ fontSize: 16, width: 40, height: 40, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                />
              </Tooltip>
            </Space>
          )}
        </div>

        <div style={{
          marginTop: 52,
          height: 'calc(100vh - 52px)',
          overflow: 'hidden',
          width: '100%',
          padding: 0,
        }}>
          <div style={{
            animation: 'fadeIn 0.3s ease-in-out',
            height: '100%',
          }}>
            {currentPage === 'knowledge' && (
              <KnowledgePage
                leftSidebarCollapsed={leftSidebarCollapsed}
                setLeftSidebarCollapsed={setLeftSidebarCollapsed}
                aiSidebarVisible={aiSidebarVisible}
                setAiSidebarVisible={setAiSidebarVisible}
                configTabVisible={configTabVisible}
                onConfigTabClose={() => setConfigTabVisible(false)}
                configTabRequestId={configTabRequestId}
              />
            )}
            {currentPage === 'debug' && <RAGDebugPage />}
            {currentPage === 'metrics' && <MetricsPage />}
          </div>
        </div>

        <style jsx global>{`
          @keyframes fadeIn {
            from {
              opacity: 0;
              transform: translateY(8px);
            }
            to {
              opacity: 1;
              transform: translateY(0);
            }
          }
        `}</style>
      </Layout>
    </ConfigProvider>
  );
}

export default App;
