import { useState, useEffect, useRef } from 'react';
import { Tree, Card, message, Spin, Typography, Empty, Layout, Button, Space, Tag } from 'antd';
import { FolderOutlined, FileOutlined, ReloadOutlined, BookOutlined, FolderOpenOutlined } from '@ant-design/icons';
import { getFileTree } from '../api/knowledge';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import rehypeRaw from 'rehype-raw';
import 'highlight.js/styles/github-dark.css';

const { DirectoryTree } = Tree;
const { Title, Text, Paragraph } = Typography;
const { Sider, Content } = Layout;

function KnowledgePage() {
  const [treeData, setTreeData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileContent, setFileContent] = useState('');
  const [contentLoading, setContentLoading] = useState(false);
  const hasInitialized = useRef(false);
  const [expandedKeys, setExpandedKeys] = useState([]);

  // 切换展开/收起
  const toggleExpand = () => {
    const getAllKeys = (nodes) => {
      let keys = [];
      nodes.forEach(node => {
        if (node.children) {
          keys.push(node.key);
          keys = keys.concat(getAllKeys(node.children));
        }
      });
      return keys;
    };
    if (expandedKeys.length === 0) {
      setExpandedKeys(getAllKeys(treeData));
    } else {
      setExpandedKeys([]);
    }
  };

  // 加载文件树
  const loadTree = async () => {
    setLoading(true);
    try {
      const response = await getFileTree();
      setTreeData(response.data.tree);
      message.success('文件树加载成功');
    } catch (error) {
      if (error.response?.status === 404) {
        message.error('请先配置知识库路径');
      } else {
        message.error('加载文件树失败: ' + (error.response?.data?.message || error.message));
      }
    } finally {
      setLoading(false);
    }
  };

  // 页面加载时读取文件树
  useEffect(() => {
    if (!hasInitialized.current) {
      hasInitialized.current = true;
      loadTree();
    }
  }, []);

  // 处理文件选择
  const handleSelect = async (selectedKeys, info) => {
    const node = info.node;
    if (node.is_leaf) {
      // 检查文件扩展名
      const fileName = node.key;
      const isMarkdown = fileName.toLowerCase().endsWith('.md');

      if (!isMarkdown) {
        message.warning('仅支持预览 Markdown 格式文件');
        return;
      }

      setSelectedFile(node);
      setContentLoading(true);
      try {
        const { getFileContent } = await import('../api/knowledge');
        const response = await getFileContent(node.key);
        setFileContent(response.data.content);
      } catch (error) {
        message.error('读取文件失败: ' + (error.response?.data?.message || error.message));
      } finally {
        setContentLoading(false);
      }
    }
  };

  return (
    <Layout style={{ height: '100%', background: '#f5f7fa' }}>
      <Sider
        width={320}
        style={{
          background: '#fff',
          borderRight: '1px solid #e8e8e8',
          boxShadow: '2px 0 8px rgba(0,0,0,0.06)',
        }}
      >
        <div style={{
          padding: '24px 20px',
          borderBottom: '1px solid #f0f0f0',
          background: '#fff',
        }}>
          <Space align="center" style={{ width: '100%', justifyContent: 'space-between' }}>
            <Title level={4} style={{ margin: 0, color: '#262626', fontSize: 18 }}>
              <BookOutlined /> 知识库
            </Title>
            <Space size="small">
              <Button
                type="text"
                size="small"
                icon={expandedKeys.length > 0 ? <FolderOutlined /> : <FolderOpenOutlined />}
                onClick={toggleExpand}
              />
              <Button
                type="text"
                size="small"
                icon={<ReloadOutlined />}
                onClick={loadTree}
              />
            </Space>
          </Space>
        </div>

        <div style={{ padding: '16px', height: 'calc(100% - 72px)', overflowY: 'auto' }}>
          <Spin spinning={loading}>
            {treeData.length > 0 ? (
              <DirectoryTree
                showIcon
                expandedKeys={expandedKeys}
                onExpand={setExpandedKeys}
                onSelect={handleSelect}
                treeData={treeData}
                icon={({ is_leaf }) =>
                  is_leaf ? <FileOutlined style={{ color: '#1890ff' }} /> : <FolderOutlined style={{ color: '#faad14' }} />
                }
                style={{ fontSize: 14 }}
              />
            ) : (
              <Empty
                description="暂无文件"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                style={{ marginTop: 60 }}
              />
            )}
          </Spin>
        </div>
      </Sider>

      <Content style={{ padding: '24px', height: '100%', overflow: 'hidden' }}>
        <Card
          title={
            selectedFile ? (
              <Space>
                <FileOutlined style={{ color: '#1890ff' }} />
                <Text strong style={{ fontSize: 16 }}>{selectedFile.title}</Text>
                <Tag color="blue">Markdown</Tag>
              </Space>
            ) : (
              <Space>
                <FileOutlined style={{ color: '#d9d9d9' }} />
                <Text type="secondary" style={{ fontSize: 16 }}>未选择文件</Text>
              </Space>
            )
          }
          bordered={false}
          style={{
            height: '100%',
            borderRadius: '12px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
          }}
          bodyStyle={{
            padding: selectedFile ? '24px' : '48px',
            height: 'calc(100% - 60px)',
            overflow: 'auto',
          }}
        >
          <Spin spinning={contentLoading}>
            {fileContent ? (
              <div style={{
                padding: '20px',
                backgroundColor: '#fff',
                borderRadius: '8px',
              }}>
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[rehypeHighlight, rehypeRaw]}
                  components={{
                    h1: ({ children }) => <h1 style={{ fontSize: '2em', fontWeight: 'bold', marginTop: '1.5em', marginBottom: '0.8em', borderBottom: '1px solid #eaecef', paddingBottom: '0.3em' }}>{children}</h1>,
                    h2: ({ children }) => <h2 style={{ fontSize: '1.5em', fontWeight: 'bold', marginTop: '1.5em', marginBottom: '0.8em', borderBottom: '1px solid #eaecef', paddingBottom: '0.3em' }}>{children}</h2>,
                    h3: ({ children }) => <h3 style={{ fontSize: '1.25em', fontWeight: 'bold', marginTop: '1.5em', marginBottom: '0.8em' }}>{children}</h3>,
                    p: ({ children }) => <p style={{ lineHeight: '1.8', marginBottom: '1em', color: '#24292e' }}>{children}</p>,
                    ul: ({ children }) => <ul style={{ paddingLeft: '2em', marginBottom: '1em', lineHeight: '1.8' }}>{children}</ul>,
                    ol: ({ children }) => <ol style={{ paddingLeft: '2em', marginBottom: '1em', lineHeight: '1.8' }}>{children}</ol>,
                    li: ({ children }) => <li style={{ marginBottom: '0.5em' }}>{children}</li>,
                    code: ({ inline, className, children, ...props }) => {
                      if (inline) {
                        return <code style={{
                          backgroundColor: 'rgba(27, 31, 35, 0.05)',
                          padding: '0.2em 0.4em',
                          borderRadius: '3px',
                          fontFamily: 'SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace',
                          fontSize: '85%'
                        }} {...props}>{children}</code>;
                      }
                      return <code className={className} {...props}>{children}</code>;
                    },
                    pre: ({ children }) => <pre style={{
                      backgroundColor: '#282c34',
                      padding: '16px',
                      borderRadius: '6px',
                      overflow: 'auto',
                      marginBottom: '1em'
                    }}>{children}</pre>,
                    blockquote: ({ children }) => <blockquote style={{
                      borderLeft: '4px solid #dfe2e5',
                      padding: '0 1em',
                      color: '#6a737d',
                      marginLeft: '0',
                      marginBottom: '1em'
                    }}>{children}</blockquote>,
                    table: ({ children }) => <table style={{
                      width: '100%',
                      borderCollapse: 'collapse',
                      marginBottom: '1em'
                    }}>{children}</table>,
                    thead: ({ children }) => <thead>{children}</thead>,
                    tbody: ({ children }) => <tbody>{children}</tbody>,
                    tr: ({ children }) => <tr style={{ borderBottom: '1px solid #eaecef' }}>{children}</tr>,
                    th: ({ children }) => <th style={{
                      padding: '6px 13px',
                      fontWeight: '600',
                      borderBottom: '1px solid #dfe2e5',
                      backgroundColor: '#f6f8fa',
                      textAlign: 'left'
                    }}>{children}</th>,
                    td: ({ children }) => <td style={{
                      padding: '6px 13px',
                      borderBottom: '1px solid #eaecef',
                      textAlign: 'left'
                    }}>{children}</td>,
                    a: ({ children, href }) => <a href={href} style={{ color: '#0366d6', textDecoration: 'none' }}>{children}</a>,
                  }}
                >
                  {fileContent}
                </ReactMarkdown>
              </div>
            ) : (
              <Empty
                description={
                  <Space direction="vertical" size="small">
                    <Paragraph type="secondary">请在左侧文件树中选择文件</Paragraph>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      仅支持预览 Markdown 格式文件
                    </Text>
                  </Space>
                }
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                style={{ marginTop: 80 }}
              />
            )}
          </Spin>
        </Card>
      </Content>
    </Layout>
  );
}

export default KnowledgePage;
