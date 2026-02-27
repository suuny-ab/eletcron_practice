import { Card, Spin, Typography, Empty, Space, Tag, Button, Input } from 'antd';
import { FileOutlined, EditOutlined, CheckOutlined, CloseOutlined, FileTextOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import { remarkPlugins, rehypePlugins, createMarkdownComponents } from '../../utils/markdownStyles.jsx';
import { COLORS } from '../../styles/tokens';

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

function NoteTab({ noteKey, noteTitle, noteState, onStartEdit, onCancelEdit, onSave, onNoteStateChange }) {
  return (
    <Card
      title={
        <Space>
          <FileOutlined style={{ color: COLORS.info }} />
          <Text strong style={{ fontSize: 16 }}>{noteTitle}</Text>
          <Tag color="blue">Markdown</Tag>
        </Space>
      }
      extra={
        <Space>
          {!noteState.isEditing && (
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => onStartEdit(noteKey)}
            >
              编辑
            </Button>
          )}
        </Space>
      }
      bordered={false}
      style={{
        height: '100%',
        borderRadius: 0,
        boxShadow: 'none',
      }}
      bodyStyle={{
        padding: noteState.content ? '24px' : '48px',
        height: 'calc(100% - 60px)',
        overflow: 'auto',
      }}
    >
      <Spin spinning={noteState.contentLoading || noteState.saveLoading}>
        {noteState.isEditing ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', height: '100%' }}>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <Button icon={<CloseOutlined />} onClick={() => onCancelEdit(noteKey)}>
                取消
              </Button>
              <Button type="primary" icon={<CheckOutlined />} onClick={() => onSave(noteKey)}>
                保存
              </Button>
            </div>
            <TextArea
              value={noteState.editContent}
              onChange={(e) => onNoteStateChange(noteKey, { editContent: e.target.value })}
              style={{
                fontFamily: 'SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace',
                fontSize: 14,
                lineHeight: 1.6,
                height: 'calc(100vh - 250px)',
                minHeight: '500px',
              }}
              placeholder="输入 Markdown 内容..."
            />
          </div>
        ) : (
          noteState.content ? (
            <div style={{
              padding: '20px',
              backgroundColor: COLORS.bgCard,
              borderRadius: '8px',
            }}>
              <ReactMarkdown
                remarkPlugins={remarkPlugins}
                rehypePlugins={rehypePlugins}
                components={createMarkdownComponents('full')}
              >
                {noteState.content}
              </ReactMarkdown>
            </div>
          ) : (
            <Empty
              description={
                <Space direction="vertical" size="small">
                  <Paragraph type="secondary">请在左侧文件树中选择文件</Paragraph>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    仅支持预览和编辑 Markdown 格式文件
                  </Text>
                </Space>
              }
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              style={{ marginTop: 80 }}
            />
          )
        )}
      </Spin>
    </Card>
  );
}

export default NoteTab;
