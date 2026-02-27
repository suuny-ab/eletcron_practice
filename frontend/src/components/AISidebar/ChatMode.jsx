import { Typography, Empty, Space, Input, Select, Button } from 'antd';
import { SendOutlined, BgColorsOutlined, ThunderboltOutlined, EditOutlined, SearchOutlined } from '@ant-design/icons';
import ChatMessage from './ChatMessage';
import { SourceList } from './SourceCard';
import { COLORS } from '../../styles/tokens';

const { Text } = Typography;
const { TextArea } = Input;

function ChatMode({
  aiMode,
  onModeChange,
  chatMessages,
  ragMessages,
  ragSources,
  ragTopK,
  onTopKChange,
  userInput,
  onInputChange,
  onSend,
  onOptimize,
  aiGenerating,
  ragLoading,
  selectedFile,
  onOpenChunk,
}) {
  const messages = aiMode === 'rag' ? ragMessages : chatMessages;
  const isLoading = aiMode === 'rag' ? ragLoading : aiGenerating;

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* 上方：对话显示 */}
      <div style={{
        flex: 2,
        padding: '16px',
        overflow: 'auto',
        borderBottom: `1px solid ${COLORS.borderLight}`,
      }}>
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          {messages.length === 0 && (
            <Empty
              description={
                <Space direction="vertical" size="small">
                  <Text type="secondary">
                    {aiMode === 'rag' ? '知识库问答' : '开始与 AI 对话'}
                  </Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {aiMode === 'rag'
                      ? '向整个知识库提问，AI 会检索相关笔记并生成答案'
                      : aiMode === 'advise' ? 'AI 建议模式' : 'AI 编辑模式'}
                  </Text>
                </Space>
              }
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          )}
          {messages.map((msg, index) => (
            <div key={index}>
              <ChatMessage msg={msg} isRagMode={aiMode === 'rag'} />
              {/* RAG 模式下最后一条 AI 消息后显示引用来源 */}
              {aiMode === 'rag' && msg.role === 'assistant' && index === messages.length - 1 && (
                <SourceList sources={ragSources} onOpenChunk={onOpenChunk} />
              )}
            </div>
          ))}
          {isLoading && (
            <div style={{
              padding: '12px',
              borderRadius: '8px',
              background: COLORS.bgHover,
              maxWidth: '85%',
            }}>
              <Text type="secondary">AI 正在生成...</Text>
            </div>
          )}
        </Space>
      </div>

      {/* 下方：输入区域 */}
      <div style={{
        flex: 1,
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
      }}>
        <TextArea
          value={userInput}
          onChange={(e) => onInputChange(e.target.value)}
          placeholder={
            aiMode === 'advise' ? '请输入您的问题...' :
            aiMode === 'edit' ? '请输入编辑要求...' :
            '请输入您的问题，AI 将检索整个知识库...'
          }
          onPressEnter={(e) => {
            if (!e.shiftKey) {
              e.preventDefault();
              onSend();
            }
          }}
          autoSize={{ minRows: 3, maxRows: 6 }}
          style={{ flex: 1 }}
        />

        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <Select
            value={aiMode}
            onChange={onModeChange}
            style={{ width: 120 }}
            size="small"
          >
            <Select.Option value="advise">
              <Space size="small"><ThunderboltOutlined />AI 建议</Space>
            </Select.Option>
            <Select.Option value="edit">
              <Space size="small"><EditOutlined />AI 编辑</Space>
            </Select.Option>
            <Select.Option value="rag">
              <Space size="small"><SearchOutlined />知识库问答</Space>
            </Select.Option>
          </Select>

          {aiMode === 'rag' && (
            <Select
              value={ragTopK}
              onChange={onTopKChange}
              style={{ width: 80 }}
              size="small"
            >
              <Select.Option value={1}>1 条</Select.Option>
              <Select.Option value={3}>3 条</Select.Option>
              <Select.Option value={5}>5 条</Select.Option>
              <Select.Option value={10}>10 条</Select.Option>
            </Select>
          )}

          {aiMode !== 'rag' && (
            <Button
              type="primary"
              icon={<BgColorsOutlined />}
              onClick={onOptimize}
              disabled={aiGenerating || !selectedFile}
              style={{ flex: 1 }}
            >
              一键排版
            </Button>
          )}

          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={onSend}
            disabled={(aiGenerating || ragLoading) || !userInput.trim()}
            style={{ flex: aiMode === 'rag' ? 2 : 1 }}
          >
            发送
          </Button>
        </div>
      </div>
    </div>
  );
}

export default ChatMode;
