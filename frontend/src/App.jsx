import React, { useState } from 'react';
import { ConfigProvider, Layout, Menu, Typography, theme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { SettingOutlined, DatabaseOutlined, ThunderboltOutlined } from '@ant-design/icons';
import ConfigPage from './pages/Config';
import KnowledgePage from './pages/Knowledge';

const { Header, Content } = Layout;
const { Title, Text } = Typography;

function App() {
  const [currentPage, setCurrentPage] = useState('config');

  const {
    token: { colorBgContainer },
  } = theme.useToken();

  const renderContent = () => {
    switch (currentPage) {
      case 'config':
        return <ConfigPage />;
      case 'knowledge':
        return <KnowledgePage />;
      default:
        return <ConfigPage />;
    }
  };

  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: '#667eea',
          borderRadius: 8,
        },
      }}
    >
      <Layout style={{ height: '100vh', overflow: 'hidden' }}>
        <Header
          style={{
            background: '#fff',
            padding: '0 32px',
            display: 'flex',
            alignItems: 'center',
            borderBottom: '1px solid #f0f0f0',
            boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
            height: 64,
            lineHeight: '64px',
          }}
        >
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 16,
            marginRight: 'auto',
          }}>
            <ThunderboltOutlined style={{
              fontSize: 24,
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }} />
            <Title level={4} style={{ margin: 0, fontWeight: 600 }}>
              知识库迁移系统
            </Title>
          </div>

          <Menu
            mode="horizontal"
            selectedKeys={[currentPage]}
            style={{
              background: 'transparent',
              border: 'none',
              minWidth: 200,
              lineHeight: '64px',
            }}
            items={[
              {
                key: 'config',
                icon: <SettingOutlined />,
                label: '系统配置',
                onClick: () => setCurrentPage('config'),
              },
              {
                key: 'knowledge',
                icon: <DatabaseOutlined />,
                label: '知识库',
                onClick: () => setCurrentPage('knowledge'),
              },
            ]}
          />
        </Header>
        <Content
          style={{
            background: colorBgContainer,
            height: 'calc(100vh - 64px)',
            overflow: 'hidden'
          }}
        >
          {renderContent()}
        </Content>
      </Layout>
    </ConfigProvider>
  );
}

export default App;
