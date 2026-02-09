import { useState } from 'react';
import { ConfigProvider, Layout, Typography, Button, Space, Tooltip } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { VerticalLeftOutlined, VerticalRightOutlined, SettingOutlined, BookOutlined } from '@ant-design/icons';
import KnowledgePage from './pages/Knowledge';

const { Title } = Typography;

function App() {
  const [leftSidebarCollapsed, setLeftSidebarCollapsed] = useState(false);
  const [aiSidebarVisible, setAiSidebarVisible] = useState(false);
  const [configTabVisible, setConfigTabVisible] = useState(false);
  const [configTabRequestId, setConfigTabRequestId] = useState(0);

  const handleOpenConfigTab = () => {
    setConfigTabVisible(true);
    setConfigTabRequestId((prev) => prev + 1);
  };

  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: '#667eea',
          borderRadius: 8,
        },
        motion: true,
        motionDurationMid: 0.3,
      }}
    >
      <Layout style={{ height: '100vh', width: '100vw', margin: 0, padding: 0, overflow: 'hidden', background: '#f5f7fa' }}>
        <div style={{
          height: 52,
          background: '#fff',
          borderBottom: '1px solid #e8e8e8',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 20px',
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          zIndex: 100,
          boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
          margin: 0,
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
          }}>
            <Title level={4} style={{ margin: 0, fontWeight: 600, fontSize: 16 }}>
              <BookOutlined /> 知识库
            </Title>
          </div>
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
            <KnowledgePage
              leftSidebarCollapsed={leftSidebarCollapsed}
              setLeftSidebarCollapsed={setLeftSidebarCollapsed}
              aiSidebarVisible={aiSidebarVisible}
              setAiSidebarVisible={setAiSidebarVisible}
              configTabVisible={configTabVisible}
              onConfigTabClose={() => setConfigTabVisible(false)}
              configTabRequestId={configTabRequestId}
            />
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
