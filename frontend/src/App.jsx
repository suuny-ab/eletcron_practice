import React from 'react';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import ConfigPage from './pages/Config';

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <ConfigPage />
    </ConfigProvider>
  );
}

export default App;
