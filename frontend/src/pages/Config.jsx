import { useState, useEffect } from 'react';
import { Form, Input, Button, Card, message, Space, Spin, Popconfirm, Typography } from 'antd';
import { SaveOutlined, DeleteOutlined, ReloadOutlined } from '@ant-design/icons';
import { getConfig, updateConfig, deleteConfig } from '../api/config';

const { Title } = Typography;

function ConfigPage() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [hasConfig, setHasConfig] = useState(false);

  // 加载配置
  const loadConfig = async () => {
    setLoading(true);
    try {
      const response = await getConfig();
      const data = response.data;
      form.setFieldsValue(data);
      setHasConfig(true);
      message.success('配置加载成功');
    } catch (error) {
      if (error.response?.status === 404) {
        setHasConfig(false);
        message.info('暂无配置，请创建新配置');
      } else {
        message.error('加载配置失败: ' + (error.response?.data?.message || error.message));
      }
    } finally {
      setLoading(false);
    }
  };

  // 保存配置
  const handleSave = async (values) => {
    setLoading(true);
    try {
      await updateConfig(values);
      setHasConfig(true);
      message.success('配置保存成功');
    } catch (error) {
      message.error('保存配置失败: ' + (error.response?.data?.message || error.message));
    } finally {
      setLoading(false);
    }
  };

  // 删除配置
  const handleDelete = async () => {
    setLoading(true);
    try {
      await deleteConfig();
      form.resetFields();
      setHasConfig(false);
      message.success('配置删除成功');
    } catch (error) {
      message.error('删除配置失败: ' + (error.response?.data?.message || error.message));
    } finally {
      setLoading(false);
    }
  };

  // 页面加载时尝试读取配置
  useEffect(() => {
    loadConfig();
  }, []);

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      padding: '20px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center'
    }}>
      <Spin spinning={loading}>
        <Card
          style={{
            width: '100%',
            maxWidth: 600,
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)',
            borderRadius: '16px'
          }}
          title={
            <Title level={3} style={{ margin: 0, textAlign: 'center' }}>
              ⚙️ 系统配置
            </Title>
          }
        >
          <Form
            form={form}
            layout="vertical"
            onFinish={handleSave}
            autoComplete="off"
          >
            <Form.Item
              label="Obsidian Vault 路径"
              name="obsidian_vault_path"
              rules={[
                { required: true, message: '请输入 Obsidian Vault 路径' }
              ]}
            >
              <Input
                placeholder="例如: C:\\Users\\XXX\\Documents\\Obsidian Vault"
                prefix="📁"
                size="large"
              />
            </Form.Item>

            <Form.Item
              label="API Key"
              name="api_key"
              rules={[
                { required: true, message: '请输入 API Key' }
              ]}
            >
              <Input.Password
                placeholder="请输入 API Key"
                prefix="🔑"
                size="large"
              />
            </Form.Item>

            <Form.Item
              label="模型名称"
              name="model_name"
              rules={[
                { required: true, message: '请输入模型名称' }
              ]}
            >
              <Input
                placeholder="例如: qwen3-max"
                prefix="🤖"
                size="large"
              />
            </Form.Item>

            <Form.Item style={{ marginTop: 24 }}>
              <Space style={{ width: '100%', justifyContent: 'center' }} size="middle">
                <Button
                  type="primary"
                  htmlType="submit"
                  icon={<SaveOutlined />}
                  size="large"
                  style={{
                    minWidth: 120,
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    border: 'none',
                    borderRadius: '8px',
                    height: 45,
                    fontSize: 16
                  }}
                >
                  {hasConfig ? '更新配置' : '保存配置'}
                </Button>

                {hasConfig && (
                  <Popconfirm
                    title="确认删除"
                    description="确定要删除配置吗？"
                    onConfirm={handleDelete}
                    okText="确定"
                    cancelText="取消"
                  >
                    <Button
                      danger
                      icon={<DeleteOutlined />}
                      size="large"
                      style={{
                        minWidth: 120,
                        borderRadius: '8px',
                        height: 45,
                        fontSize: 16
                      }}
                    >
                      删除配置
                    </Button>
                  </Popconfirm>
                )}

                <Button
                  icon={<ReloadOutlined />}
                  size="large"
                  onClick={loadConfig}
                  style={{
                    minWidth: 120,
                    borderRadius: '8px',
                    height: 45,
                    fontSize: 16
                  }}
                >
                  刷新
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </Card>
      </Spin>
    </div>
  );
}

export default ConfigPage;
