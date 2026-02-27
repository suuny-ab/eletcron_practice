import { Typography, Space } from 'antd';
import { ThunderboltOutlined, EditOutlined, SearchOutlined } from '@ant-design/icons';
import PreviewMode from './PreviewMode';
import ChatMode from './ChatMode';
import { COLORS } from '../../styles/tokens';

const { Text } = Typography;

const modeLabels = {
  advise: 'AI 建议',
  edit: 'AI 编辑',
  rag: '知识库问答',
};

function AISidebar({
  visible,
  aiMode,
  onModeChange,
  chatMessages,
  ragMessages,
  ragSources,
  userInput,
  onInputChange,
  onSend,
  onOptimize,
  ragTopK,
  onTopKChange,
  previewMode,
  generatedContent,
  aiGenerating,
  ragLoading,
  onConfirmPreview,
  onCancelPreview,
  selectedFile,
  onOpenChunk,
  isDragging,
}) {
  const isRagMode = aiMode === 'rag';

  return (
    <div style={{
      height: '100%',
      padding: '0',
      background: COLORS.bgBase,
      display: 'flex',
      flexDirection: 'column',
      opacity: visible ? 1 : 0,
      pointerEvents: visible ? 'auto' : 'none',
      transition: isDragging ? 'none' : 'opacity 0.2s ease',
    }}>
      <div style={{ height: '100%', background: COLORS.bgCard, display: 'flex', flexDirection: 'column' }}>
        {/* 标题栏 */}
        <div style={{
          padding: '16px',
          borderBottom: `1px solid ${COLORS.borderLight}`,
          background: isRagMode
            ? `linear-gradient(135deg, ${COLORS.rag}12 0%, ${COLORS.ragLight}08 100%)`
            : '#fafafa',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <Text strong style={isRagMode ? { color: COLORS.rag } : undefined}>
            {previewMode ? 'AI 排版预览' : modeLabels[aiMode]}
          </Text>
          <Space size="small">
            {(aiGenerating || ragLoading) && (
              <span style={{ color: isRagMode ? COLORS.rag : COLORS.info, fontSize: 12 }}>
                (生成中...)
              </span>
            )}
          </Space>
        </div>

        {previewMode ? (
          <PreviewMode
            generatedContent={generatedContent}
            aiGenerating={aiGenerating}
            onConfirm={onConfirmPreview}
            onCancel={onCancelPreview}
          />
        ) : (
          <ChatMode
            aiMode={aiMode}
            onModeChange={onModeChange}
            chatMessages={chatMessages}
            ragMessages={ragMessages}
            ragSources={ragSources}
            ragTopK={ragTopK}
            onTopKChange={onTopKChange}
            userInput={userInput}
            onInputChange={onInputChange}
            onSend={onSend}
            onOptimize={onOptimize}
            aiGenerating={aiGenerating}
            ragLoading={ragLoading}
            selectedFile={selectedFile}
            onOpenChunk={onOpenChunk}
          />
        )}
      </div>
    </div>
  );
}

export default AISidebar;
