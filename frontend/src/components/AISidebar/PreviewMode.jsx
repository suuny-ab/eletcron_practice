import { memo } from 'react';
import { Button, Typography } from 'antd';
import { CheckOutlined, CloseOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import { remarkPlugins, rehypePlugins, createMarkdownComponents } from '../../utils/markdownStyles.jsx';
import { COLORS } from '../../styles/tokens';

const { Text } = Typography;

const PreviewMode = memo(function PreviewMode({ generatedContent, aiGenerating, onConfirm, onCancel }) {
  return (
    <div style={{ height: '100%', minHeight: 0, display: 'flex', flexDirection: 'column' }}>
      <div style={{ flex: 1, minHeight: 0, padding: '16px', overflow: 'auto' }}>
        <div style={{ fontSize: 12, color: COLORS.textTertiary, marginBottom: 8 }}>
          内容长度: {generatedContent.length} 字符
        </div>
        <ReactMarkdown
          key={generatedContent}
          remarkPlugins={remarkPlugins}
          rehypePlugins={rehypePlugins}
          components={createMarkdownComponents('preview')}
        >
          {generatedContent || (aiGenerating && '等待 AI 生成内容...')}
        </ReactMarkdown>
      </div>
      <div style={{
        padding: '12px',
        borderTop: `1px solid ${COLORS.borderLight}`,
        display: 'flex',
        gap: '8px',
      }}>
        <Button
          icon={<CloseOutlined />}
          onClick={onCancel}
          disabled={!aiGenerating && !generatedContent}
          style={{ flex: 1 }}
        >
          {aiGenerating ? '取消生成' : '取消'}
        </Button>
        <Button
          type="primary"
          icon={<CheckOutlined />}
          onClick={() => onConfirm(generatedContent)}
          disabled={aiGenerating || !generatedContent}
          style={{ flex: 1 }}
        >
          确认保存
        </Button>
      </div>
    </div>
  );
});

export default PreviewMode;
