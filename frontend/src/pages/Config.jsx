import { useState, useEffect, useRef } from 'react';
import { Form, Input, Button, Card, message, Space, Spin, Popconfirm, Typography, Col, Row, Layout, Tabs, Divider } from 'antd';
import { SaveOutlined, DeleteOutlined, ReloadOutlined, SettingOutlined, EditOutlined, ReloadOutlined as UndoOutlined } from '@ant-design/icons';
import { getConfig, updateConfig, deleteConfig } from '../api/config';

const { Title, Text } = Typography;
const { Content } = Layout;
const { TextArea } = Input;

function ConfigPage({ embedded = false }) {
  const [form] = Form.useForm();
  const [promptsForm] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [hasConfig, setHasConfig] = useState(false);
  const [activeTab, setActiveTab] = useState('basic');
  const hasInitialized = useRef(false);

  // 默认提示词模板
  const defaultPrompts = {
    optimize: {
      system: `你是一个专业的Markdown文档排版优化专家，擅长整理和优化各类文档的结构和格式。
在保持原文的核心内容和意义不变的前提下可以对文档内容做适当修改。`,
      human: `请优化以下Markdown文档的排版和结构：

文档内容：
{content}

请直接返回优化后的完整文档内容，不要添加额外的说明文字。`
    },
    advise: {
      system: `你是一个专业的文档助手，擅长分析和优化各类文档内容。
请基于用户提供的文档内容和问题，提供有价值的建议和回答。

回答要求：
1. 语言需要专业且友好
2. 建议需要实用且具体
3. 格式要清晰易读`,
      human: `文件内容：
{content}

用户问题：{question}

请基于以上文件内容和用户问题，提供专业的分析和建议。`
    },
    edit: {
      system: `你是一个专业的文档编辑专家，擅长根据用户的具体要求编辑和优化Markdown文档。

编辑原则：
1. 严格遵守用户的要求进行编辑
2. 保持Markdown格式的规范性
3. 确保文档的逻辑连贯性
4. 保持原文档的核心观点和意图，除非用户明确要求改变
5. 输出完整的编辑后文档，不要添加额外的说明文字`,
      human: `用户编辑要求：
{requirement}

原文档内容：
{content}

请根据用户要求编辑上述文档，直接返回编辑后的完整Markdown内容。`
    },
    summary: {
      system: `你是对话摘要器。请将以下对话内容压缩为一段摘要，保留关键结论、修改细则、明确的约束与约定，去除重复、闲聊与无关信息。

摘要要求：
1. 以清晰要点组织，不超过 200 字
2. 必须保留用户已确认的修改决策与约束
3. 不要引入新的内容，不做推测`,
      human: `{conversation}`
    }
  };

  // 加载配置
  const loadConfig = async () => {
    setLoading(true);
    try {
      const response = await getConfig();
      const data = response.data;
      form.setFieldsValue(data);
      // 提示词配置：优先使用后端数据，否则使用默认值
      const promptsToSet = data.prompts || defaultPrompts;
      promptsForm.setFieldsValue({ prompts: promptsToSet });
      setHasConfig(true);
      message.success('配置加载成功');
    } catch (error) {
      if (error.response?.status === 404) {
        setHasConfig(false);
        message.info('暂无配置，请创建新配置');
        // 404时也设置默认提示词
        promptsForm.setFieldsValue({ prompts: defaultPrompts });
      } else {
        message.error('加载配置失败: ' + (error.response?.data?.message || error.message));
      }
    } finally {
      setLoading(false);
    }
  };

  // 保存基础配置
  const handleSave = async (values) => {
    setLoading(true);
    try {
      // 获取提示词配置（验证并获取所有字段值）
      const promptsValues = await promptsForm.validateFields();
      const configData = {
        ...values,
        prompts: promptsValues.prompts || defaultPrompts  // 如果为空则使用默认值
      };
      await updateConfig(configData);
      setHasConfig(true);
      message.success('配置保存成功');
    } catch (error) {
      message.error('保存配置失败: ' + (error.response?.data?.message || error.message));
    } finally {
      setLoading(false);
    }
  };

  // 重置单个提示词为默认值
  const handleResetPrompt = (taskType) => {
    const promptsValues = promptsForm.getFieldsValue() || {};
    const currentPrompts = promptsValues.prompts || {};
    promptsForm.setFieldsValue({
      prompts: {
        ...currentPrompts,
        [taskType]: defaultPrompts[taskType]
      }
    });
    message.success(`已重置 ${taskType} 提示词为默认值`);
  };

  // 删除配置
  const handleDelete = async () => {
    setLoading(true);
    try {
      await deleteConfig();
      form.resetFields();
      promptsForm.resetFields();
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
              <Tabs
                activeKey={activeTab}
                onChange={setActiveTab}
                items={[
                  {
                    key: 'basic',
                    label: '基础配置',
                    children: (
                      <>
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
                      </>
                    )
                  },
                  {
                    key: 'prompts',
                    label: '提示词配置',
                    children: (
                      <Form form={promptsForm} layout="vertical">
                        {Object.entries(defaultPrompts).map(([taskType, defaultConfig]) => (
                          <div key={taskType} style={{ marginBottom: 24 }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                              <Text strong style={{ fontSize: 15 }}>
                                {taskType === 'optimize' && '文档排版优化'}
                                {taskType === 'advise' && '文档建议'}
                                {taskType === 'edit' && '文档编辑'}
                                {taskType === 'summary' && '对话摘要'}
                              </Text>
                              <Button
                                size="small"
                                icon={<UndoOutlined />}
                                onClick={() => handleResetPrompt(taskType)}
                              >
                                重置为默认
                              </Button>
                            </div>
                            <Form.Item
                              name={['prompts', taskType, 'system']}
                              label={<Text type="secondary">系统提示词（System Prompt）</Text>}
                              initialValue={defaultConfig.system}
                            >
                              <TextArea
                                rows={4}
                                placeholder="请输入系统提示词"
                                style={{ borderRadius: 8 }}
                              />
                            </Form.Item>
                            <Form.Item
                              name={['prompts', taskType, 'human']}
                              label={<Text type="secondary">用户提示词（Human Prompt）</Text>}
                              initialValue={defaultConfig.human}
                            >
                              <TextArea
                                rows={4}
                                placeholder="请输入用户提示词"
                                style={{ borderRadius: 8 }}
                              />
                            </Form.Item>
                          </div>
                        ))}
                      </Form>
                    )
                  }
                ]}
              />

              <Divider />

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
