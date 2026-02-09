import { useState, useEffect, useRef } from 'react';
import { Form, Input, Button, Card, message, Space, Spin, Popconfirm, Typography, Col, Row, Layout } from 'antd';
import { SaveOutlined, DeleteOutlined, ReloadOutlined, SettingOutlined } from '@ant-design/icons';
import { getConfig, updateConfig, deleteConfig } from '../api/config';

const { Title, Text } = Typography;
const { Content } = Layout;

function ConfigPage({ embedded = false }) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [hasConfig, setHasConfig] = useState(false);
  const hasInitialized = useRef(false);

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
    if (!hasInitialized.current) {
      hasInitialized.current = true;
      loadConfig();
    }
  }, []);

  const containerStyle = embedded
    ? {
      height: '100%',
      overflow: 'auto',
      padding: '24px',
      display: 'flex',
      flexDirection: 'column',
    }
    : {
      height: 'calc(100vh - 52px)',
      marginTop: 52,
      overflow: 'hidden',
      padding: '24px',
      display: 'flex',
      flexDirection: 'column',
    };

  const Container = embedded ? 'div' : Content;

  return (
    <Container style={containerStyle}>
      <Spin spinning={loading}>
        <div style={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          overflow: 'auto',
        }}>
          <Card
            style={{
              width: '100%',
              maxWidth: 560,
              margin: '0 auto',
              boxShadow: '0 4px 24px rgba(0, 0, 0, 0.08)',
              borderRadius: '12px',
              border: '1px solid #f0f0f0'
            }}
          >
            <div style={{ marginBottom: 32, textAlign: 'center' }}>
              <div style={{
                width: 64,
                height: 64,
                borderRadius: '50%',
                background: '#fff',
                border: '1px solid #e8e8e8',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 16px',
              }}>
                <SettingOutlined style={{ fontSize: 28, color: '#262626' }} />
              </div>
              <Title level={3} style={{ margin: 0 }}>
                系统配置
              </Title>
              <Text type="secondary">
                配置知识库路径和 AI 模型
              </Text>
            </div>

            <Form
              form={form}
              layout="vertical"
              onFinish={handleSave}
              autoComplete="off"
            >
              <Form.Item
                label={<Text strong>Obsidian Vault 路径</Text>}
                name="obsidian_vault_path"
                rules={[
                  { required: true, message: '请输入 Obsidian Vault 路径' }
                ]}
              >
                <Input
                  placeholder="例如: C:\\Users\\XXX\\Documents\\Obsidian Vault"
                  size="large"
                  style={{ borderRadius: 8 }}
                />
              </Form.Item>

              <Form.Item
                label={<Text strong>API Key</Text>}
                name="api_key"
                rules={[
                  { required: true, message: '请输入 API Key' }
                ]}
              >
                <Input.Password
                  placeholder="请输入 API Key"
                  size="large"
                  style={{ borderRadius: 8 }}
                />
              </Form.Item>

              <Form.Item
                label={<Text strong>模型名称</Text>}
                name="model_name"
                rules={[
                  { required: true, message: '请输入模型名称' }
                ]}
              >
                <Input
                  placeholder="例如: qwen3-max"
                  size="large"
                  style={{ borderRadius: 8 }}
                />
              </Form.Item>

              <Form.Item style={{ marginTop: 32 }}>
                <Row gutter={16}>
                  <Col span={hasConfig ? 8 : 24}>
                    <Button
                      htmlType="submit"
                      icon={<SaveOutlined />}
                      size="large"
                      block
                      style={{
                        background: '#fff',
                        border: '1px solid #d9d9d9',
                        borderRadius: 8,
                        height: 42,
                        fontSize: 15
                      }}
                    >
                      {hasConfig ? '更新配置' : '保存配置'}
                    </Button>
                  </Col>
                  {hasConfig && (
                    <>
                      <Col span={8}>
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
                            block
                            style={{
                              borderRadius: 8,
                              height: 42,
                              fontSize: 15
                            }}
                          >
                            删除配置
                          </Button>
                        </Popconfirm>
                      </Col>
                      <Col span={8}>
                        <Button
                          icon={<ReloadOutlined />}
                          size="large"
                          block
                          onClick={loadConfig}
                          style={{
                            borderRadius: 8,
                            height: 42,
                            fontSize: 15
                          }}
                        >
                          刷新
                        </Button>
                      </Col>
                    </>
                  )}
                </Row>
              </Form.Item>
            </Form>
          </Card>
        </div>
      </Spin>
    </Container>
  );
}

export default ConfigPage;
